# wechat-link

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-2ea44f)
![Scope](https://img.shields.io/badge/Scope-Core%20Protocol-6f42c1)
![Protocol](https://img.shields.io/badge/Protocol-iLink--Compatible-0f766e)

**一个面向 iLink-compatible Weixin Bot 集成的非官方 Python SDK，专注协议层、媒体链路与薄中转服务。**

[简体中文](./README.md) | [English](./README.en.md) | [日本語](./README.ja.md)

</div>

---

## 项目定位

`wechat-link` 不是一个“大而全”的机器人平台，也不是一个包装成“官方开放平台替代品”的外壳。

它的定位非常明确：

> **把 iLink / 微信 Bot 的关键 HTTP 协议整理成一个干净、可复用、可嵌入、可持续维护的 Python SDK，并提供一个可选的薄 Relay。**

这意味着它优先解决的是：
- 协议边界是否清晰
- SDK 是否足够稳定、可读、可组合
- 媒体上传链路是否完整
- 是否能方便接入自己的应用、LLM、工作流或服务端

而不是一开始就去做：后台系统、群控平台、多账号运营面板、复杂业务编排。

## 为什么是 `wechat-link`

大多数相关项目会很快长成一个“机器人应用”，协议层、业务逻辑、运行时状态、平台功能缠在一起，短期看上去很快，长期却很难维护。

`wechat-link` 的处理方式相对克制：

- 先把登录、轮询、发消息、typing、媒体链路做稳
- Relay 只是 SDK 的一层薄封装，不再额外造一套系统
- 协议细节尽量落到明确的数据结构和接口里
- 默认考虑接入 FastAPI、Django、LangChain、任务队列和内部服务
- 少承诺还没做好的能力，优先把核心链路维护清楚

## 架构概览

```mermaid
flowchart LR
    A["Your App / LLM / Workflow"] --> B["wechat-link SDK"]
    A --> C["wechat-link Relay (Optional)"]
    C --> B
    B --> D["iLink Bot API"]
    B --> E["CDN Upload / Download"]
    E --> F["AES-128-ECB Media Path"]
    D --> G["Weixin / iLink Runtime"]
```

### 设计分层

- **`wechat_link.client`**：对 iLink API 的核心调用封装
- **`wechat_link.media`**：媒体上传编排、缩略图元数据处理、CDN 上传流程
- **`wechat_link.cdn` / `wechat_link.crypto`**：CDN 传输与 AES 细节
- **`wechat_link.relay`**：薄 FastAPI 中转层，方便把 SDK 暴露为 HTTP 服务
- **`wechat_link.store`**：`get_updates_buf` 的持久化辅助

## 生命周期与数据流

```mermaid
sequenceDiagram
    autonumber
    participant App as Your App
    participant SDK as wechat-link SDK
    participant API as iLink API
    participant CDN as Weixin CDN

    App->>SDK: get_updates(cursor)
    SDK->>API: POST /ilink/bot/getupdates
    API-->>SDK: msgs + get_updates_buf
    SDK-->>App: UpdatesResponse

    App->>SDK: send_text(..., context_token)
    SDK->>API: POST /ilink/bot/sendmessage
    API-->>SDK: ret=0

    App->>SDK: upload_image(...)
    SDK->>API: POST /ilink/bot/getuploadurl
    API-->>SDK: upload_param
    SDK->>CDN: upload ciphertext
    CDN-->>SDK: encrypted download param
    App->>SDK: send_image(..., uploaded)
    SDK->>API: POST /ilink/bot/sendmessage
```

## 当前能力矩阵

| 能力 | 状态 | 说明 |
| --- | --- | --- |
| 获取登录二维码 | 已实现 | `get_bot_qrcode()` |
| 查询二维码状态 | 已实现 | `get_qrcode_status()` |
| 长轮询收消息 | 已实现 | `get_updates()` |
| 游标持久化 | 已实现 | `FileCursorStore` |
| 发送文本 | 已实现 | `send_text()` |
| 获取 typing 配置 | 已实现 | `get_config()` |
| 发送 typing 状态 | 已实现 | `send_typing()` |
| 请求上传地址 | 已实现 | `get_upload_url()` |
| 图片上传 / 发送 | 已实现 | `upload_image()` / `send_image()` |
| 文件上传 / 发送 | 已实现 | `upload_file()` / `send_file()` |
| 视频上传 / 发送 | 已实现 | 支持显式 `thumb_path` |
| 语音上传 / 发送 | 已实现 | `upload_voice()` / `send_voice()` |
| 薄 Relay 服务 | 已实现 | FastAPI 路由封装 |
| 自动视频抽帧 | 未实现 | 当前不做隐式媒体处理 |
| 自动语音转码 | 未实现 | 当前不引入 ffmpeg / silk 工具链 |
| 完整 Bot Runtime | 非当前目标 | 保持 SDK-first 边界 |

## 安装

### 从源码安装

```bash
git clone https://github.com/syusama/wechat-link.git
cd wechat-link
pip install -e .
```

### 安装 Relay 依赖

```bash
pip install -e .[relay]
```

### 开发环境

```bash
pip install -e .[dev]
pytest -q
```

## 快速开始

### 1) 使用已有 `bot_token` 收消息并回显

```python
import time

from wechat_link import FileCursorStore, WeChatLinkClient

client = WeChatLinkClient(bot_token="your-bot-token")
store = FileCursorStore(".state/get_updates_buf.json")
cursor = store.load() or ""

try:
    while True:
        updates = client.get_updates(cursor=cursor)

        if updates.next_cursor:
            cursor = updates.next_cursor
            store.save(cursor)

        for message in updates.messages:
            text = message.text().strip()
            if not text or not message.from_user_id or not message.context_token:
                continue

            client.send_text(
                to_user_id=message.from_user_id,
                text=f"echo: {text}",
                context_token=message.context_token,
            )

        time.sleep(1)
finally:
    client.close()
```

对应示例：`examples/echo_bot.py`

### 2) 底层扫码登录接口

当前版本提供的是**扫码登录原语**，而不是完整的登录编排器。

```python
import time

from wechat_link import WeChatLinkClient

client = WeChatLinkClient()
qr = client.get_bot_qrcode()
print(qr.qrcode)

while True:
    status = client.get_qrcode_status(qr.qrcode)
    print(status.status)

    if status.status == "confirmed":
        print("bot_token:", status.bot_token)
        print("baseurl:", status.baseurl)
        print("ilink_bot_id:", status.ilink_bot_id)
        print("ilink_user_id:", status.ilink_user_id)
        break

    time.sleep(1)
```

这里故意保持低封装。现阶段更重要的是把协议边界讲清楚，而不是过早叠加高层运行时。

### 3) 发送图片 / 视频

```python
from wechat_link.client import WeChatLinkClient

client = WeChatLinkClient(bot_token="your-bot-token")

uploaded = client.upload_image(
    file_path="demo.jpg",
    to_user_id="user@im.wechat",
)

client.send_image(
    to_user_id="user@im.wechat",
    uploaded=uploaded,
    context_token="ctx-from-inbound-message",
)

uploaded_video = client.upload_video(
    file_path="demo.mp4",
    to_user_id="user@im.wechat",
    thumb_path="thumb.jpg",
)

client.send_video(
    to_user_id="user@im.wechat",
    uploaded=uploaded_video,
    context_token="ctx-from-inbound-message",
)

client.close()
```

对应示例：`examples/send_media.py`

## Relay：把 SDK 暴露为 HTTP 服务

如果你希望把 Python SDK 接到其他语言、其他服务、或者内部平台上，可以使用内置的薄 Relay。

### 启动 Relay

```bash
uvicorn examples.relay_server:app --reload
```

对应示例：`examples/relay_server.py`

### 已提供的路由

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| `GET` | `/health` | 健康检查 |
| `GET` | `/login/qrcode` | 获取登录二维码 |
| `GET` | `/login/status` | 查询二维码状态 |
| `POST` | `/config` | 获取 typing 配置 |
| `POST` | `/typing` | 发送 typing 状态 |
| `POST` | `/updates/poll` | 长轮询消息 |
| `POST` | `/messages/text` | 发文本消息 |
| `POST` | `/messages/image/upload` | 上传并发送图片 |
| `POST` | `/messages/file/upload` | 上传并发送文件 |
| `POST` | `/messages/video/upload` | 上传并发送视频 |
| `POST` | `/messages/voice/upload` | 上传并发送语音 |

### Relay 调用示例

```bash
curl -X POST http://127.0.0.1:8000/messages/image/upload \
  -F "to_user_id=user@im.wechat" \
  -F "context_token=ctx-1" \
  -F "file=@demo.jpg"
```

```bash
curl -X POST http://127.0.0.1:8000/messages/video/upload \
  -F "to_user_id=user@im.wechat" \
  -F "context_token=ctx-1" \
  -F "file=@demo.mp4" \
  -F "thumb_file=@thumb.jpg"
```

## 协议要点

### 1. `context_token` 是回复链路的关键

回复同一会话时，必须把上游消息里的 `context_token` 带回去。`wechat-link` 不会替你“猜测上下文”，这是协议层最关键的边界之一。

### 2. `get_updates_buf` 必须持久化

`get_updates_buf` 是长轮询游标。如果不持久化，最常见的问题就是重复消费消息。当前仓库通过 `FileCursorStore` 提供了一个极简但够用的本地持久化方案。

### 3. 媒体发送不是单个接口，而是一条链路

媒体发送通常分成三步：
1. `get_upload_url()` 申请上传参数
2. 上传加密后的文件到 CDN
3. 用上传结果组装 `sendmessage` 的媒体消息体

### 4. 请求头由 SDK 自动构造

所有核心 CGI POST 请求都会自动构造以下头部：

```text
Content-Type: application/json
AuthorizationType: ilink_bot_token
Authorization: Bearer <bot_token>
X-WECHAT-UIN: base64(decimal(random_uint32))
```

### 5. 媒体链路包含 AES-128-ECB 处理

当前实现已经覆盖：
- CDN 上传参数拼装
- AES-128-ECB 加密尺寸计算
- CDN 下载参数回传
- 图片 / 文件 / 视频 / 语音的协议消息封包

## 设计原则

### 先把基础链路做稳
先把协议层、消息链路和媒体链路维护清楚，再考虑更高层的运行时封装。

### Relay 保持可选
Relay 是桥，不是平台；需要时用，不需要时可以完全绕过。

### 少做隐式处理
尽量减少“自动猜测”“隐式处理”和“黑盒行为”，方便调试、审计和长期维护。

### 能力面保持克制
少而稳，优先做正确、做清晰，而不是一开始承诺很大的能力面。

## 项目结构

```text
src/wechat_link/
├── __init__.py
├── cdn.py
├── client.py
├── crypto.py
├── headers.py
├── media.py
├── message_builders.py
├── models.py
├── relay.py
└── store.py

examples/
├── echo_bot.py
├── relay_server.py
└── send_media.py

tests/
├── test_cdn.py
├── test_client.py
├── test_crypto.py
├── test_cursor_store.py
├── test_headers.py
├── test_media_client.py
├── test_media_helpers.py
├── test_message_builders.py
├── test_relay.py
├── test_relay_helpers.py
└── test_relay_media.py
```

## 接下来会继续做什么

接下来的工作仍然会围绕“核心链路”推进，而不是扩张成平台：

- 继续强化协议文档与错误语义
- 提升媒体参数校验与开发者体验
- 保持 Relay 的薄封装定位
- 只在确有必要时增加高层 helper，而不是提前堆运行时

## 明确边界

`wechat-link` 是一个 **非官方项目**。

它不代表腾讯官方，不应被描述为腾讯官方开放平台，也不应被包装成某种“官方替代品”。更准确的描述是：

> **An unofficial Python SDK for iLink-compatible Weixin bot integration.**

同样地，当前项目也**不以**以下能力为目标：
- 多账号运营后台
- 大规模群控平台
- 营销自动化面板
- 与协议层强耦合的大型 Bot Framework

## 致谢与参考

本项目的协议研究与实现边界，参考了公开可见的上游项目与资料，包括但不限于：
- [`hao-ji-xing/cc-weixin`](https://github.com/hao-ji-xing/cc-weixin)
- `openclaw-weixin` 相关公开源码结构
- 社区已公开的 iLink Bot 协议调用实践

`wechat-link` 的目标不是复刻别人的产品形态，而是把这条协议链路整理成一个更克制、更干净、更适合 Python 生态复用的基础件。

## 参与贡献

如果你打算提 Issue 或 PR，建议先看：

- [`CONTRIBUTING.md`](./CONTRIBUTING.md)

当前更适合投入精力的方向有：

- 协议行为核对与纠偏
- 媒体链路稳定性与边界处理
- 测试覆盖与文档准确性
- 在不扩大项目边界的前提下做结构瘦身

## License

MIT
