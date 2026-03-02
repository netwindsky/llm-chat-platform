# LLM 聊天平台

基于 llama.cpp 的本地大模型聊天应用，支持流式响应、思考模式、Markdown 渲染等功能。

## 功能特性

- 🚀 **流式响应** - 支持实时流式输出，提升交互体验
- 🧠 **思考模式** - 支持推理模型显示思考过程
- 📝 **Markdown 渲染** - 完整支持 Markdown 语法高亮
- 🎨 **现代 UI** - 精美的深色主题界面
- 🔄 **模型管理** - 动态加载/卸载本地模型

## 项目结构

```
llm-chat-platform/
├── configs/          # 配置文件
│   ├── models.yaml   # 模型配置
│   ├── runtimes.yaml # 运行时配置
│   └── server.yaml   # 服务配置
├── server/           # FastAPI 后端
│   ├── api/          # API 路由
│   ├── backends/     # 后端实现
│   ├── core/         # 核心模块
│   └── services/     # 服务层
├── web/              # Vue.js 前端
│   └── src/
│       ├── views/    # 页面组件
│       ├── stores/  # 状态管理
│       └── components/ # 公共组件
├── doc/              # 项目文档
└── docs/             # 技术文档
```

## 快速开始

### 1. 环境要求

- Python 3.10+
- Node.js 18+
- llama.cpp 可执行文件

### 2. 安装后端依赖

```bash
cd server
pip install -r requirements.txt
```

### 3. 安装前端依赖

```bash
cd web
npm install
```

### 4. 配置模型

编辑 `configs/models.yaml` 添加你的模型路径：

```yaml
models:
  - id: qwen3-30b-a3b-thinking
    name: Qwen3-30B-A3B-Thinking
    path: models/Qwen3-30B-A3B-Thinking-2507-UD-Q4_K_XL.gguf
    type: reasoning-model
    backend: llama
```

### 5. 配置运行时

编辑 `configs/runtimes.yaml` 设置 llama.cpp 路径：

```yaml
runtimes:
  llama:
    bin_path: runtimes/llama/bin/llama-server.exe
    port: 8081
```

### 6. 启动服务

**启动后端：**
```bash
cd server
python main.py
```

**启动前端：**
```bash
cd web
npm run dev
```

访问 http://localhost:5173 即可使用。

## 配置说明

### 模型类型

- `chat-model` - 普通对话模型
- `reasoning-model` - 推理模型（支持思考过程）
- `vision-language-model` - 视觉语言模型

### 模型参数

在 `configs/models.yaml` 中可以为每个模型设置：

```yaml
models:
  - id: model-id
    name: 模型名称
    path: 模型文件路径
    type: 模型类型
    backend: llama
    max_context: 8192      # 最大上下文长度
    default_temp: 0.7      # 默认温度
    default_top_p: 0.9     # 默认 top_p
```

## 技术栈

- **后端**: FastAPI, llama.cpp, Python
- **前端**: Vue 3, Pinia, Element Plus, Vite
- **部署**: 本地运行，无需云服务

## 注意事项

1. 模型文件（.gguf）不包含在仓库中，需要自行下载
2. 运行时环境（runtimes/）不包含在仓库中，需要自行配置
3. 确保有足够的显存/内存运行模型

## 许可证

MIT License
