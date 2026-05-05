# Release Workflow

`syncdoc-free` is the source of truth for SyncDoc application code.

This repo owns:

- backend and frontend feature development
- feature branches and pull requests
- CI validation
- Docker Hub image publishing
- release tags

This repo does not own:

- Hetzner deployment automation
- private runtime secrets
- production infrastructure configuration

## Development Flow

1. Create a feature branch from `main`.
2. Develop and test locally.
3. Open a pull request and validate CI.
4. Merge to `main` after approval or local validation.
5. Publish Docker images from `main` or from a release tag.
6. Deploy those images from the private deployment repo.

## Local Validation

Recommended checks before merging:

```bash
cd frontend
npm run lint
npx tsc --noEmit

cd ../backend
ruff check .
ruff format . --check
pytest -v
```

Also validate the full application locally with Docker Compose or your preferred local stack.

## Publishing

### Simple Flow

Use the `main` image tags:

1. Merge tested code to `main`.
2. Run the `Publish Docker Images` workflow.
3. The private repo can deploy `syncdoc-api:main` and `syncdoc-frontend:main`.

This is the fastest path, but `main` is a floating release target.

### Preferred Flow

Use versioned tags such as `v0.1.1`:

1. Merge tested code to `main`.
2. Create and push a release tag.
3. Confirm Docker Hub published the backend and frontend images for that tag.
4. Update the private deployment repo to use that exact tag or digest.
5. Deploy to Hetzner from the private repo.

## Boundary With The Private Repo

If a change affects product behavior, backend logic, frontend UI, or tests, it belongs here.

If a change affects:

- Hetzner
- Traefik
- Cloudflared
- Doppler service-token usage
- deployment workflows

it belongs in the private `syncdoc` repo.
