# 完整堆栈 GCE 部署指南

本文档覆盖在 Google Cloud Compute Engine (GCE) 上部署完整 Video Digestor 堆栈的端到端流程。

> 如果只需部署 Miniflux + Nextflux Reader 层，参见 [`miniflux-nextflux-gce.md`](miniflux-nextflux-gce.md)。

---

## 架构概览

```
Internet
  │
  ▼ 80/443
[ nginx ]  (反代)
  ├── /api/*   → localhost:8000  (FastAPI, vd-api.service)
  └── /*       → localhost:3001  (Next.js, vd-web.service)

[ vd-worker.service ]  (Temporal Worker, 无端口)

Docker Compose (core-services):
  ├── postgres:5432
  ├── redis:6379
  └── temporal:7233

可选 Docker Compose (reader-stack):
  ├── miniflux:8080
  └── nextflux:3000
```

---

## 1. 创建 GCE VM

推荐规格：

| 项目 | 推荐值 |
|------|--------|
| 机型 | e2-standard-2（2vCPU / 8GB RAM）|
| 操作系统 | Ubuntu 22.04 LTS |
| 磁盘 | 30 GB SSD（含 Docker 镜像 + DB 数据）|
| 区域 | 选择离主要用户最近的区域 |

```bash
# 用 gcloud 创建（按需调整参数）
gcloud compute instances create vd-server \
  --machine-type=e2-standard-2 \
  --image-family=ubuntu-2204-lts \
  --image-project=ubuntu-os-cloud \
  --boot-disk-size=30GB \
  --boot-disk-type=pd-ssd \
  --tags=vd-server \
  --zone=us-west1-a
```

可选：使用仓库脚本重建实例（高风险操作默认受保护）：

```bash
./scripts/recreate_gce_instance.sh \
  --project YOUR_PROJECT \
  --zone us-west1-b \
  --instance vd-prod \
  --repo https://github.com/YOUR_ORG/YOUR_REPO.git \
  --force-delete-instance \
  --force-replace-app-dir
```

说明：

- 若实例已存在但未传 `--force-delete-instance`，脚本会拒绝删除并退出。
- 若远端 `~/app` 已存在但未传 `--force-replace-app-dir`，脚本会拒绝覆盖并退出。

---

## 2. 防火墙规则

```bash
# 开放 HTTP / HTTPS（nginx 入口）
gcloud compute firewall-rules create allow-vd-http \
  --allow=tcp:80,tcp:443 \
  --target-tags=vd-server \
  --description="Video Digestor HTTP/HTTPS"

# 可选：SSH（如已有默认 allow-ssh 规则则跳过）
gcloud compute firewall-rules create allow-ssh \
  --allow=tcp:22 \
  --target-tags=vd-server
```

---

## 3. 初始化服务器

```bash
# SSH 进入 VM
gcloud compute ssh vd-server --zone=us-west1-a

# 更新系统
sudo apt-get update && sudo apt-get upgrade -y

# 安装 Docker + Docker Compose
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER

# 安装 Python 工具链
sudo apt-get install -y python3-pip python3-venv git curl
pip3 install uv --user
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc && source ~/.bashrc

# 安装 Node.js 20
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs

# 安装 nginx + certbot
sudo apt-get install -y nginx certbot python3-certbot-nginx

# 创建服务用户
sudo useradd -m -s /bin/bash vd
sudo mkdir -p /opt/vd
sudo chown vd:vd /opt/vd
```

---

## 4. 部署代码

```bash
# 切换到 vd 用户
sudo -u vd -i

# 克隆仓库
git clone https://github.com/YOUR_ORG/YOUR_REPO.git /opt/vd/repo
cd /opt/vd/repo

# 安装 Python 依赖
uv sync --frozen --extra dev

# 安装 Node 依赖 & 构建 Next.js
npm --prefix apps/web ci
npm --prefix apps/web run build
```

---

## 5. 配置环境变量

```bash
# 复制模板并填写生产值
cp /opt/vd/repo/.env.example /opt/vd/.env

# 编辑关键配置
nano /opt/vd/.env
```

**生产环境必填项（与本地开发不同的部分）**：

```bash
# 数据库（指向 Docker Compose 里的 postgres）
export DATABASE_URL='postgresql+psycopg://postgres:YOUR_DB_PASS@127.0.0.1:5432/video_analysis'

# 时间节点
export TEMPORAL_TARGET_HOST='127.0.0.1:7233'

export NEXT_PUBLIC_API_BASE_URL='https://YOUR_DOMAIN'

# Gemini
export GEMINI_API_KEY='YOUR_KEY'

# 邮件通知（可选）
export NOTIFICATION_ENABLED='true'
export RESEND_API_KEY='YOUR_RESEND_KEY'
export RESEND_FROM_EMAIL='digest@YOUR_DOMAIN'

# RSSHub fallback 节点（运行 probe 脚本自动写入）
# python3 scripts/probe_rsshub_health.py --write-env --env-file /opt/vd/.env
```

