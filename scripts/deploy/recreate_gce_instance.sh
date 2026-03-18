#!/usr/bin/env bash
# recreate_gce_instance.sh — 一键在 GCE 上重建全栈实例
# 用法: ./scripts/deploy/recreate_gce_instance.sh [--project PROJECT_ID] [--zone ZONE] [--instance INSTANCE_NAME] [--scopes SCOPE1,SCOPE2] [--force-delete-instance] [--force-replace-app-dir]
# 依赖: gcloud CLI 已安装并已 auth login
set -euo pipefail

# ── 默认参数（仅 CLI 覆盖）───────────────────────────────────────────────────
GCP_PROJECT=""
GCP_ZONE="us-west1-b"
INSTANCE_NAME="vd-prod"
MACHINE_TYPE="e2-standard-2"
DISK_SIZE="50GB"
IMAGE_FAMILY="debian-12"
IMAGE_PROJECT="debian-cloud"
GITHUB_REPO_URL=""  # e.g. git@github.com:your-org/your-repo.git
FORCE_DELETE_INSTANCE="0"
FORCE_REPLACE_APP_DIR="0"
DEFAULT_INSTANCE_SCOPES="https://www.googleapis.com/auth/devstorage.read_only,https://www.googleapis.com/auth/logging.write,https://www.googleapis.com/auth/monitoring.write,https://www.googleapis.com/auth/service.management.readonly,https://www.googleapis.com/auth/servicecontrol,https://www.googleapis.com/auth/trace.append"
INSTANCE_SCOPES="$DEFAULT_INSTANCE_SCOPES"

log() { printf '\033[1;36m[gce-recreate]\033[0m %s\n' "$*" >&2; }
fail() { printf '\033[1;31m[gce-recreate] ERROR:\033[0m %s\n' "$*" >&2; exit 1; }

# ── Parse flags ───────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --project)  GCP_PROJECT="$2"; shift 2 ;;
    --zone)     GCP_ZONE="$2"; shift 2 ;;
    --instance) INSTANCE_NAME="$2"; shift 2 ;;
    --machine)  MACHINE_TYPE="$2"; shift 2 ;;
    --disk-size) DISK_SIZE="$2"; shift 2 ;;
    --image-family) IMAGE_FAMILY="$2"; shift 2 ;;
    --image-project) IMAGE_PROJECT="$2"; shift 2 ;;
    --scopes)   INSTANCE_SCOPES="$2"; shift 2 ;;
    --repo)     GITHUB_REPO_URL="$2"; shift 2 ;;
    --force-delete-instance) FORCE_DELETE_INSTANCE=1; shift ;;
    --force-replace-app-dir) FORCE_REPLACE_APP_DIR=1; shift ;;
    -h|--help)
      cat <<'USAGE'
Usage: scripts/deploy/recreate_gce_instance.sh [options]
  --project <id>
  --zone <zone>
  --instance <name>
  --machine <type>
  --disk-size <size>
  --image-family <family>
  --image-project <project>
  --scopes <scope_csv>   # Default: minimal GCE runtime scopes. Set cloud-platform to keep legacy behavior.
  --repo <github-url>
  --force-delete-instance
  --force-replace-app-dir
USAGE
      exit 0
      ;;
    *) fail "unknown flag: $1" ;;
  esac
done

[[ -z "$GCP_PROJECT" ]] && GCP_PROJECT="$(gcloud config get-value project 2>/dev/null)" || true
[[ -z "$GCP_PROJECT" ]] && fail "GCP_PROJECT not set. Pass --project or run: gcloud config set project YOUR_PROJECT"

log "Project : $GCP_PROJECT"
log "Zone    : $GCP_ZONE"
log "Instance: $INSTANCE_NAME"
log "Machine : $MACHINE_TYPE"
log "Scopes  : $INSTANCE_SCOPES"

