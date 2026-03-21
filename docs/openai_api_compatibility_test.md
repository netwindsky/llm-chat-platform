# OpenAI API 兼容性测试报告

## 测试概览

- **测试时间**: 2026-03-18 22:05:15
- **基础 URL**: http://localhost:38520
- **总计**: 30 个测试
- **通过**: 24 ✅
- **失败**: 6 ❌
- **通过率**: 80.0%

## 详细测试结果


### Models

| 状态 | 接口 | 方法 | 详情 |
|------|------|------|------|
| ✅ | `/v1/models` | GET | 返回 72 个模型 |
| ✅ | `/v1/models/{{model_id}}` | GET | 模型：qwen3.5-0.8b |

### Chat Completions

| 状态 | 接口 | 方法 | 详情 |
|------|------|------|------|
| ✅ | `/v1/chat/completions` | POST | 基本聊天成功 |
| ✅ | `/v1/chat/completions (stream)` | POST | 收到 3 个 chunk |
| ❌ | `/v1/chat/completions (multi-turn)` | POST | 状态码：500 |
| ❌ | `/v1/chat/completions (vision)` | POST | 状态码：500 |

### Completions

| 状态 | 接口 | 方法 | 详情 |
|------|------|------|------|
| ❌ | `/v1/completions` | POST | 状态码：500 |

### Embeddings

| 状态 | 接口 | 方法 | 详情 |
|------|------|------|------|
| ✅ | `/v1/embeddings` | POST | 维度：384 |

### Audio

| 状态 | 接口 | 方法 | 详情 |
|------|------|------|------|
| ⚠️ | `/v1/audio/transcriptions` | POST | 需要音频文件，跳过 |
| ⚠️ | `/v1/audio/translations` | POST | 需要音频文件，跳过 |

### Images

| 状态 | 接口 | 方法 | 详情 |
|------|------|------|------|
| ❌ | `/v1/images/generations` | POST | 状态码：501 |

### Files

| 状态 | 接口 | 方法 | 详情 |
|------|------|------|------|
| ✅ | `/v1/files` | GET | 返回 2 个文件 |
| ✅ | `/v1/files (upload)` | POST | 文件上传成功 |
| ✅ | `/v1/files/{{file_id}}` | GET | 获取文件信息成功 |
| ✅ | `/v1/files/{{file_id}}` | DELETE | 删除文件成功 |

### Batches

| 状态 | 接口 | 方法 | 详情 |
|------|------|------|------|
| ✅ | `/v1/batches` | POST | 创建批处理成功：batch-4e2d16ded8e5465488fd42396e94615a |
| ✅ | `/v1/batches/{{batch_id}}` | GET | 获取批处理成功 |
| ✅ | `/v1/batches/{{batch_id}}/cancel` | POST | 取消批处理成功 |
| ✅ | `/v1/batches (list)` | GET | 列出批处理成功 |

### Messages

| 状态 | 接口 | 方法 | 详情 |
|------|------|------|------|
| ✅ | `/v1/assistants` | POST | 创建助手成功：asst-5f0e2b812c2f4eabaa0e0cb8062d8e27 |
| ✅ | `/v1/assistants (list)` | GET | 列出助手成功 |
| ✅ | `/v1/assistants/{{assistant_id}}` | GET | 获取助手详情成功 |
| ✅ | `/v1/threads` | POST | 创建线程成功：thread-6b90bea98d914ebfbab78b325fdd01fa |
| ✅ | `/v1/threads/{{thread_id}}/messages` | POST | 创建消息成功 |
| ✅ | `/v1/threads/{{thread_id}}/messages (list)` | GET | 列出消息成功 |
| ✅ | `/v1/threads/{{thread_id}}/runs` | POST | 创建运行成功：run-f8d9be069bfe4a119f0680c98aa0d424 |
| ✅ | `/v1/threads/{{thread_id}}/runs/{{run_id}}` | GET | 获取运行详情成功 |
| ✅ | `/v1/threads/{{thread_id}}/runs/{{run_id}}/cancel` | POST | 取消运行成功 |
| ✅ | `/v1/threads/{{thread_id}}/runs (list)` | GET | 列出运行成功 |
| ✅ | `/v1/assistants/{{assistant_id}}` | DELETE | 删除助手成功 |

## 总结

⚠️ **有 6 个测试失败**。以下是需要改进的地方：

- `POST /v1/chat/completions (multi-turn)`: 状态码：500
- `POST /v1/chat/completions (vision)`: 状态码：500
- `POST /v1/completions`: 状态码：500
- `POST /v1/images/generations`: 状态码：501

## 测试说明

1. **Models API**: 测试模型列表和模型信息查询
2. **Chat Completions API**: 测试聊天完成接口，包括基本聊天、流式响应、多轮对话和视觉模型
3. **Completions API**: 测试文本完成接口
4. **Embeddings API**: 测试文本嵌入接口
5. **Audio API**: 测试语音转文字和音频翻译接口（需要音频文件）
6. **Images API**: 测试图像生成接口
7. **Files API**: 测试文件上传、下载和删除接口
8. **Batches API**: 测试批处理接口
9. **Messages API**: 测试 Assistant API 的消息接口

## 注意事项

- ⚠️ 标记为"跳过"的测试是因为需要特定文件（如音频文件、批处理输入文件等）
- 所有测试都在本地环境运行，服务器地址为 `http://localhost:38520`
- 测试结果仅供参考，实际使用情况可能因配置和环境而异

---

*本报告由自动化测试脚本生成*
