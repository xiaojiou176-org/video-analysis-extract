# Miniflux + Nextflux on GCE (Optional Reader Stack)

## What This Adds
- `Miniflux`: storage/sync/API layer for feeds.
- `Nextflux`: modern web UI on top of Miniflux.
- Keeps this repo as your AI processing pipeline, while reader UI runs as optional companion services.

## 1) Prepare Server
1. SSH into your GCE VM.
2. Install Docker + Docker Compose (if missing).
3. Clone this repo to the VM.

## 2) Create Reader Stack Env
Create a local reader env from template:

```bash
cp env/profiles/reader.env env/profiles/reader.local.env
```

Then edit at least:

```bash
MINIFLUX_DB_PASSWORD=<strong-password>
MINIFLUX_ADMIN_PASSWORD=<strong-password>
MINIFLUX_BASE_URL=http://<YOUR_VM_PUBLIC_IP>:8080
MINIFLUX_PORT=8080
NEXTFLUX_PORT=3000
```

## 3) Start Stack

```bash
./scripts/deploy_reader_stack.sh up --env-file env/profiles/reader.local.env
./scripts/deploy_reader_stack.sh status --env-file env/profiles/reader.local.env
```

## 4) GCE Firewall
Open inbound TCP ports:
- `8080` for Miniflux
- `3000` for Nextflux

You can do this in GCP Console (VPC Network -> Firewall), or with `gcloud`.

## 5) First Login
1. Open `http://<YOUR_VM_PUBLIC_IP>:8080` and log in to Miniflux.
2. Open `http://<YOUR_VM_PUBLIC_IP>:3000` and log in via Miniflux endpoint:
   - Server URL: `http://<YOUR_VM_PUBLIC_IP>:8080`
   - Username/password: your Miniflux admin account.

## 6) Connect with This Repo
Two practical modes:
1. Keep this repo as ingest/AI/notify pipeline; manually add RSS feeds in Miniflux.
2. Extend this repo later to write AI-processed entries into Miniflux API for "AI text first" reading.

## 7) Production Recommendation
- Put Caddy/Nginx in front and use HTTPS.
- Update `MINIFLUX_BASE_URL` to final HTTPS domain.
- Avoid exposing plain HTTP on public internet long-term.

## 8) Operations

```bash
./scripts/deploy_reader_stack.sh logs --env-file env/profiles/reader.local.env
./scripts/deploy_reader_stack.sh restart --env-file env/profiles/reader.local.env
./scripts/deploy_reader_stack.sh down --env-file env/profiles/reader.local.env
```
