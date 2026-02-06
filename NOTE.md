# Turnstile Solver - 开发笔记

## 项目状态

**当前状态**: 基本可用，需要优化

## 文件说明

| 文件 | 说明 | 状态 |
|------|------|------|
| `api_solver.py` | 完整版服务，从 grok 项目复制 | ✅ 可用 |
| `solver.py` | 简化版服务，自己实现 | ⚠️ 有局限性 |
| `client.py` | Python 客户端库 | ✅ 可用 |
| `db_results.py` | 内存数据库 | ✅ 可用 |
| `browser_configs.py` | 浏览器配置 | ✅ 可用 |
| `README.md` | 使用文档 | ✅ 完成 |
| `requirements.txt` | 依赖列表 | ✅ 完成 |

## 两个版本的区别

### api_solver.py (推荐)
- 来自 D3vin 的原项目
- 访问真实目标页面解决 Turnstile
- 功能完整，稳定性好
- 依赖: camoufox, patchright, quart, rich

### solver.py (简化版)
- 自己实现的简化版
- 通过构造 HTML 页面触发 Turnstile
- **局限性**: 不能解决所有网站的 Turnstile
- 依赖: camoufox, quart

## 待完成工作

1. **简化 api_solver.py**
   - 移除不必要的依赖 (patchright, rich)
   - 简化代码结构
   - 保留核心功能

2. **改进 solver.py**
   - 考虑改为访问真实页面的方式
   - 或者放弃，直接用 api_solver.py

3. **Docker 化**
   - 创建 Dockerfile
   - docker-compose.yml

4. **测试**
   - 添加自动化测试
   - 测试不同网站的 Turnstile

## API 接口

```
POST /createTask
  {"websiteURL": "xxx", "websiteKey": "xxx"}
  -> {"taskId": "xxx"}

POST /getTaskResult
  {"taskId": "xxx"}
  -> {"status": "ready", "solution": {"token": "xxx"}}

GET /turnstile?url=xxx&sitekey=xxx  (旧版)
GET /result?id=xxx                   (旧版)
GET /health
```

## 快速启动

```bash
# 安装
cd /home/exedev/zhuce100/turnstile-solver
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m camoufox fetch

# 运行 (使用完整版)
python api_solver.py --browser_type camoufox --thread 1

# 运行 (使用简化版)
python solver.py --port 5072 --thread 1
```

## 相关项目

- `/home/exedev/zhuce100/grok/` - Grok 注册工具，使用此 Turnstile Solver
- `/home/exedev/zhuce100/gpt/` - OpenAI 注册工具，使用 Camoufox 直接注册

## 原作者

api_solver.py 原作者: D3vin
- Telegram: https://t.me/D3_vin
- GitHub: https://github.com/D3-vin
