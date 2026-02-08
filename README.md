# Turnstile Solver (Leapcell Python)

Cloudflare Turnstile 验证码解决服务 - Python Serverless 版本，使用 Playwright + Chromium。

## 特性

- 🌐 **Playwright + Chromium** - 与 Leapcell 官方示例相同的技术栈
- 🚀 **Serverless 部署** - 专为 Leapcell 优化
- 🔐 **API Key 认证** - 可选的安全保护
- ⚡ **同步 API** - 请求等待结果返回
- 🛡️ **反检测脚本** - 隐藏 webdriver 等特征

## API 端点

### GET /turnstile

同步解决验证码，等待完成后返回结果。

```bash
curl -H "X-API-Key: your-key" \
  "https://your-domain/turnstile?url=https://example.com&sitekey=0x4AAA..."
```

参数:
- `url` (必需) - 目标页面 URL
- `sitekey` (必需) - Turnstile sitekey
- `action` (可选) - Action 参数
- `cdata` (可选) - 自定义数据

响应:
```json
{
  "errorId": 0,
  "status": "ready",
  "solution": {
    "token": "0.xxxxx..."
  },
  "elapsed": 12.34
}
```

### GET /health

健康检查。

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `API_KEY` | 空 | API 密钥，设置后需要认证 |
| `DEBUG` | false | 开启调试日志 |
| `TIMEOUT` | 60 | 超时时间 (秒) |

## 部署到 Leapcell

1. 在 Leapcell 后台创建新服务
2. 连接 GitHub 仓库 `c21xdx/turnstile-solver`
3. **选择分支**: `leapcell-python`
4. 设置环境变量：`API_KEY`
5. 部署

## 认证

```bash
# Header 方式
curl -H "X-API-Key: your-key" "https://your-domain/turnstile?..."

# URL 参数方式
curl "https://your-domain/turnstile?...&key=your-key"
```

## 调用间隔建议

| 场景 | 建议间隔 |
|------|----------|
| 正常使用 | 10-30 秒 |
| 保守使用 | 60 秒 |

## License

MIT