---

## 6. 启动核心服务（Docker Compose）

```bash
cd /opt/vd/repo

# 启动 Postgres / Redis / Temporal
sudo docker compose -f infra/compose/core-services.compose.yml up -d

# 等待 postgres 健康
sudo docker compose -f infra/compose/core-services.compose.yml ps

# 执行数据库迁移
source /opt/vd/.env
for f in $(ls infra/migrations/*.sql | sort); do
    echo "Running $f…"
    psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f "$f"
done

# 初始化 SQLite 状态库
sqlite3 "$SQLITE_PATH" < infra/sql/sqlite_state_init.sql
```

---

## 7. 安装 systemd 服务单元

```bash
# 复制单元文件
sudo cp /opt/vd/repo/infra/systemd/vd-api.service    /etc/systemd/system/
sudo cp /opt/vd/repo/infra/systemd/vd-worker.service  /etc/systemd/system/
sudo cp /opt/vd/repo/infra/systemd/vd-web.service     /etc/systemd/system/

# 重载并启用
sudo systemctl daemon-reload
sudo systemctl enable vd-api vd-worker vd-web
sudo systemctl start  vd-api vd-worker vd-web

# 确认状态
sudo systemctl status vd-api vd-worker vd-web
```

---

## 8. 配置 nginx

```bash
# 复制 nginx 配置
sudo cp /opt/vd/repo/infra/nginx/vd.conf /etc/nginx/sites-available/vd.conf

# 替换域名（或使用 VM 外部 IP 做临时测试）
sudo sed -i 's/YOUR_DOMAIN/YOUR_ACTUAL_DOMAIN_OR_IP/g' /etc/nginx/sites-available/vd.conf

# 启用站点
sudo ln -sf /etc/nginx/sites-available/vd.conf /etc/nginx/sites-enabled/vd.conf
sudo nginx -t && sudo systemctl reload nginx
```

### 8.1 申请 HTTPS 证书（可选但强烈推荐）

```bash
sudo certbot --nginx -d YOUR_DOMAIN
# certbot 会自动修改 nginx 配置并添加 HTTPS 块
sudo systemctl reload nginx
```

---

## 9. 验证部署

```bash
# API 健康检查
curl http://YOUR_DOMAIN/healthz

# 查看服务日志
sudo journalctl -u vd-api    -f --no-pager
sudo journalctl -u vd-worker -f --no-pager
sudo journalctl -u vd-web    -f --no-pager
```

---

## 10. 日常运维

```bash
# 更新代码并重启
cd /opt/vd/repo
git pull
uv sync --frozen
npm --prefix apps/web ci && npm --prefix apps/web run build
sudo systemctl restart vd-api vd-worker vd-web

# 执行新迁移
source /opt/vd/.env
for f in $(ls infra/migrations/*.sql | sort); do
    psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f "$f"
done

# 查看所有服务状态
sudo systemctl status vd-api vd-worker vd-web
sudo docker compose -f /opt/vd/repo/infra/compose/core-services.compose.yml ps

# 刷新 RSSHub fallback 节点排名
source /opt/vd/.env
python3 /opt/vd/repo/scripts/probe_rsshub_health.py --write-env --env-file /opt/vd/.env
sudo systemctl restart vd-worker
```

---

## 11. 可选：部署 Reader Stack（Miniflux + Nextflux）

```bash
sudo docker compose -f /opt/vd/repo/infra/compose/miniflux-nextflux.compose.yml up -d
```

详见 [`miniflux-nextflux-gce.md`](miniflux-nextflux-gce.md)。

---

## 端口清单

| 服务 | 监听地址 | 对外暴露 |
|------|----------|---------|
| nginx | 0.0.0.0:80/443 | 是（HTTP/HTTPS 入口）|
| FastAPI (vd-api) | 127.0.0.1:8000 | 否（仅通过 nginx /api/）|
| Next.js (vd-web) | 127.0.0.1:3001 | 否（仅通过 nginx /）|
| PostgreSQL | 127.0.0.1:5432 | 否 |
| Redis | 127.0.0.1:6379 | 否 |
| Temporal | 127.0.0.1:7233 | 否 |
| Miniflux（可选）| 0.0.0.0:8080 | 是（如启用）|
| Nextflux（可选）| 0.0.0.0:3000 | 是（如启用）|
