# Release Checklist

这份文档是 `wechat-link` 的首发与后续版本发布清单，按一次真实发布的顺序整理。

当前建议的首发版本：`v0.1.0`

---

## 1. 发布前检查

在创建 tag 或 Release 之前，先确认下面几项：

- [ ] `README.md`、`README.en.md`、`README.ja.md` 已更新
- [ ] `README.pypi.md` 可用于 PyPI 展示
- [ ] `LICENSE` 已存在
- [ ] `pyproject.toml` 中版本号正确
- [ ] `pytest -q` 通过
- [ ] `python -m build --outdir dist` 通过
- [ ] `python -m twine check dist\\wechat_link-0.1.0.tar.gz dist\\wechat_link-0.1.0-py3-none-any.whl` 通过

当前仓库已经完成并验证过的项：

- `pytest -q`
- `python -m build --outdir dist`
- `python -m twine check ...`

---

## 2. GitHub 仓库准备

发布前建议先把默认仓库信息补完整：

### About

Description:

`Unofficial Python SDK for iLink-compatible Weixin Bot integration, focused on protocol handling, media delivery, and a lightweight relay.`

Suggested topics:

```text
python
sdk
wechat
weixin
bot
ilink
api
fastapi
relay
llm
automation
protocol
cdn
media
unofficial
```

这些文案也已经整理在：

- `docs/repository-metadata.md`

---

## 3. PyPI 准备

### 注册与安全设置

- [ ] 注册 PyPI 账号
- [ ] 完成邮箱验证
- [ ] 开启 2FA

### 配置 Trusted Publishing

建议使用当前仓库里的 GitHub Actions 工作流：

- Workflow file: `.github/workflows/publish.yml`
- GitHub repository: `syusama/wechat-link`
- Environment name: `pypi`

如果是首次发布，建议先在 PyPI 后台完成 Trusted Publisher 绑定，再发 GitHub Release。

---

## 4. 版本号与 tag

当前首发建议：

- Python package version: `0.1.0`
- Git tag: `v0.1.0`

命令示例：

```bash
git add .
git commit -m "chore: prepare v0.1.0 release"
git tag v0.1.0
git push origin main --tags
```

---

## 5. GitHub Release 标题

建议标题：

`wechat-link v0.1.0`

也可以更直接一点：

`v0.1.0 — first public release`

---

## 6. GitHub Release Notes 模板

下面这版比较适合首发：

```md
## wechat-link v0.1.0

First public release of `wechat-link`.

### Highlights

- Initial Python SDK for iLink-compatible Weixin Bot integration
- Long polling with cursor persistence support
- Text messaging support
- Typing API support
- Media upload and send support for image, file, video, and voice
- Optional FastAPI relay layer
- Multilingual documentation: Chinese, English, and Japanese

### Package

- PyPI package: `wechat-link`
- Python: `>=3.11`

### Notes

- This is an unofficial project
- The current focus is the protocol layer and a thin relay
- High-level bot runtime features are intentionally out of scope for now
```

如果你想要中文版首发说明，可以用下面这版：

```md
## wechat-link v0.1.0

`wechat-link` 的首次公开发布。

### 本次发布内容

- 提供 iLink-compatible Weixin Bot 的 Python SDK
- 支持长轮询与游标持久化
- 支持文本消息发送
- 支持 typing 接口
- 支持图片、文件、视频、语音的上传与发送
- 提供可选的 FastAPI Relay
- 提供中 / 英 / 日三语文档

### 包信息

- PyPI 包名：`wechat-link`
- Python 版本：`>=3.11`

### 说明

- 这是一个非官方项目
- 当前重点是协议层与薄中转层
- 更高层的 Bot Runtime 能力暂不作为首发目标
```

---

## 7. 发布动作

如果 Trusted Publishing 已配置完成，发布顺序可以很简单：

1. Push 最新代码
2. Push `v0.1.0` tag
3. 在 GitHub 创建 Release
4. 发布 Release
5. 等待 GitHub Actions 自动上传到 PyPI

---

## 8. 发布后检查

发布完成后，建议检查：

- [ ] PyPI 页面能正常打开
- [ ] `pip install wechat-link` 可以安装
- [ ] `pip install "wechat-link[relay]"` 可以安装
- [ ] PyPI 描述显示正常
- [ ] GitHub Release 页面内容正常

建议额外做一次干净环境安装验证：

```bash
python -m venv .venv-test
.venv-test\\Scripts\\activate
pip install wechat-link
python -c "import wechat_link; print(wechat_link.__all__)"
```

---

## 9. 首发后的下一步

首发完成后，建议优先做这些事情：

- 补一个简洁的 `CHANGELOG.md`
- 增加 `.github` 的 issue / PR 模板
- 增加 TestPyPI 验证流程
- 如果后续开始频繁发版，再补自动化版本发布流程
