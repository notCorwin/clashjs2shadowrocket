# Clash JS / Shadowrocket 规则生成器

这是一个无需后端和构建工具的静态页面。默认以“规则生成器”为主入口，内置 AI、Google、流媒体、Apple、局域网直连等分流策略，以及东南亚/美国自动测速节点组；选择策略后即可生成 `Clash JS` 和 `Shadowrocket` 配置。

“配置转换器”作为次要入口保留，用于导入或直接编辑完整的 `rules-source.json`，适合高级用户维护自定义规则。两个面板共用同一份规则源：切换面板时当前面板的编辑结果会先写回规则源，所以来回切不会丢改动。

`rules-source.json` 是一份通用示例。自己的日常配置建议用页面上的“导出规则源”存成本地文件（`rules-source.local.json` 已被 gitignore），需要时再用“导入 JSON”载入，避免把个人网段、内网 DNS 提交进仓库。

## 本地预览

默认规则通过 `fetch` 加载，用 `file://` 直接打开会被浏览器拦截，需要静态服务器：

```bash
python3 -m http.server 8000
```

然后打开 <http://localhost:8000>。用手机通过局域网 IP 访问时页面仍可用，但浏览器只在 HTTPS/localhost 下提供剪贴板 API，“复制”会退回为全选并提示手动复制。

## 自检

改完 `app.js` 或 `rules-source.json` 后跑一次（零依赖）：

```bash
node check.mjs
```

它会校验出厂规则源、IPv6 网段生成 `IP-CIDR6`、订阅自带规则排在 `MATCH` 之前、停用的策略组不进输出、关键词不误伤无关域名、私有地址不指向代理，以及节点组改名后引用同步。

## GitHub Pages

在仓库 Settings → Pages 中选择部署分支的根目录（`/ (root)`）。提交 `index.html`、`app.js`、`style.css` 和 `rules-source.json` 后，GitHub Pages 会直接提供页面。Pages 对静态资源默认缓存约 10 分钟，改动上线后稍等即可，不需要手动加版本号。

## DNS 策略

DNS 分成两份，各管一边：

- **国外 DoH（代理域名）**：写入 Clash 的 `nameserver` / `proxy-server-nameserver` 和 Shadowrocket 的 `dns-server` / `fallback-dns-server` / `proxy-dns-server`。默认 Cloudflare + Google，用 IP 形式的 DoH，避免解析 DoH 域名本身时再被污染。
- **国内 DoH（直连域名）**：写入 Clash 的 `direct-nameserver`；Shadowrocket 没有对应字段，改为 `dns-direct-system = true`，交给系统 DNS。如果直连域名也用国外 DNS，国内站点会被调度到远端 CDN，直连反而更慢。

Fake-IP 排除局域网、NTP、STUN 等必须返回真实地址的场景；`hijack-dns` 拦截常见硬编码 DNS，减少明文 DNS 泄漏。生成器底部的 DNS 面板只维护上面这两份列表，其余字段沿用规则源里的取值，导入的配置不会被覆盖。
