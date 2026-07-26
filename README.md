# Clash JS / Shadowrocket 规则生成器

这是一个无需后端和构建工具的静态页面。默认以“规则生成器”为主入口，内置 AI、Google、GitHub、流媒体、国内直连等分流策略，以及东南亚/美国自动测速节点组；选择策略后即可生成 `Clash JS` 和 `Shadowrocket` 配置。

“配置转换器”作为次要入口保留，用于导入或直接编辑完整的 `rules-source.json`，适合高级用户维护自定义规则。

## 本地预览

由于浏览器限制，默认规则通过 `fetch` 加载，建议使用静态服务器预览：

```bash
python3 -m http.server 8000
```

然后打开 <http://localhost:8000>。

## GitHub Pages

在仓库 Settings → Pages 中选择部署分支的根目录（`/ (root)`）。提交 `index.html`、`app.js`、`style.css` 和 `rules-source.json` 后，GitHub Pages 会直接提供页面。

规则源的唯一编辑入口是 `rules-source.json`；`clash.js` 与 `shadowrocket.conf` 仍可通过原有的 Python 生成器生成：

```bash
python3 rules_generator.py --check
python3 rules_generator.py
```

## DNS 策略

`rules-source.json` 中的 `mihomo_dns` 会写入 Clash JS，使用国内 DoH 作为主解析、Cloudflare/Google DoH 作为 Fallback，并单独配置代理节点引导解析；局域网和直连域名保留系统解析以兼容路由器及内网服务。`shadowrocket_dns` 会生成相同取舍的 `dns-server`、`fallback-dns-server` 和 `proxy-dns-server`，同时关闭系统 DNS 回退、关闭 IPv6 DNS 响应，并劫持常见硬编码 DNS，减少明文 DNS 泄漏。
