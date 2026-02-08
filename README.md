# Turnstile Solver (Leapcell) - HTTP/SOCKS5 Proxy

支持 HTTP 和 SOCKS5 代理的 Cloudflare Turnstile 验证码解决服务。

## 代理格式

```
http://ip:port
http://user:pass@ip:port
https://ip:port
https://user:pass@ip:port
socks4://ip:port
socks5://ip:port
socks5://user:pass@ip:port
```

## API

```bash
# 带 SOCKS5 代理
curl -H "X-API-Key: key" \
  "https://domain/turnstile?url=https://example.com&sitekey=xxx&proxy=socks5://user:pass@ip:port"

# 带 HTTP 代理
curl -H "X-API-Key: key" \
  "https://domain/turnstile?url=https://example.com&sitekey=xxx&proxy=http://ip:port"
```

## 环境变量

| 变量 | 说明 |
|------|------|
| `API_KEY` | API 密钥 |
| `PROXY` | 默认代理 |
| `DEBUG` | 调试日志 (true/false) |
| `TIMEOUT` | 超时毫秒 (默认 90000) |

## 部署

1. Leapcell → 创建服务
2. 仓库: `c21xdx/turnstile-solver`
3. 分支: `leapcell`
4. 设置环境变量

## License

MIT
