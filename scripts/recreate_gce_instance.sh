#!/usr/bin/env bash
# recreate_gce_instance.sh — 一键在 GCE 上重建全栈实例
# 用法: ./scripts/recreate_gce_instance.sh [--project PROJECT_ID] [--zone ZONE] [--instance INSTANCE_NAME]
# 依赖: gcloud CLI 已安装并已 auth login
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# ── 默认参数（可通过 CLI flags 覆盖）──────────────────────────────────────────
GCP_PROJECT="${GCP_PROJECT:-}"
GCP_ZONE="${GCP_ZONE:-us-west1-b}"
INSTANCE_NAME="${INSTANCE_NAME:-vd-prod}"
MACHINE_TYPE="${MACHINE_TYPE:-e2-standard-2}"
DISK_SIZE="${DISK_SIZE:-50GB}"
IMAGE_FAMILY="${IMAGE_FAMILY:-debian-12}"
IMAGE_PROJECT="${IMAGE_PROJECT:-debian-cloud}"
GITHUB_REPO_URL="${GITHUB_REPO_URL:-}"  # e.g. git@github.com:your-org/your-repo.git

log() { printf '\033[1;36m[gce-recreate]\033[0m %s\n' "$*" >&2; }
fail() { printf '\033[1;31m[gce-recreate] ERROR:\033[0m %s\n' "$*" >&2; exit 1; }

# ── Parse flags ───────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --project)  GCP_PROJECT="$2"; shift 2 ;;
    --zone)     GCP_ZONE="$2"; shift 2 ;;
    --instance) INSTANCE_NAME="$2"; shift 2 ;;
    --machine)  MACHINE_TYPE="$2"; shift 2 ;;
    --repo)     GITHUB_REPO_URL="$2"; shift 2 ;;
    *) fail "unknown flag: $1" ;;
  esac
done

[[ -z "$GCP_PROJECT" ]] && GCP_PROJECT="$(gcloud config get-value project 2>/dev/null)" || true
[[ -z "$GCP_PROJECT" ]] && fail "GCP_PROJECT not set. Pass --project or run: gcloud config set project YOUR_PROJECT"

log "Project : $GCP_PROJECT"
log "Zone    : $GCP_ZONE"
log "Instance: $INSTANCE_NAME"
log "Machine : $MACHINE_TYPE"

# ── Step 1: Delete old instance (if exists) ───────────────────────────────────
if gcloud compute instances describe "$INSTANCE_NAME" \
    --project="$GCP_PROJECT" --zone="$GCP_ZONE" &>/dev/null; then
  log "Deleting existing instance '$INSTANCE_NAME' …"
  gcloud compute instances delete "$INSTANCE_NAME" \
    --project="$GCP_PROJECT" --zone="$GCP_ZONE" --quiet
fi

# ── Step 2: Create new instance ───────────────────────────────────────────────
log "Creating instance '$INSTANCE_NAME' …"
gcloud compute instances create "$INSTANCE_NAME" \
  --project="$GCP_PROJECT" \
  --zone="$GCP_ZONE" \
  --machine-type="$MACHINE_TYPE" \
  --boot-disk-size="$DISK_SIZE" \
  --image-family="$IMAGE_FAMILY" \
  --image-project="$IMAGE_PROJECT" \
  --tags="http-server,https-server,vd-api" \
  --scopes="https://www.googleapis.com/auth/cloud-platform"

# ── Step 3: Open firewall (idempotent) ────────────────────────────────────────
log "Ensuring firewall rules …"
gcloud compute firewall-rules create allow-vd-api \
  --project="$GCP_PROJECT" \
  --allow="tcp:8000" \
  --target-tags="vd-api" \
  --description="Video Digestor API port" 2>/dev/null || \
  log "firewall rule 'allow-vd-api' already exists, skipping."

gcloud compute firewall-rules create allow-http-https \
  --project="$GCP_PROJECT" \
  --allow="tcp:80,tcp:443" \
  --target-tags="http-server,https-server" 2>/dev/null || \
  log "firewall rule 'allow-http-https' already exists, skipping."

