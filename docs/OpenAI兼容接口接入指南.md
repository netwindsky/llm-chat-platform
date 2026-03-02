# OpenAI 兼容接口接入指南

本文档介绍如何通过各种软件和工具接入本 LLM 推理平台的 OpenAI 兼容接口。

## 目录

- [接口概览](#接口概览)
- [基础配置](#基础配置)
- [Python SDK 接入](#python-sdk-接入)
- [Node.js 接入](#nodejs-接入)
- [Cursor 编辑器接入](#cursor-编辑器接入)
- [VS Code 插件接入](#vs-code-插件接入)
- [Cherry Studio 接入](#cherry-studio-接入)
- [Chatbox 接入](#chatbox-接入)
- [LobeChat 接入](#lobachat-接入)
- [NextChat 接入](#nextchat-接入)
- [其他支持 OpenAI 协议的软件](#其他支持-openai-协议的软件)
- [常见问题](#常见问题)

---

## 接口概览

本平台提供完全兼容 OpenAI API 的接口，支持以下端点：

| 端点 | 方法 | 说明 |
|------|------|------|
| `/v1/models` | GET | 获取可用模型列表 |
| `/v1/models/{model_id}` | GET | 获取指定模型信息 |
| `/v1/chat/completions` | POST | 聊天完成接口（支持流式/非流式） |

### 基础 URL

```
http://localhost:8080/v1/chat/completions
```

### 认证方式

本地部署无需 API Key，但部分客户端需要填写，可使用任意值（如 `sk-local`）。

---

## 基础配置

### 1. 启动服务

确保后端服务已启动：

```bash
cd server
python main.py
```

服务将在 `http://localhost:8080` 启动。

### 2. 加载模型

**自动加载（推荐）**

OpenAI 兼容接口支持自动加载模型。当请求的模型未加载时，系统会自动加载该模型。无需手动操作！

**手动加载**

也可以通过管理接口手动加载模型：

```bash
curl -X POST "http://localhost:8080/api/v1/models/qwen3.5-35b-a3b-thinking/load" \
  -H "Content-Type: application/json" \
  -d '{"gpu_layers": 99}'
```

或通过前端界面加载模型。

---

## Python SDK 接入

### 安装 OpenAI SDK

```bash
pip install openai
```

### 基础用法

```python
from openai import OpenAI

# 初始化客户端
client = OpenAI(
    base_url="http://localhost:8080/v1",
    api_key="sk-local"  # 本地部署可使用任意值
)

# 列出可用模型
models = client.models.list()
print("可用模型:")
for model in models.data:
    print(f"  - {model.id}")

# 非流式聊天
response = client.chat.completions.create(
    model="qwen3.5-35b-a3b-thinking",
    messages=[
        {"role": "system", "content": "你是一个有帮助的助手。"},
        {"role": "user", "content": "你好，请介绍一下自己。"}
    ],
    temperature=0.7,
    max_tokens=2048
)
print(response.choices[0].message.content)

# 流式聊天
stream = client.chat.completions.create(
    model="qwen3.5-35b-a3b-thinking",
    messages=[
        {"role": "user", "content": "写一首关于春天的诗"}
    ],
    stream=True
)
for chunk in stream:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="", flush=True)
print()
```

### 多模态（图片分析）

```python
import base64

# 方式1: 使用图片URL
response = client.chat.completions.create(
    model="qwen3.5-35b-a3b-vision",
    messages=[
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "这张图片里有什么？"},
                {
                    "type": "image_url",
                    "image_url": {"url": "https://example.com/image.jpg"}
                }
            ]
        }
    ]
)

# 方式2: 使用 Base64 编码的图片
with open("image.png", "rb") as f:
    image_data = base64.b64encode(f.read()).decode("utf-8")

response = client.chat.completions.create(
    model="qwen3.5-35b-a3b-vision",
    messages=[
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "描述这张图片"},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{image_data}"
                    }
                }
            ]
        }
    ]
)
print(response.choices[0].message.content)
```

### 异步调用

```python
import asyncio
from openai import AsyncOpenAI

async def main():
    client = AsyncOpenAI(
        base_url="http://localhost:8080/v1",
        api_key="sk-local"
    )
    
    response = await client.chat.completions.create(
        model="qwen3.5-35b-a3b-thinking",
        messages=[{"role": "user", "content": "你好"}]
    )
    print(response.choices[0].message.content)

asyncio.run(main())
```

---

## Node.js 接入

### 安装依赖

```bash
npm install openai
```

### 基础用法

```javascript
import OpenAI from 'openai';

const client = new OpenAI({
  baseURL: 'http://localhost:8080/v1',
  apiKey: 'sk-local'
});

// 非流式聊天
async function chat() {
  const response = await client.chat.completions.create({
    model: 'qwen3.5-35b-a3b-thinking',
    messages: [
      { role: 'user', content: '你好，请介绍一下自己。' }
    ],
    temperature: 0.7,
    max_tokens: 2048
  });
  
  console.log(response.choices[0].message.content);
}

// 流式聊天
async function streamChat() {
  const stream = await client.chat.completions.create({
    model: 'qwen3.5-35b-a3b-thinking',
    messages: [
      { role: 'user', content: '写一首诗' }
    ],
    stream: true
  });
  
  for await (const chunk of stream) {
    process.stdout.write(chunk.choices[0]?.delta?.content || '');
  }
}

chat();
streamChat();
```

### 多模态支持

```javascript
async function analyzeImage() {
  const response = await client.chat.completions.create({
    model: 'qwen3.5-35b-a3b-vision',
    messages: [
      {
        role: 'user',
        content: [
          { type: 'text', text: '描述这张图片' },
          {
            type: 'image_url',
            image_url: { url: 'https://example.com/image.jpg' }
          }
        ]
      }
    ]
  });
  
  console.log(response.choices[0].message.content);
}
```

---

## Cursor 编辑器接入

Cursor 是一款 AI 驱动的代码编辑器，支持自定义 OpenAI 兼容接口。

### 配置步骤

1. 打开 Cursor 设置（`Ctrl + ,` 或 `Cmd + ,`）
2. 搜索 "OpenAI" 或导航到 `Models > OpenAI`
3. 配置以下选项：

| 配置项 | 值 |
|--------|-----|
| OpenAI API Key | `sk-local` |
| OpenAI Base URL | `http://localhost:8080/v1` |
| Override OpenAI Base URL | ✅ 启用 |

4. 在模型列表中添加模型 ID，如：
   - `qwen3.5-35b-a3b-thinking`
   - `qwen3.5-35b-a3b-no-thinking`

### 通过配置文件

编辑 `~/.cursor/config.json`：

```json
{
  "models": {
    "openai": {
      "apiKey": "sk-local",
      "baseUrl": "http://localhost:8080/v1"
    }
  }
}
```

### 使用建议

- **编码任务**: 使用 `qwen3.5-35b-a3b-thinking`（思考模式）
- **通用对话**: 使用 `qwen3.5-35b-a3b-no-thinking`（非思考模式）

---

## VS Code 插件接入

### Continue 插件

[Continue](https://continue.dev/) 是一款流行的 VS Code AI 编程助手插件。

#### 配置步骤

1. 安装 Continue 插件
2. 打开 Continue 设置（点击左侧 Continue 图标 → 齿轮图标）
3. 编辑 `config.json`：

```json
{
  "models": [
    {
      "title": "Qwen3.5 Thinking",
      "provider": "openai",
      "model": "qwen3.5-35b-a3b-thinking",
      "apiBase": "http://localhost:8080/v1",
      "apiKey": "sk-local"
    },
    {
      "title": "Qwen3.5 Vision",
      "provider": "openai",
      "model": "qwen3.5-35b-a3b-vision",
      "apiBase": "http://localhost:8080/v1",
      "apiKey": "sk-local"
    }
  ]
}
```

### Codeium 插件

Codeium 也支持自定义后端：

1. 打开 VS Code 设置
2. 搜索 "Codeium"
3. 配置 Enterprise 模式的自定义端点

---

## Cherry Studio 接入

[Cherry Studio](https://www.cherry-ai.com/) 是一款支持多模型的桌面客户端。

### 配置步骤

1. 打开 Cherry Studio
2. 进入 设置 → 模型提供商
3. 添加自定义提供商：
   - **名称**: LLM Platform
   - **类型**: OpenAI 兼容
   - **Base URL**: `http://localhost:8080/v1`
   - **API Key**: `sk-local`

4. 添加模型：
   - `qwen3.5-35b-a3b-thinking`
   - `qwen3.5-35b-a3b-no-thinking`
   - `qwen3.5-35b-a3b-vision`

---

## Chatbox 接入

[Chatbox](https://chatboxai.app/) 是一款简洁的 AI 聊天客户端。

### 配置步骤

1. 打开 Chatbox 设置
2. 选择 "模型提供方" → "OpenAI API"
3. 配置：
   - **API 域名**: `http://localhost:8080`
   - **API Key**: `sk-local`
   - **模型**: 手动输入模型 ID

4. 保存并开始使用

---

## LobeChat 接入

[LobeChat](https://lobehub.com/) 是一款开源的 AI 聊天应用。

### 配置步骤

1. 进入 设置 → 语言模型
2. 添加 OpenAI 兼容提供商：
   - **名称**: LLM Platform
   - **API URL**: `http://localhost:8080/v1`
   - **API Key**: `sk-local`

3. 在模型配置中添加：
   ```yaml
   - id: qwen3.5-35b-a3b-thinking
     name: Qwen3.5 Thinking
     type: text
   - id: qwen3.5-35b-a3b-vision
     name: Qwen3.5 Vision
     type: vision
   ```

---

## NextChat 接入

[NextChat](https://github.com/ChatGPTNextWeb/ChatGPT-Next-Web) 是一款流行的开源 ChatGPT 客户端。

### 配置步骤

1. 部署或访问 NextChat
2. 点击左下角设置图标
3. 选择 "自定义接口"
4. 配置：
   - **接口地址**: `http://localhost:8080/v1`
   - **API Key**: `sk-local`
   - **模型**: 选择或输入模型 ID

### Docker 部署配置

```bash
docker run -d \
  -p 3000:3000 \
  -e OPENAI_API_KEY=sk-local \
  -e BASE_URL=http://localhost:8080/v1 \
  -e CUSTOM_MODELS=qwen3.5-35b-a3b-thinking,qwen3.5-35b-a3b-vision \
  yidadaa/chatgpt-next-web
```

---

## 其他支持 OpenAI 协议的软件

以下软件也支持 OpenAI 兼容接口，配置方式类似：

| 软件 | 类型 | 配置要点 |
|------|------|----------|
| **Raycast AI** | Mac 效率工具 | 使用扩展配置自定义端点 |
| **TypingMind** | Web 客户端 | 设置 → OpenAI → 自定义 Base URL |
| **LibreChat** | 开源聊天平台 | 配置 `librechat.yaml` |
| **Dify** | AI 应用开发平台 | 添加自定义模型供应商 |
| **FastGPT** | 知识库问答平台 | 配置 OneAPI 或直接接入 |
| **Poe** | 聊天平台 | 通过 Poe Protocol 适配 |
| **SiliconCloud** | 云平台 | 配置自定义推理端点 |

### 通用配置模板

大多数软件需要以下配置：

```
Base URL: http://localhost:8080/v1
API Key: sk-local (或任意值)
Model ID: qwen3.5-35b-a3b-thinking
```

---

## 常见问题

### 1. 模型自动加载

OpenAI 兼容接口支持自动加载模型。首次请求时，系统会自动加载指定模型（可能需要等待几十秒）。

如果加载失败，请检查：
- 模型文件是否存在
- 显存是否充足
- 后端服务日志

### 2. 连接超时

**可能原因**:
- 服务未启动
- 端口被占用
- 防火墙阻止

**解决方案**:
```bash
# 检查服务状态
curl http://localhost:8080/health

# 检查端口占用
netstat -an | findstr 8080  # Windows
lsof -i :8080               # Linux/Mac
```

### 3. 流式响应中断

**可能原因**: 网络代理或中间件缓冲

**解决方案**: 
- 禁用代理
- 配置 `X-Accel-Buffering: no` 头

### 4. 多模态图片无法识别

**可能原因**:
- 使用了非视觉模型
- mmproj 文件缺失

**解决方案**:
- 确保使用 `qwen3.5-35b-a3b-vision` 模型
- 检查 mmproj 文件是否存在

### 5. 思考模式不生效

**可能原因**: 使用了非思考模式模型

**解决方案**: 
- 编码/推理任务使用 `qwen3.5-35b-a3b-thinking`
- 通用对话使用 `qwen3.5-35b-a3b-no-thinking`

---

## 模型选择建议

| 场景 | 推荐模型 | 特点 |
|------|----------|------|
| 代码编写 | `qwen3.5-35b-a3b-thinking` | 思考模式，深度推理 |
| 复杂推理 | `qwen3.5-35b-a3b-thinking` | 思考模式，详细分析 |
| 日常对话 | `qwen3.5-35b-a3b-no-thinking` | 非思考模式，快速响应 |
| 图片分析 | `qwen3.5-35b-a3b-vision` | 多模态，图片理解 |
| 文档处理 | `qwen3.5-35b-a3b-no-thinking` | 非思考模式，高效处理 |

---

## 技术支持

如有问题，请检查：

1. 后端服务日志
2. 模型加载状态
3. API 响应内容

更多帮助请参考项目文档或提交 Issue。
