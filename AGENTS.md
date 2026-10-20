# AGENTS.md

## 项目定位

本仓库是基于 Docsify 的文档站源仓库，部署目标为 GitHub Pages，站点根目录 `docsify_root/`。
没有构建步骤：Docsify 在浏览器运行时拉取 Markdown 渲染。

AI 助手在本仓库工作时，优先目标：

1. 维护 `docsify_root/` 下的 Markdown 内容
2. 保持导航自动生成机制稳定
3. 避免破坏 GitHub Pages 的部署前提（站点根目录、入口 `index.html`、hash 路由、`.nojekyll`）

## 关键规则

### 1. 内容放置

- 所有站点内容放在 `docsify_root/` 下
- 图片放在对应文档同级的 `img/` 目录
- 目录名使用 `01_` 这类数字前缀控制排序，脚本展示时会自动去掉前缀

### 2. 导航由脚本生成

不要手工长期维护以下文件：

- `docsify_root/README.md`
- `docsify_root/_sidebar.md`
- 各文档目录下的 `README.md`

这些文件由 `update_docsify_readmes.py` 生成。改动目录结构或增删文档后，必须重新运行：

```bash
python update_docsify_readmes.py
```

### 3. 链接规则

- 生成链接统一使用站点根路径 `/目录/...`，并做 URL 编码
- `index.html` 中 `relativePath: true` 与 `alias` 配置用于保证任意层级页面都能定位导航文件
- 不要随意改动这套配置，除非已验证 Docsify 跳转逻辑

## 修改优先级

允许优先修改：

1. `docsify_root/` 下的 Markdown 文档
2. `update_docsify_readmes.py`
3. `docsify_root/index.html`
4. `README.md`

修改前应先理解现状：

- 页面 404 / 跳转异常：先查 `relativePath`、`alias`、`_sidebar.md` 链接形式
- 导航缺失：先跑脚本，再查脚本的 `IGNORE_DIRS` 与 `is_final_directory` 判定
- 样式丢失或白屏：多为 CDN 不可达，执行 `python tools/fetch_vendor.py`

不建议手工改生成物，应改脚本。

## 标准工作流

1. 判断是改文档内容还是改结构
2. 只改内容时直接编辑对应 `.md`
3. 增删或重命名文档/目录后运行 `python update_docsify_readmes.py`
4. 检查 `docsify_root/README.md`、`docsify_root/_sidebar.md` 生成结果
5. 提交并推送到 `main`，GitHub Actions 会自动重建导航并部署

## 成功标准

- 作者只需要维护 Markdown 本身
- 导航自动生成，无手工维护成本
- 页面跳转不出现 404
- 部署到 GitHub Pages 后站点结构稳定
