# SyncDoc — Open Source

SyncDoc is an infrastructure-as-code (IaC) documentation tool that generates living documentation from your Terraform, Docker, Ansible, and Git configurations. This is the open-source, self-hosted version.

## Features

- **Live Infrastructure Documentation** — Auto-generated docs from your IaC sources
- **Multi-source Support** — Terraform, Docker, Ansible, Git, and CI/CD workflows
- **Dependency Graph** — Visualise service relationships and manual connections
- **Drift Detection** — Detect when infrastructure changes without documentation updates
- **Semantic Search** — Full-text and embedding-based search across resources (requires LLM key)
- **Self-hosted** — Runs entirely on your infrastructure with Docker Compose

## Quick Start

### Prerequisites

- Docker & Docker Compose
- macOS or Linux

### Run from Docker Hub

```bash
git clone https://github.com/syncdoc-dev/syncdoc-free.git
cd syncdoc-free

# Copy environment file and set a strong JWT secret
cp .env.example .env
export JWT_SECRET_KEY="$(openssl rand -hex 32)"

# Start the stack
docker compose up -d

# Wait for migrations (~10s), then open
docker compose logs -f api
open http://localhost:5173        # macOS
xdg-open http://localhost:5173    # Linux
```

The development stack exposes:
- **Frontend**: http://localhost:5173
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

### Production-like setup (no Traefik)

If you want to expose ports directly without a reverse proxy:

```bash
cp .env.example .env
export JWT_SECRET_KEY="$(openssl rand -hex 32)"
docker compose -f docker-compose.simple.yml up -d
```

This uses `syncdocdev/syncdoc-api:latest` and `syncdocdev/syncdoc-frontend:latest` from Docker Hub.

### With Traefik (reverse proxy + SSL)

For deployments with an existing Traefik instance:

```bash
cp .env.example .env
# Set PROD_FRONTEND_URL and PROD_BACKEND_URL in .env
docker compose -f docker-compose.prod.yml up -d
```

## Optional: AI Features

To enable AI-powered documentation generation and semantic search, add your LLM API key:

```env
LLM_PROVIDER=openai          # or "anthropic"
LLM_API_KEY=sk-your-key-here
LLM_MODEL=gpt-4o
```

AI features are gracefully disabled if no API key is provided.

## Optional: GitHub OAuth

To enable GitHub login:

1. Create an OAuth app at https://github.com/settings/developers
2. Set the callback URL to `http://localhost:8000/api/auth/github/callback`
3. Add to `.env`:

```env
GH_CLIENT_ID=your-client-id
GH_CLIENT_SECRET=your-client-secret
```

## Development

See [docs/LOCAL_SETUP.md](docs/LOCAL_SETUP.md) for local development setup without Docker.

## Roadmap / TODO

- [ ] Official Helm chart for Kubernetes deployments
- [ ] Windows development support
- [ ] SDK and API client libraries
- [ ] SOC 2 compliance documentation
- [ ] Prometheus / OpenTelemetry metrics export

## Contributing

We welcome contributions! Please open an issue or pull request on GitHub.

## Community & Support

- **GitHub Issues**: [Report bugs or request features](https://github.com/syncdoc-dev/syncdoc-free/issues)
- **Discussions**: [Community discussions](https://github.com/syncdoc-dev/syncdoc-free/discussions)

## License

[See LICENSE file](LICENSE)
