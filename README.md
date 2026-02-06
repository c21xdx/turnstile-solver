# Turnstile Solver

独立的 Cloudflare Turnstile 验证码解决服务，使用 Camoufox 浏览器自动解决验证码。

## 特性

- 🦊 使用 Camoufox 反检测浏览器
- 🚀 HTTP API，供任何项目调用
- 🐳 Docker 支持，一键部署
- 🔐 API Key 认证
- 💡 浏览器池，支持并发请求

## Docker 部署 (推荐)

### 快速启动

```bash
# 不需要认证
docker run -d -p 5072:5072 --shm-size=512m \
  --name turnstile-solver \
  c21xdx/turnstile-solver

# 启用 API Key 认证 (推荐)
docker run -d -p 5072:5072 --shm-size=512m \
  --name turnstile-solver \
  -e API_KEY="your-secret-key" \
  c21xdx/turnstile-solver
```

### 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `API_KEY` | 空 | API Key，设置后请求必须携带 |
| `THREAD_COUNT` | 2 | 浏览器线程数 |

### 资源需求

| 线程数 | 内存 | CPU |
|--------|------|-----|
| 1 | ~300 MB | 1核 |
| 2 | ~700 MB | 2核 |
| 4 | ~1.2 GB | 2核 |

### Docker Compose

```yaml
version: '3.8'

services:
  turnstile-solver:
    image: c21xdx/turnstile-solver
    container_name: turnstile-solver
    ports:
      - "5072:5072"
    environment:
      - API_KEY=your-secret-key
      - THREAD_COUNT=1
    shm_size: '512m'
    restart: unless-stopped
```

## 本地安装

```bash
# 克隆项目
git clone https://github.com/c21xdx/turnstile-solver.git
cd turnstile-solver

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate  # Linux/Mac

# 安装依赖
pip install -r requirements.txt

# 下载 Camoufox 浏览器
python -m camoufox fetch

# 启动服务
python api_solver.py --browser_type camoufox --thread 1

# 启用 API Key
python api_solver.py --browser_type camoufox --thread 1 --api-key your-secret-key
```

## API 文档

### 认证方式

如果设置了 `API_KEY`，请求时需要携带：

```bash
# 方式1: Header
curl -H "X-API-Key: your-secret-key" "http://localhost:5072/turnstile?..."

# 方式2: URL 参数
curl "http://localhost:5072/turnstile?...&key=your-secret-key"
```

### 创建任务

```http
GET /turnstile?url=https://example.com&sitekey=0x4AAAAAAxxxxxx
```

响应:
```json
{
    "errorId": 0,
    "taskId": "550e8400-e29b-41d4-a716-446655440000"
}
```

### 获取结果

```http
GET /result?id=550e8400-e29b-41d4-a716-446655440000
```

响应 (处理中):
```json
{
    "errorId": 0,
    "status": "processing"
}
```

响应 (成功):
```json
{
    "errorId": 0,
    "status": "ready",
    "solution": {
        "token": "0.xxxxxxxx"
    }
}
```

### 健康检查

```http
GET /health
```

响应:
```json
{
    "status": "ok",
    "pool_size": 1,
    "thread_count": 1,
    "browser_type": "camoufox"
}
```

## 客户端示例

### Python

```python
import time
import requests

SOLVER_URL = "http://127.0.0.1:5072"
API_KEY = "your-secret-key"  # 留空则不验证

def solve_turnstile(url: str, sitekey: str, timeout: int = 60) -> str:
    headers = {"X-API-Key": API_KEY} if API_KEY else {}
    
    # 创建任务
    resp = requests.get(
        f"{SOLVER_URL}/turnstile",
        params={"url": url, "sitekey": sitekey},
        headers=headers
    )
    task_id = resp.json()["taskId"]
    
    # 等待结果
    start = time.time()
    while time.time() - start < timeout:
        resp = requests.get(
            f"{SOLVER_URL}/result",
            params={"id": task_id},
            headers=headers
        )
        data = resp.json()
        
        if data.get("status") == "ready":
            return data["solution"]["token"]
        
        time.sleep(2)
    
    raise Exception("Timeout")

# 使用示例
token = solve_turnstile(
    url="https://example.com",
    sitekey="0x4AAAAAAAxxxxxx"
)
print(f"Token: {token}")
```

### cURL

```bash
# 创建任务
curl -H "X-API-Key: your-secret-key" \
  "http://127.0.0.1:5072/turnstile?url=https://example.com&sitekey=0x4AAA..."

# 获取结果
curl -H "X-API-Key: your-secret-key" \
  "http://127.0.0.1:5072/result?id=xxx"
```

## 命令行参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--port` | 5072 | 监听端口 |
| `--host` | 0.0.0.0 | 监听地址 |
| `--thread` | 4 | 浏览器池大小 |
| `--browser_type` | chromium | 浏览器类型 (camoufox/chromium/chrome) |
| `--api-key` | 空 | API Key，设置后需要认证 |
| `--no-headless` | false | 显示浏览器窗口 |
| `--debug` | false | 调试模式 |

## 许可证

MIT License

## 致谢

基于 [D3vin](https://github.com/D3-vin) 的原版本开发。
