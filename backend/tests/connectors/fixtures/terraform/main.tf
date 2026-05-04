# ── Variables ─────────────────────────────────────────────

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.medium"
}

variable "ami_id" {
  description = "AMI ID for the EC2 instance"
  type        = string
}

variable "environment" {
  description = "Deployment environment name"
  type        = string
  default     = "production"
}

variable "db_password" {
  description = "RDS master password"
  type        = string
  sensitive   = true
}

# ── Data Sources ──────────────────────────────────────────

data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_caller_identity" "current" {}

# ── Networking ────────────────────────────────────────────

resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "syncdoc-vpc"
  }
}

resource "aws_subnet" "public_a" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.1.0/24"
  availability_zone       = "eu-west-2a"
  map_public_ip_on_launch = true

  depends_on = [aws_vpc.main]

  tags = {
    Name = "public-a"
  }
}

resource "aws_subnet" "public_b" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.2.0/24"
  availability_zone       = "eu-west-2b"
  map_public_ip_on_launch = true

  depends_on = [aws_vpc.main]

  tags = {
    Name = "public-b"
  }
}

resource "aws_subnet" "private_a" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.10.0/24"
  availability_zone = "eu-west-2a"

  depends_on = [aws_vpc.main]

  tags = {
    Name = "private-a"
  }
}

resource "aws_subnet" "private_b" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.11.0/24"
  availability_zone = "eu-west-2b"

  depends_on = [aws_vpc.main]

  tags = {
    Name = "private-b"
  }
}

resource "aws_internet_gateway" "gw" {
  vpc_id = aws_vpc.main.id

  depends_on = [aws_vpc.main]

  tags = {
    Name = "syncdoc-igw"
  }
}

resource "aws_nat_gateway" "nat" {
  allocation_id = aws_eip.nat.id
  subnet_id     = aws_subnet.public_a.id

  depends_on = [aws_internet_gateway.gw, aws_eip.nat, aws_subnet.public_a]

  tags = {
    Name = "syncdoc-nat"
  }
}

resource "aws_eip" "nat" {
  domain = "vpc"

  tags = {
    Name = "nat-eip"
  }
}

# ── Security Groups ───────────────────────────────────────

resource "aws_security_group" "alb_sg" {
  name        = "alb-sg"
  description = "Security group for ALB"
  vpc_id      = aws_vpc.main.id

  depends_on = [aws_vpc.main]

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "web_sg" {
  name        = "web-sg"
  description = "Security group for web servers"
  vpc_id      = aws_vpc.main.id

  depends_on = [aws_vpc.main, aws_security_group.alb_sg]

  ingress {
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb_sg.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "db_sg" {
  name        = "db-sg"
  description = "Security group for RDS"
  vpc_id      = aws_vpc.main.id

  depends_on = [aws_vpc.main, aws_security_group.web_sg]

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.web_sg.id]
  }
}

resource "aws_security_group" "redis_sg" {
  name        = "redis-sg"
  description = "Security group for ElastiCache"
  vpc_id      = aws_vpc.main.id

  depends_on = [aws_vpc.main, aws_security_group.web_sg]

  ingress {
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.web_sg.id]
  }
}

# ── Load Balancer ─────────────────────────────────────────

resource "aws_lb" "main" {
  name               = "syncdoc-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb_sg.id]
  subnets            = [aws_subnet.public_a.id, aws_subnet.public_b.id]

  depends_on = [aws_security_group.alb_sg, aws_subnet.public_a, aws_subnet.public_b]

  tags = {
    Name = "syncdoc-alb"
  }
}

resource "aws_lb_target_group" "web" {
  name     = "web-tg"
  port     = 8000
  protocol = "HTTP"
  vpc_id   = aws_vpc.main.id

  depends_on = [aws_vpc.main]

  health_check {
    path                = "/api/health"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    interval            = 30
  }
}

resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.main.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = aws_acm_certificate.cert.arn

  depends_on = [aws_lb.main, aws_acm_certificate.cert]

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.web.arn
  }
}

# ── Compute ───────────────────────────────────────────────

resource "aws_instance" "web" {
  ami                    = var.ami_id
  instance_type          = var.instance_type
  subnet_id              = aws_subnet.private_a.id
  vpc_security_group_ids = [aws_security_group.web_sg.id]

  depends_on = [aws_security_group.web_sg, aws_subnet.private_a, aws_iam_instance_profile.web]

  tags = {
    Name = "web-server"
  }
}

resource "aws_launch_template" "web" {
  name_prefix   = "web-"
  image_id      = var.ami_id
  instance_type = var.instance_type

  network_interfaces {
    security_groups = [aws_security_group.web_sg.id]
  }

  depends_on = [aws_security_group.web_sg]

  tag_specifications {
    resource_type = "instance"
    tags = {
      Name = "web-asg"
    }
  }
}

resource "aws_autoscaling_group" "web" {
  name                = "web-asg"
  desired_capacity    = 2
  max_size            = 6
  min_size            = 1
  target_group_arns   = [aws_lb_target_group.web.arn]
  vpc_zone_identifier = [aws_subnet.private_a.id, aws_subnet.private_b.id]

  depends_on = [aws_launch_template.web, aws_lb_target_group.web, aws_subnet.private_a, aws_subnet.private_b]

  launch_template {
    id      = aws_launch_template.web.id
    version = "$Latest"
  }
}

