# Turnstile Solver

独立的 Cloudflare Turnstile 验证码解决服务，使用 Camoufox 浏览器自动解决验证码。

## 特性

- 🦊 使用 Camoufox 反检测浏览器
- 🚀 HTTP API，供任何项目调用
- 💡 浏览器池，支持并发请求
- 🔄 兼容旧版 API

## 安装

```bash
# 克隆项目
cd /path/to/turnstile-solver

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# .\venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 下载 Camoufox 浏览器
python -m camoufox fetch
```

## 使用

### 启动服务

```bash
# 基本启动
python solver.py

# 指定端口和浏览器数量
python solver.py --port 5072 --thread 2

# 调试模式 (显示详细日志)
python solver.py --debug

# 显示浏览器窗口 (调试用)
python solver.py --headed
```

### 后台运行

```bash
# Linux
nohup python solver.py --port 5072 --thread 2 > solver.log 2>&1 &

# 停止
pkill -f "python solver.py"
```

## API 文档

### 新版 API (YesCaptcha 兼容风格)

#### 创建任务

```http
POST /createTask
Content-Type: application/json

{
    "websiteURL": "https://example.com",
    "websiteKey": "0x4AAAAAAxxxxxx"
}
```

响应:
```json
{
    "taskId": "550e8400-e29b-41d4-a716-446655440000"
}
```

#### 获取结果

```http
POST /getTaskResult
Content-Type: application/json

{
    "taskId": "550e8400-e29b-41d4-a716-446655440000"
}
```

响应 (处理中):
```json
{
    "status": "processing"
}
```

响应 (成功):
```json
{
    "status": "ready",
    "solution": {
        "token": "0.xxxxxxxx"
    }
}
```

响应 (失败):
```json
{
    "status": "failed",
    "error": "Timeout"
}
```

### 旧版 API (简单风格)

#### 创建任务

```http
GET /turnstile?url=https://example.com&sitekey=0x4AAAAAAxxxxxx
```

响应:
```json
{
    "taskId": "550e8400-e29b-41d4-a716-446655440000"
}
```

#### 获取结果

```http
GET /result?id=550e8400-e29b-41d4-a716-446655440000
```

响应:
```json
{
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
    "pool_size": 2,
    "pending_tasks": 0
}
```

## 客户端示例

### Python

```python
import time
import requests

SOLVER_URL = "http://127.0.0.1:5072"

def solve_turnstile(url: str, sitekey: str, timeout: int = 60) -> str:
    """解决 Turnstile 验证码"""
    # 创建任务
    resp = requests.post(f"{SOLVER_URL}/createTask", json={
        "websiteURL": url,
        "websiteKey": sitekey
    })
    task_id = resp.json()["taskId"]
    
    # 等待结果
    start = time.time()
    while time.time() - start < timeout:
        resp = requests.post(f"{SOLVER_URL}/getTaskResult", json={
            "taskId": task_id
        })
        data = resp.json()
        
        if data["status"] == "ready":
            return data["solution"]["token"]
        elif data["status"] == "failed":
            raise Exception(f"Solve failed: {data.get('error')}")
        
        time.sleep(2)
    
    raise Exception("Timeout")

# 使用示例
token = solve_turnstile(
    url="https://accounts.x.ai",
    sitekey="0x4AAAAAAAhr9JGVDZbrZOo0"
)
print(f"Token: {token}")
```

### cURL

```bash
# 创建任务
curl -X POST http://127.0.0.1:5072/createTask \
  -H "Content-Type: application/json" \
  -d '{"websiteURL": "https://example.com", "websiteKey": "0x4AAA..."}'

# 获取结果
curl -X POST http://127.0.0.1:5072/getTaskResult \
  -H "Content-Type: application/json" \
  -d '{"taskId": "xxx"}'
```

## 配置参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--port` | 5072 | 监听端口 |
| `--host` | 0.0.0.0 | 监听地址 |
| `--thread` | 2 | 浏览器池大小 |
| `--headed` | false | 显示浏览器窗口 |
| `--debug` | false | 调试模式 |

## 注意事项

1. **内存占用**: 每个浏览器实例约占 500MB 内存
2. **超时时间**: 默认 60 秒，复杂验证可能需要更长
3. **并发数**: `--thread` 决定最大并发处理数
4. **结果缓存**: 结果保留 5 分钟后自动清理

## 许可证

MIT License