# ── Step 4: Wait for SSH ──────────────────────────────────────────────────────
log "Waiting for SSH to become available …"
for i in $(seq 1 30); do
  if gcloud compute ssh "$INSTANCE_NAME" \
      --project="$GCP_PROJECT" --zone="$GCP_ZONE" \
      --command="echo ok" --quiet 2>/dev/null; then
    break
  fi
  sleep 5
  [[ $i -eq 30 ]] && fail "SSH did not become available in 150s"
done

# ── Step 5: Bootstrap via startup script ─────────────────────────────────────
STARTUP_SCRIPT="$(cat <<'STARTUP'
#!/usr/bin/env bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

# Install system deps
apt-get update -qq
apt-get install -y -qq git curl nginx postgresql postgresql-contrib redis-server python3-pip python3-venv docker.io docker-compose

# Install uv (Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"

# Enable & start services
systemctl enable docker redis-server postgresql nginx
systemctl start docker redis-server postgresql nginx
STARTUP
)"

log "Running bootstrap on instance …"
gcloud compute ssh "$INSTANCE_NAME" \
  --project="$GCP_PROJECT" --zone="$GCP_ZONE" \
  --command="$STARTUP_SCRIPT" --quiet

# ── Step 6: Clone repo (if URL provided) ─────────────────────────────────────
if [[ -n "$GITHUB_REPO_URL" ]]; then
  log "Cloning repo from $GITHUB_REPO_URL …"
  gcloud compute ssh "$INSTANCE_NAME" \
    --project="$GCP_PROJECT" --zone="$GCP_ZONE" --quiet \
    --command="
      rm -rf ~/app
      git clone '$GITHUB_REPO_URL' ~/app
      cd ~/app
      echo 'Repo cloned. Next steps:'
      echo '  1. cp .env.example .env && edit .env with your secrets'
      echo '  2. ./scripts/bootstrap_full_stack.sh'
      echo '  3. sudo cp infra/systemd/*.service /etc/systemd/system/'
      echo '  4. sudo systemctl daemon-reload && sudo systemctl enable vd-api vd-worker vd-web'
      echo '  5. sudo cp infra/nginx/vd.conf /etc/nginx/sites-available/vd && sudo nginx -t && sudo systemctl reload nginx'
    "
fi

# ── Done ──────────────────────────────────────────────────────────────────────
EXTERNAL_IP="$(gcloud compute instances describe "$INSTANCE_NAME" \
  --project="$GCP_PROJECT" --zone="$GCP_ZONE" \
  --format="get(networkInterfaces[0].accessConfigs[0].natIP)")"

log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log "Instance ready!  External IP: $EXTERNAL_IP"
log ""
log "Next steps:"
log "  1. SSH in: gcloud compute ssh $INSTANCE_NAME --project=$GCP_PROJECT --zone=$GCP_ZONE"
log "  2. cd ~/app && cp .env.example .env  (then fill in secrets)"
log "  3. ./scripts/bootstrap_full_stack.sh"
log "  4. sudo cp infra/systemd/*.service /etc/systemd/system/"
log "  5. sudo systemctl daemon-reload && sudo systemctl enable vd-api vd-worker vd-web"
log "  6. sudo systemctl start vd-api vd-worker vd-web"
log "  7. sudo cp infra/nginx/vd.conf /etc/nginx/sites-available/vd"
log "     sudo ln -sf /etc/nginx/sites-available/vd /etc/nginx/sites-enabled/"
log "     sudo nginx -t && sudo systemctl reload nginx"
log ""
log "  API will be at: http://$EXTERNAL_IP:8000"
log "  Web will be at: http://$EXTERNAL_IP"
log ""
log "  Set GitHub secret LIVE_SMOKE_API_BASE_URL=http://$EXTERNAL_IP:8000"
log "  to enable live smoke CI on main branch pushes."
log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