# ── Database ──────────────────────────────────────────────

resource "aws_db_subnet_group" "main" {
  name       = "syncdoc-db-subnet"
  subnet_ids = [aws_subnet.private_a.id, aws_subnet.private_b.id]

  depends_on = [aws_subnet.private_a, aws_subnet.private_b]
}

resource "aws_db_instance" "postgres" {
  identifier             = "syncdoc-db"
  engine                 = "postgres"
  engine_version         = "16.3"
  instance_class         = "db.t4g.medium"
  allocated_storage      = 50
  max_allocated_storage  = 200
  db_name                = "syncdoc"
  username               = "syncdoc"
  password               = var.db_password
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.db_sg.id]
  multi_az               = true
  storage_encrypted      = true
  kms_key_id             = aws_kms_key.db.arn
  skip_final_snapshot    = false

  depends_on = [aws_db_subnet_group.main, aws_security_group.db_sg, aws_kms_key.db]
}

# ── Cache ─────────────────────────────────────────────────

resource "aws_elasticache_subnet_group" "main" {
  name       = "syncdoc-cache-subnet"
  subnet_ids = [aws_subnet.private_a.id, aws_subnet.private_b.id]

  depends_on = [aws_subnet.private_a, aws_subnet.private_b]
}

resource "aws_elasticache_replication_group" "redis" {
  replication_group_id = "syncdoc-redis"
  description          = "Redis for Celery and caching solution"
  node_type            = "cache.t4g.micro"
  num_cache_clusters   = 2
  engine_version       = "7.1"
  port                 = 6379
  subnet_group_name    = aws_elasticache_subnet_group.main.name
  security_group_ids   = [aws_security_group.redis_sg.id]
  at_rest_encryption_enabled = true

  depends_on = [aws_elasticache_subnet_group.main, aws_security_group.redis_sg]
}

# ── Storage ───────────────────────────────────────────────

resource "aws_s3_bucket" "docs" {
  bucket = "syncdoc-docs-${var.environment}"

  tags = {
    Name = "syncdoc-docs"
  }
}

resource "aws_s3_bucket_versioning" "docs" {
  bucket = aws_s3_bucket.docs.id

  depends_on = [aws_s3_bucket.docs]

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "docs" {
  bucket = aws_s3_bucket.docs.id

  depends_on = [aws_s3_bucket.docs, aws_kms_key.s3]

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.s3.arn
    }
  }
}

# ── Encryption ────────────────────────────────────────────

resource "aws_kms_key" "db" {
  description = "KMS key for RDS encryption"
  enable_key_rotation = true
}

resource "aws_kms_key" "s3" {
  description = "KMS key for S3 encryption"
  enable_key_rotation = true
}

# ── IAM ───────────────────────────────────────────────────

resource "aws_iam_role" "web" {
  name = "syncdoc-web-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy" "web_s3" {
  name = "web-s3-access"
  role = aws_iam_role.web.id

  depends_on = [aws_iam_role.web, aws_s3_bucket.docs]

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["s3:GetObject", "s3:PutObject", "s3:ListBucket"]
      Resource = [aws_s3_bucket.docs.arn, "${aws_s3_bucket.docs.arn}/*"]
    }]
  })
}

resource "aws_iam_instance_profile" "web" {
  name = "syncdoc-web-profile"
  role = aws_iam_role.web.name

  depends_on = [aws_iam_role.web]
}

# ── DNS & TLS ─────────────────────────────────────────────

resource "aws_acm_certificate" "cert" {
  domain_name       = "syncdoc.example.com"
  validation_method = "DNS"

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_route53_zone" "main" {
  name = "syncdoc.example.com"
}

resource "aws_route53_record" "app" {
  zone_id = aws_route53_zone.main.zone_id
  name    = "syncdoc.example.com"
  type    = "A"

  depends_on = [aws_route53_zone.main, aws_lb.main]

  alias {
    name                   = aws_lb.main.dns_name
    zone_id                = aws_lb.main.zone_id
    evaluate_target_health = true
  }
}

# ── Monitoring ────────────────────────────────────────────

resource "aws_cloudwatch_metric_alarm" "cpu_high" {
  alarm_name          = "web-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  alarm_actions       = [aws_sns_topic.alerts.arn]

  depends_on = [aws_sns_topic.alerts, aws_autoscaling_group.web]

  dimensions = {
    AutoScalingGroupName = aws_autoscaling_group.web.name
  }
}

resource "aws_sns_topic" "alerts" {
  name = "syncdoc-alerts"
}

# ── Outputs ───────────────────────────────────────────────

output "instance_ip" {
  description = "Public IP of the web instance"
  value       = aws_instance.web.public_ip
}

output "alb_dns" {
  description = "ALB DNS name"
  value       = aws_lb.main.dns_name
}

output "db_endpoint" {
  description = "RDS endpoint"
  value       = aws_db_instance.postgres.endpoint
}

output "redis_endpoint" {
  description = "ElastiCache endpoint"
  value       = aws_elasticache_replication_group.redis.primary_endpoint_address
}

output "docs_bucket" {
  description = "S3 bucket for generated docs"
  value       = aws_s3_bucket.docs.bucket
}
