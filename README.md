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

规则源的唯一编辑入口是 `rules-source.json`。网页中的“配置转换器”可以直接生成并下载最新的 `Clash JS` 与 `Shadowrocket` 配置；仓库内现有的 `clash.js` 与 `shadowrocket.conf` 是已生成的静态示例。

## DNS 策略

`rules-source.json` 中的 `mihomo_dns` 会写入 Clash JS，使用加密 DoH 作为主解析和 Fallback，并单独配置代理节点解析 DNS；Fake-IP 排除局域网、NTP、STUN 等必须返回真实地址的场景。`shadowrocket_dns` 会生成对应的 `dns-server`、`fallback-dns-server` 和 `proxy-dns-server`，关闭系统 DNS 回退、关闭 IPv6 DNS 响应，并劫持常见硬编码 DNS，减少明文 DNS 泄漏。

规则生成器底部的“DNS 与 Fallback DNS”面板可以分别编辑 Mihomo 和 Shadowrocket 的开关、DNS 列表、Fallback 列表、Fake-IP 排除规则及 DNS 劫持规则；生成配置前会保留这些修改。主 DNS 建议使用至少两个 HTTPS DoH，Fallback 使用不同服务商，避免单一服务故障。