validate_repo_url() {
  local value="$1"
  [[ -n "$value" ]] || return 0
  [[ "$value" =~ ^https://github\.com/[A-Za-z0-9._-]+/[A-Za-z0-9._-]+(\.git)?$ ]] && return 0
  [[ "$value" =~ ^git@github\.com:[A-Za-z0-9._-]+/[A-Za-z0-9._-]+(\.git)?$ ]] && return 0
  fail "invalid --repo URL: must be a GitHub https://github.com/org/repo(.git) or git@github.com:org/repo(.git)"
}

validate_repo_url "$GITHUB_REPO_URL"

if [[ "$FORCE_DELETE_INSTANCE" != "0" && "$FORCE_DELETE_INSTANCE" != "1" ]]; then
  fail "--force-delete-instance parser error"
fi
if [[ "$FORCE_REPLACE_APP_DIR" != "0" && "$FORCE_REPLACE_APP_DIR" != "1" ]]; then
  fail "--force-replace-app-dir parser error"
fi

# ── Step 1: Delete old instance (if exists) ───────────────────────────────────
if gcloud compute instances describe "$INSTANCE_NAME" \
    --project="$GCP_PROJECT" --zone="$GCP_ZONE" &>/dev/null; then
  if [[ "$FORCE_DELETE_INSTANCE" != "1" ]]; then
    fail "instance '$INSTANCE_NAME' already exists. Re-run with --force-delete-instance to allow deletion."
  fi
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
  --scopes="$INSTANCE_SCOPES"

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
apt-get install -y -qq git curl nginx postgresql postgresql-contrib python3-pip python3-venv docker.io docker-compose

# Install uv (Python package manager) with pinned version + checksum validation.
UV_VERSION="0.10.7"
case "$(uname -m)" in
  x86_64|amd64)
    UV_TARGET="uv-x86_64-unknown-linux-gnu"
    UV_SHA256="9ac6cee4e379a5abfca06e78a777b26b7ba1f81cb7935b97054d80d85ac00774"
    ;;
  aarch64|arm64)
    UV_TARGET="uv-aarch64-unknown-linux-gnu"
    UV_SHA256="20efc27d946860093650bcf26096a016b10fdaf03b13c33b75fbde02962beea9"
    ;;
  *)
    echo "unsupported architecture for uv: $(uname -m)" >&2
    exit 1
    ;;
esac
UV_ARCHIVE="${UV_TARGET}.tar.gz"
UV_URL="https://github.com/astral-sh/uv/releases/download/${UV_VERSION}/${UV_ARCHIVE}"
curl -fsSL "${UV_URL}" -o "/tmp/${UV_ARCHIVE}"
echo "${UV_SHA256}  /tmp/${UV_ARCHIVE}" | sha256sum -c -
tar -xzf "/tmp/${UV_ARCHIVE}" -C /tmp
mkdir -p "$HOME/.local/bin"
install -m 0755 "/tmp/${UV_TARGET}/uv" "$HOME/.local/bin/uv"
if [[ -f "/tmp/${UV_TARGET}/uvx" ]]; then
  install -m 0755 "/tmp/${UV_TARGET}/uvx" "$HOME/.local/bin/uvx"
fi
export PATH="$HOME/.local/bin:$PATH"

# Enable & start services
systemctl enable docker postgresql nginx
systemctl start docker postgresql nginx
STARTUP
)"

log "Running bootstrap on instance …"
gcloud compute ssh "$INSTANCE_NAME" \
  --project="$GCP_PROJECT" --zone="$GCP_ZONE" \
  --command="$STARTUP_SCRIPT" --quiet

# ── Step 6: Clone repo (if URL provided) ─────────────────────────────────────
if [[ -n "$GITHUB_REPO_URL" ]]; then
  log "Cloning repo from $GITHUB_REPO_URL …"
  REMOTE_REPO_URL_Q="$(printf '%q' "$GITHUB_REPO_URL")"
  REMOTE_FORCE_REPLACE_Q="$(printf '%q' "$FORCE_REPLACE_APP_DIR")"
  gcloud compute ssh "$INSTANCE_NAME" \
    --project="$GCP_PROJECT" --zone="$GCP_ZONE" --quiet \
    --command="set -euo pipefail;
      GITHUB_REPO_URL=${REMOTE_REPO_URL_Q};
      FORCE_REPLACE_APP_DIR=${REMOTE_FORCE_REPLACE_Q};
      if [[ -d \"\$HOME/app\" ]]; then
        if [[ \"\$FORCE_REPLACE_APP_DIR\" != \"1\" ]]; then
          echo 'Refusing to remove \$HOME/app without --force-replace-app-dir.' >&2;
          exit 12;
        fi
        rm -rf -- \"\$HOME/app\";
      fi;
      git clone -- \"\$GITHUB_REPO_URL\" \"\$HOME/app\";
      cd \"\$HOME/app\";
      echo 'Repo cloned. Next steps:';
      echo '  1. cp .env.example .env && edit .env with your secrets';
      echo '  2. ./scripts/bootstrap_full_stack.sh';
      echo '  3. sudo cp infra/systemd/*.service /etc/systemd/system/';
      echo '  4. sudo systemctl daemon-reload && sudo systemctl enable vd-api vd-worker vd-web';
      echo '  5. sudo cp infra/nginx/vd.conf /etc/nginx/sites-available/vd && sudo nginx -t && sudo systemctl reload nginx';"
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
