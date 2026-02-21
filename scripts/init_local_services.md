# Init Local Services (Non-Docker)

本文件只初始化本地依赖服务，不启动 API/Worker/MCP。

## 1) 安装依赖
```bash
brew update
brew install postgresql@16 redis temporal
```

## 2) 启动 PostgreSQL + Redis
```bash
brew services start postgresql@16
brew services start redis
```

## 3) 初始化数据库
```bash
createdb video_analysis || true
```

如果你希望使用固定账号口令，也可以自行创建角色并授权。

## 4) 启动 Temporal Dev Server
```bash
temporal server start-dev --ip 127.0.0.1 --port 7233
```

建议在单独终端运行并保持前台常驻。

## 5) 环境变量建议
```bash
export DATABASE_URL='postgresql+psycopg://localhost:5432/video_analysis'
export TEMPORAL_TARGET_HOST='127.0.0.1:7233'
export TEMPORAL_NAMESPACE='default'
export TEMPORAL_TASK_QUEUE='video-analysis-worker'
export SQLITE_STATE_PATH="$HOME/.video-digestor/state/worker_state.db"
export SQLITE_PATH="$HOME/.video-digestor/state/worker_state.db"
export VD_API_BASE_URL='http://127.0.0.1:8000'
```

## 6) 停止服务
```bash
brew services stop postgresql@16
brew services stop redis
```

Temporal Dev Server 在其终端 `Ctrl+C` 停止。
