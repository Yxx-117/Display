# Docsify 知识库仓库（GitHub Pages 版）

基于 Docsify 的零构建文档站骨架：仓库里只有 Markdown + 一个 `index.html`，
推送到 GitHub 后由 GitHub Actions 自动部署到 GitHub Pages。

## 一、站点是怎么跑起来的

不需要编译，也没有构建产物。浏览器打开 `index.html` 后，Docsify 在运行时
按 hash 路由去拉取对应的 `.md` 文件并渲染成页面。

```text
访问 /#/01_产品业务文档/01_快速开始/快速开始
        -> Docsify fetch docsify_root/01_产品业务文档/01_快速开始/快速开始.md
        -> 前端渲染为 HTML
```

因为路由是 hash 模式，服务端不需要任何 rewrite 规则，任何静态托管都能直接放。

## 二、目录结构

```text
.
├── docsify_root/              # 站点根目录，也是部署上传的目录
│   ├── index.html             # 全站唯一 HTML
│   ├── .nojekyll              # 禁止 Jekyll 构建，避免 _sidebar.md 被忽略
│   ├── README.md              # 首页（脚本生成）
│   ├── _sidebar.md            # 侧边栏（脚本生成）
│   ├── _404.md                # 站内 404
│   └── 01_产品业务文档/        # 数字前缀仅用于排序，展示时自动去掉
│       ├── README.md          # 分类索引（脚本生成）
│       └── 01_快速开始/
│           ├── README.md      # 目录内索引（脚本生成）
│           ├── 快速开始.md
│           └── img/           # 图片目录，不参与导航
├── .github/workflows/         # GitHub Actions 自动部署
├── tools/fetch_vendor.py      # 可选：把 CDN 资源下载到本地
└── update_docsify_readmes.py  # 导航自动生成脚本
```

## 三、部署到 GitHub Pages

1. 在 GitHub 新建仓库（免费账号需设为 **Public**，私有仓库要 Pro 才能开 Pages）
2. 把本目录内容推到默认分支（当前仓库为 `master`，工作流同时监听 `main` 与 `master`）
3. 仓库 → **Settings → Pages → Source**，选择 **GitHub Actions**
4. 推送代码，Actions 会自动执行：生成导航 → 打包 `docsify_root` → 部署
5. 部署完成后，Settings → Pages 顶部会给出访问地址：

```text
https://<用户名>.github.io/<仓库名>/
```

之后每次推送到 `main` 都会自动重新部署，无需任何人工操作。

### 需要注意

- 站点部署在子路径 `/<仓库名>/` 下，Docsify 会自动识别 basePath，链接不用改
- `docsify_root/.nojekyll` 必须保留，否则 Jekyll 会跳过 `_sidebar.md` 等下划线开头文件
- GitHub Pages 站点上限 1GB，图片请先压缩，或改用图床

## 四、日常维护

在 `docsify_root/` 下维护 `.md` 文档（图片放同级 `img/`），然后提交推送即可，
导航由 CI 自动重建。

如果想在本地先看效果，再手动跑一次：

```bash
python update_docsify_readmes.py
```

## 五、可选：静态资源本地化

`index.html` 默认使用 npmmirror CDN。若希望完全摆脱外部 CDN：

```bash
python tools/fetch_vendor.py
```

资源会下载到 `docsify_root/vendor/` 并自动改写 `index.html`，随后把
`docsify_root/vendor/` 一起提交即可。需要还原时执行：

```bash
python tools/fetch_vendor.py --restore
```

## 六、本地预览

```bash
cd docsify_root
python -m http.server 3000
```

访问 <http://localhost:3000>。不要用 `file://` 直接打开 `index.html`，
浏览器跨域限制会导致文档读不出来。

## 七、注意事项

- `README.md` 与 `_sidebar.md` 是生成物，不要手工长期维护
- 目录名建议保留 `01_` 数字前缀，展示名仍为中文
- 脚本生成链接时已对路径做 URL 编码，中文目录名一般不会出现 404
- GitHub Pages 在国内访问速度一般，若团队访问体验差，可绑定自定义域名并接入国内 CDN
