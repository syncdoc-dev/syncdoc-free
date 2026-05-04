# Build stage
FROM node:24-alpine AS builder

WORKDIR /app

# Build-time version injected into the frontend bundle
ARG APP_VERSION=dev
ENV VITE_APP_VERSION=$APP_VERSION

# Install dependencies
COPY package.json package-lock.json ./
RUN npm ci --legacy-peer-deps

# Build application
COPY . .
RUN npm run build

# Production stage — nginx serves static assets and proxies /api to backend
FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

# Install curl for healthcheck
RUN apk add --no-cache curl

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD curl -f http://localhost/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
