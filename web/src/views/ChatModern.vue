<template>
  <div
    class="chat-modern"
    :class="{ 'sidebar-collapsed': sidebarCollapsed }"
  >
    <!-- 侧边栏 -->
    <aside class="sidebar">
      <div class="sidebar-header">
        <div class="brand">
          <div class="brand-icon">
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
            >
              <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
            </svg>
          </div>
          <span class="brand-text">NeuralChat</span>
        </div>
        <button
          class="sidebar-toggle"
          @click="sidebarCollapsed = !sidebarCollapsed"
        >
          <el-icon><Fold v-if="!sidebarCollapsed" /><Expand v-else /></el-icon>
        </button>
      </div>

      <!-- 新建对话按钮 -->
      <button
        class="new-chat-btn"
        @click="startNewChat"
      >
        <el-icon><Plus /></el-icon>
        <span>新建对话</span>
      </button>

      <!-- 对话历史 -->
      <div class="conversations">
        <div class="section-title">
          最近对话
        </div>
        <div class="conversation-list">
          <div
            v-for="conv in sortedConversations"
            :key="conv.id"
            class="conversation-item"
            :class="{ active: currentConversationId === conv.id }"
            @click="loadConversation(conv.id)"
          >
            <el-icon><ChatRound /></el-icon>
            <span
              v-if="editingConversationId !== conv.id"
              class="conv-title"
            >{{ conv.title }}</span>
            <input
              v-else
              v-model="editingTitle"
              class="conv-title-input"
              @blur="saveTitle(conv.id)"
              @keyup.enter="saveTitle(conv.id)"
              @keyup.esc="cancelEdit()"
            >
            <div class="conv-actions">
              <button
                class="action-btn"
                @click.stop="startEditTitle(conv)"
              >
                <el-icon><Edit /></el-icon>
              </button>
              <button
                class="action-btn delete"
                @click.stop="deleteConversation(conv.id)"
              >
                <el-icon><Close /></el-icon>
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- 底部设置 -->
      <div class="sidebar-footer">
        <button
          class="footer-btn"
          @click="$router.push('/settings')"
        >
          <el-icon><Setting /></el-icon>
          <span>设置</span>
        </button>
      </div>
    </aside>

    <!-- 主内容区 -->
    <main class="main-content">
      <!-- 顶部栏 -->
      <header class="top-bar">
        <div class="top-bar-left">
          <h2 class="page-title">
            {{ currentConversationTitle || '新对话' }}
          </h2>
        </div>
        
        <div class="top-bar-center">
          <div
            v-click-outside="closeModelDropdown"
            class="model-selector"
          >
            <button
              class="model-btn"
              @click="modelDropdownOpen = !modelDropdownOpen"
            >
              <div
                class="model-status"
                :class="currentModel?.status"
              />
              <span>{{ currentModel?.name || '选择模型' }}</span>
              <el-icon><ArrowDown /></el-icon>
            </button>
            
            <transition name="dropdown">
              <div
                v-show="modelDropdownOpen"
                class="model-dropdown"
              >
                <div class="dropdown-header">
                  可用模型
                </div>
                <div class="model-list">
                  <div 
                    v-for="model in availableModels" 
                    :key="model.id"
                    class="model-option"
                    :class="{ active: selectedModel === model.id, loading: model.status === 'loading' }"
                    @click="selectModel(model.id)"
                  >
                    <div class="model-info">
                      <span class="model-name">{{ model.name }}</span>
                      <span class="model-meta">{{ model.size }} · {{ model.backend }}</span>
                    </div>
                    <div
                      class="model-status-indicator"
                      :class="model.status"
                    >
                      <span v-if="model.status === 'loaded'">●</span>
                      <span
                        v-else-if="model.status === 'loading'"
                        class="loading-spinner"
                      />
                      <span v-else>○</span>
                    </div>
                  </div>
                </div>
              </div>
            </transition>
          </div>
        </div>

        <div class="top-bar-right">
          <button
            class="icon-btn"
            title="清空对话"
            @click="clearChat"
          >
            <el-icon><Delete /></el-icon>
          </button>
        </div>
      </header>

      <!-- 消息区域 -->
      <div
        ref="messagesContainer"
        class="messages-area"
      >
        <!-- 滚动控制按钮 -->
        <div
          v-if="messages.length > 0"
          class="scroll-controls"
        >
          <button
            class="scroll-btn scroll-to-top"
            title="回到顶部"
            @click="scrollToTop"
          >
            <el-icon><ArrowUp /></el-icon>
          </button>
          <button
            class="scroll-btn scroll-to-bottom"
            title="回到底部"
            @click="scrollToBottom"
          >
            <el-icon><ArrowDown /></el-icon>
          </button>
        </div>
        
        <!-- 欢迎界面 -->
        <div
          v-if="messages.length === 0"
          class="welcome-screen"
        >
          <div class="welcome-content">
            <div class="welcome-logo">
              <div class="logo-ring" />
              <div class="logo-ring" />
              <div class="logo-ring" />
              <el-icon><ChatDotRound /></el-icon>
            </div>
            <h1 class="welcome-title">
              有什么可以帮助你？
            </h1>
            <p class="welcome-subtitle">
              选择模型后开始智能对话
            </p>
            
            <div class="quick-actions">
              <button
                class="quick-btn"
                @click="sendQuickMessage('帮我写一段Python代码')"
              >
                <el-icon><Edit /></el-icon>
                <span>帮我写代码</span>
              </button>
              <button
                class="quick-btn"
                @click="sendQuickMessage('解释量子计算')"
              >
                <el-icon><Lightning /></el-icon>
                <span>解释概念</span>
              </button>
              <button
                class="quick-btn"
                @click="sendQuickMessage('翻译这段文字')"
              >
                <el-icon><Document /></el-icon>
                <span>翻译文本</span>
              </button>
              <button
                class="quick-btn"
                @click="sendQuickMessage('分析数据')"
              >
                <el-icon><DataAnalysis /></el-icon>
                <span>数据分析</span>
              </button>
            </div>
          </div>
        </div>

        <!-- 消息列表 -->
        <div
          v-else
          class="messages-list"
        >
          <!-- 加载更多按钮 -->
          <div
            v-if="hasMoreMessages"
            class="load-more"
          >
            <button
              class="load-more-btn"
              @click="displayMessageCount += 20"
            >
              加载更多消息 (还有 {{ messages.length - displayMessageCount }} 条)
            </button>
          </div>
          <div 
            v-for="(msg, index) in displayedMessages" 
            :key="messages.length - displayedMessages.length + index"
            class="message"
            :class="[msg.role, { 'has-image': msg.images?.length }]"
          >
            <!-- 头像 -->
            <div class="message-avatar">
              <div
                v-if="msg.role === 'user'"
                class="avatar user"
              >
                <el-icon><User /></el-icon>
              </div>
              <div
                v-else
                class="avatar ai"
              >
                <svg
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                >
                  <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
                </svg>
              </div>
            </div>

            <!-- 内容 -->
            <div class="message-body">
              <!-- 调试信息 -->
              <div v-if="msg.role === 'assistant'" style="font-size: 10px; color: #666; margin-bottom: 4px;">
                thinking: {{ msg.thinking ? '有内容 (' + msg.thinking.length + ' 字符)' : '无' }}
              </div>
              
              <!-- 思考过程 -->
              <div
                v-if="msg.thinking && msg.thinking.length > 0"
                class="thinking-block"
              >
                <div
                  class="thinking-header"
                  @click="msg.showThinking = !msg.showThinking"
                >
                  <div class="thinking-title">
                    <svg class="thinking-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
                      <circle cx="12" cy="12" r="3"/>
                      <path d="M12 8v2M12 14v2M8 12h2M14 12h2"/>
                    </svg>
                    <span>Reasoning</span>
                  </div>
                  <el-icon
                    class="expand-icon"
                    :class="{ expanded: msg.showThinking }"
                  >
                    <ArrowDown />
                  </el-icon>
                </div>
                <transition name="expand">
                  <div
                    v-show="msg.showThinking"
                    class="thinking-content"
                  >
                    <div class="thinking-label">Thinking Process:</div>
                    <div class="thinking-text" v-html="renderMarkdown(msg.thinking)"></div>
                  </div>
                </transition>
              </div>

              <!-- 图片 -->
              <div
                v-if="msg.images?.length"
                class="message-images"
              >
                <div 
                  v-for="(img, idx) in msg.images" 
                  :key="idx"
                  class="image-frame"
                  @click="previewImage(img)"
                >
                  <img :src="'data:image/jpeg;base64,' + img">
                </div>
              </div>

              <!-- 文本内容 - 流式过程中也实时渲染 Markdown -->
              <div
                class="message-text"
                v-html="renderMarkdown(msg.content)"
              />

              <!-- 工具调用 -->
              <div
                v-if="msg.tool_calls?.length"
                class="tool-calls"
              >
                <div
                  v-for="(tool, idx) in msg.tool_calls"
                  :key="idx"
                  class="tool-call"
                >
                  <div class="tool-header">
                    <el-icon><Tools /></el-icon>
                    <span>{{ tool.function.name }}</span>
                  </div>
                </div>
              </div>

              <!-- 统计信息 -->
              <div
                v-if="msg.stats"
                class="message-stats"
              >
                <!-- 切换按钮 -->
                <span
                  class="stat-item mode-toggle"
                  :title="msg.showPromptStats ? '点击切换到生成统计' : '点击切换到Prompt处理统计'"
                  @click="msg.showPromptStats = !msg.showPromptStats"
                >
                  <el-icon><Switch /></el-icon>
                  {{ msg.showPromptStats ? 'Prompt处理' : '生成' }}
                </span>
                
                <!-- Prompt 处理统计 -->
                <template v-if="msg.showPromptStats">
                  <span class="stat-item">
                    <el-icon><Document /></el-icon>
                    {{ msg.stats.promptTokens.toLocaleString() }} tokens
                  </span>
                  <span class="stat-item">
                    <el-icon><Timer /></el-icon>
                    {{ msg.stats.promptProcessTime }}s
                  </span>
                  <span class="stat-item">
                    <el-icon><Odometer /></el-icon>
                    {{ msg.stats.promptTokensPerSecond }} t/s
                  </span>
                </template>
                
                <!-- 生成统计 -->
                <template v-else>
                  <span class="stat-item">
                    <el-icon><Document /></el-icon>
                    {{ msg.stats.generationTokens.toLocaleString() }} tokens
                  </span>
                  <span class="stat-item">
                    <el-icon><Timer /></el-icon>
                    {{ msg.stats.generationTime }}s
                  </span>
                  <span class="stat-item">
                    <el-icon><Odometer /></el-icon>
                    {{ msg.stats.generationTokensPerSecond }} t/s
                  </span>
                </template>
              </div>

              <!-- 消息操作 -->
              <div class="message-actions">
                <button
                  class="action-btn"
                  title="复制"
                  @click="copyMessage(msg.content)"
                >
                  <el-icon><CopyDocument /></el-icon>
                </button>
                <button
                  v-if="msg.role === 'assistant' && (messages.length - displayedMessages.length + index) === messages.length - 1"
                  class="action-btn"
                  title="重新生成"
                  @click="regenerateMessage(messages.length - displayedMessages.length + index)"
                >
                  <el-icon><Refresh /></el-icon>
                </button>
              </div>
            </div>
          </div>

          <!-- 加载状态 -->
          <div
            v-if="loading"
            class="message loading"
          >
            <div class="message-avatar">
              <div class="avatar ai">
                <svg
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                >
                  <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
                </svg>
              </div>
            </div>
            <div class="message-body">
              <div class="typing-indicator">
                <span />
                <span />
                <span />
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 输入区域 -->
      <div class="input-area">
        <!-- 上下文使用量指示器 -->
        <div 
          v-if="currentModel"
          class="context-usage-bar"
        >
          <div class="context-usage-info">
            <span class="context-label">上下文使用</span>
            <span class="context-stats">
              {{ contextUsage.used.toLocaleString() }} / {{ contextUsage.max.toLocaleString() }}
              <span 
                class="context-percentage"
                :style="{ color: contextUsage.color }"
              >
                ({{ contextUsage.percentage }}%)
              </span>
            </span>
          </div>
          <div class="context-progress">
            <div 
              class="context-progress-fill"
              :style="{ 
                width: contextUsage.percentage + '%',
                backgroundColor: contextUsage.color 
              }"
            />
          </div>
        </div>
        
        <div class="input-container">
          <!-- 图片预览 -->
          <div
            v-if="selectedImages.length"
            class="image-preview-bar"
          >
            <div
              v-for="(img, idx) in selectedImages"
              :key="idx"
              class="preview-item"
            >
              <img :src="img.preview">
              <button
                class="remove-image"
                @click="removeImage(idx)"
              >
                <el-icon><Close /></el-icon>
              </button>
            </div>
          </div>

          <div class="input-row">
            <button
              class="attach-btn"
              @click="triggerImageUpload"
            >
              <el-icon><Paperclip /></el-icon>
            </button>
            <input 
              ref="imageInput"
              type="file" 
              accept="image/*" 
              multiple 
              style="display: none"
              @change="handleImageSelect"
            >
            
            <div class="input-wrapper">
              <textarea 
                ref="textarea"
                v-model="inputMessage"
                placeholder="输入消息..."
                rows="1"
                @keydown.enter.prevent="sendMessage"
                @input="autoResize"
              />
            </div>

            <button 
              class="send-btn" 
              :class="{ active: inputMessage.trim() || selectedImages.length, loading }"
              :disabled="!inputMessage.trim() && !selectedImages.length || loading"
              @click="sendMessage"
            >
              <el-icon v-if="!loading">
                <Promotion />
              </el-icon>
              <el-icon
                v-else
                class="spinning"
              >
                <Loading />
              </el-icon>
            </button>
          </div>

          <div class="input-hint">
            <span>Enter 发送 · Shift + Enter 换行</span>
          </div>
        </div>
      </div>
    </main>

  </div>
</template>

<script setup>
import { ref, computed, nextTick, onMounted, shallowRef, watch } from 'vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import { useModelStore } from '@/stores/models'
import { useChatHistoryStore } from '@/stores/chatHistory'
import { chatApi } from '@/api/client'
import { storeToRefs } from 'pinia'
import { RecycleScroller } from 'vue-virtual-scroller'
import 'vue-virtual-scroller/dist/vue-virtual-scroller.css'
import {
  Plus, ChatRound, Setting, Close, Fold, Expand,
  ArrowDown, ArrowUp, Delete, ChatDotRound, Edit, Lightning,
  DataAnalysis, User, View, ArrowDown as ArrowDownIcon,
  Tools, CopyDocument, Refresh, Paperclip, Promotion,
  Loading, Document, Timer, Odometer, Switch, More
} from '@element-plus/icons-vue'

// 注册虚拟滚动组件
const components = { RecycleScroller }

// Store
const modelStore = useModelStore()
const chatHistoryStore = useChatHistoryStore()
const { models: availableModels, loadedModels, loading: modelLoading } = storeToRefs(modelStore)
const { sortedConversations, currentConversation: currentConversationId } = storeToRefs(chatHistoryStore)

// 状态
const sidebarCollapsed = ref(false)
const modelDropdownOpen = ref(false)
const inputMessage = ref('')
const selectedImages = ref([])
const loading = ref(false)
const messagesContainer = ref(null)
const textarea = ref(null)
const imageInput = ref(null)

// 数据 - 使用 shallowRef 减少响应式开销
const messages = shallowRef([])
// Markdown 渲染缓存
const markdownCache = new Map()
// 显示的消息数量限制（性能优化）
const MAX_DISPLAY_MESSAGES = 50
const displayMessageCount = ref(MAX_DISPLAY_MESSAGES)
// 计算实际显示的消息
const displayedMessages = computed(() => {
  const all = messages.value
  if (all.length <= displayMessageCount.value) {
    return all
  }
  // 只返回最近的消息
  return all.slice(-displayMessageCount.value)
})
// 是否有更多历史消息
const hasMoreMessages = computed(() => messages.value.length > displayMessageCount.value)
const selectedModel = ref('')
const editingConversationId = ref(null)
const editingTitle = ref('')

const currentModel = computed(() => {
  return availableModels.value.find(m => m.id === selectedModel.value)
})

const currentConversationTitle = computed(() => {
  return chatHistoryStore.currentConversation?.title || '新对话'
})

// 计算当前上下文使用量
const contextUsage = computed(() => {
  const maxContext = currentModel.value?.max_context || 32768
  
  // 计算所有消息的 token 总数
  let usedTokens = 0
  messages.value.forEach(msg => {
    if (msg.stats) {
      if (msg.role === 'user') {
        usedTokens += msg.stats.promptTokens || 0
      } else {
        usedTokens += msg.stats.generationTokens || 0
      }
    } else {
      // 如果没有 stats，估算 token 数
      usedTokens += estimateTokens(msg.content)
    }
  })
  
  // 加上当前输入的 token 数
  const inputTokens = estimateTokens(inputMessage.value)
  const totalUsed = usedTokens + inputTokens
  const percentage = Math.min((totalUsed / maxContext) * 100, 100)
  
  return {
    used: totalUsed,
    max: maxContext,
    percentage: percentage.toFixed(1),
    color: percentage > 90 ? '#f56c6c' : percentage > 70 ? '#e6a23c' : '#67c23a'
  }
})

// 方法
// 配置 marked
marked.setOptions({
  breaks: true,
  gfm: true,
  headerIds: false,
  mangle: false
})

const renderMarkdown = (content) => {
  if (!content) return ''
  // 检查缓存
  if (markdownCache.has(content)) {
    return markdownCache.get(content)
  }
  // 限制缓存大小
  if (markdownCache.size > 100) {
    const firstKey = markdownCache.keys().next().value
    markdownCache.delete(firstKey)
  }
  const html = marked.parse(content)
  const sanitized = DOMPurify.sanitize(html)
  markdownCache.set(content, sanitized)
  return sanitized
}

const autoResize = () => {
  const el = textarea.value
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 200) + 'px'
}

const sendMessage = async () => {
  console.log('[Chat] sendMessage called')
  console.log('[Chat] inputMessage:', inputMessage.value)
  console.log('[Chat] selectedModel:', selectedModel.value)
  console.log('[Chat] loading:', loading.value)
  
  if ((!inputMessage.value.trim() && !selectedImages.value.length) || loading.value) {
    console.log('[Chat] Blocked: empty message or loading')
    return
  }
  if (!selectedModel.value) {
    alert('请先选择一个模型')
    return
  }

  const userMessage = {
    role: 'user',
    content: inputMessage.value,
    images: selectedImages.value.map(img => img.data)
  }

  // 使用新数组触发 shallowRef 更新
  messages.value = [...messages.value, userMessage]
  inputMessage.value = ''
  selectedImages.value = []
  loading.value = true

  await nextTick()
  scrollToBottom(true)

  // 创建助手消息占位（使用 ref 而不是 reactive，避免响应式问题）
  const assistantMessage = ref({
    role: 'assistant',
    content: '',
    thinking: '',
    showThinking: true,
    showTokenDetail: false,
    showPromptStats: false,
    stats: null,
    isStreaming: true
  })
  messages.value = [...messages.value, assistantMessage.value]
  
  // 统计信息
  const startTime = Date.now()
  let firstTokenTime = null
  let inputTokens = 0
  let outputTokens = 0

  try {
    // 读取系统提示词
    let systemMessage = ''
    const savedSettings = localStorage.getItem('neuralchat-settings')
    if (savedSettings) {
      try {
        const settings = JSON.parse(savedSettings)
        systemMessage = settings.systemMessage || ''
      } catch (e) {
        console.error('Failed to parse settings:', e)
      }
    }

    // 构建消息历史（支持多模态）
    const history = []

    // 添加系统消息（如果有）
    if (systemMessage.trim()) {
      history.push({
        role: 'system',
        content: systemMessage.trim()
      })
    }

    // 添加用户消息历史
    messages.value
      .filter(m => m.role !== 'assistant' || m.content)
      .forEach(m => {
        // 如果有图片，使用多模态格式
        if (m.images && m.images.length > 0) {
          const content = [
            { type: 'text', text: m.content || '' }
          ]
          // 添加图片
          m.images.forEach(img => {
            content.push({
              type: 'image_url',
              image_url: {
                url: `data:image/jpeg;base64,${img}`
              }
            })
          })
          history.push({
            role: m.role,
            content: content
          })
        } else {
          // 纯文本消息
          history.push({
            role: m.role,
            content: m.content
          })
        }
      })

    // 调用流式 API
    const streamData = {
      model: selectedModel.value,
      messages: history,
      stream: true,
      temperature: 0.7
      // max_tokens 由后端默认设置 128K
    }

    for await (const chunk of chatApi.stream(streamData)) {
      console.log('Stream chunk:', JSON.stringify(chunk, null, 2))
      
      // 处理 usage 信息（通常在最后一个 chunk）
      if (chunk.usage) {
        inputTokens = chunk.usage.prompt_tokens || 0
        outputTokens = chunk.usage.completion_tokens || 0
      }
      
      const delta = chunk.choices?.[0]?.delta
      if (delta) {
        console.log('Delta:', JSON.stringify(delta, null, 2))
        
        // 记录第一个 token 的时间（用于区分 prompt 处理时间和生成时间）
        if (!firstTokenTime && (delta.content || delta.reasoning_content || delta.thinking || delta.reasoning)) {
          firstTokenTime = Date.now()
        }
        
        // 处理思考内容 - 检查多种可能的字段名
        const reasoningContent = delta.reasoning_content || delta.thinking || delta.reasoning
        if (reasoningContent) {
          assistantMessage.value.thinking += reasoningContent
        }
        // 处理正式回复
        if (delta.content) {
          assistantMessage.value.content += delta.content
        }
        // 节流滚动，不阻塞流式输出
        scrollToBottom()
      }
    }
    
    // 计算并保存统计信息
    const endTime = Date.now()
    const totalDuration = (endTime - startTime) / 1000 // 秒
    
    // 如果后端没有返回 usage，通过内容长度估算 token 数
    // 中文字符按 1 token 计算，英文按 0.25 token/字符 计算
    if (inputTokens === 0) {
      const inputText = history.map(m => m.content).join('')
      inputTokens = estimateTokens(inputText)
    }
    if (outputTokens === 0) {
      const outputText = assistantMessage.value.content + assistantMessage.value.thinking
      outputTokens = estimateTokens(outputText)
    }
    
    // 计算 prompt 处理时间和生成时间
    // prompt 处理时间 = 第一个 token 到达前的时间
    // 生成时间 = 第一个 token 到达后到结束的时间
    const promptProcessTime = firstTokenTime ? ((firstTokenTime - startTime) / 1000) : 0
    const generationTime = firstTokenTime ? ((endTime - firstTokenTime) / 1000) : totalDuration
    
    // 计算速度
    const promptTokensPerSecond = promptProcessTime > 0 ? (inputTokens / promptProcessTime).toFixed(2) : 0
    const generationTokensPerSecond = generationTime > 0 ? (outputTokens / generationTime).toFixed(2) : 0
    
    assistantMessage.value.stats = {
      // Prompt 处理统计
      promptTokens: inputTokens,
      promptProcessTime: promptProcessTime.toFixed(2),
      promptTokensPerSecond,
      // 生成统计
      generationTokens: outputTokens,
      generationTime: generationTime.toFixed(2),
      generationTokensPerSecond,
      // 总计
      totalTokens: inputTokens + outputTokens,
      totalDuration: totalDuration.toFixed(1)
    }
    console.log('Stats:', assistantMessage.value.stats)
    // 流式完成，标记为已完成并触发 markdown 渲染
    assistantMessage.value.isStreaming = false
  } catch (error) {
    console.error('Chat error:', error)
    assistantMessage.value.content = '抱歉，发生了错误：' + error.message
    assistantMessage.value.isStreaming = false
  } finally {
    loading.value = false
    await nextTick()
    scrollToBottom(true)
    // 保存对话到历史记录
    if (chatHistoryStore.currentConversationId) {
      chatHistoryStore.updateMessages(chatHistoryStore.currentConversationId, messages.value)
      chatHistoryStore.updateModel(chatHistoryStore.currentConversationId, selectedModel.value)
    }
  }
}

// 估算 token 数量（中文 1:1，英文 4:1）
const estimateTokens = (text) => {
  if (!text) return 0
  // 统计中文字符数量
  const chineseChars = (text.match(/[\u4e00-\u9fff]/g) || []).length
  // 统计其他字符数量
  const otherChars = text.length - chineseChars
  // 估算：中文 1:1，英文 4:1
  return chineseChars + Math.floor(otherChars / 4)
}

const sendQuickMessage = (text) => {
  inputMessage.value = text
  sendMessage()
}

let scrollTimeout = null
const scrollToBottom = (immediate = false) => {
  if (scrollTimeout) {
    clearTimeout(scrollTimeout)
  }
  
  const doScroll = () => {
    const container = messagesContainer.value
    if (container) {
      container.scrollTo({
        top: container.scrollHeight,
        behavior: immediate ? 'auto' : 'smooth'
      })
    }
  }
  
  if (immediate) {
    doScroll()
  } else {
    scrollTimeout = setTimeout(doScroll, 50)
  }
}

const scrollToTop = () => {
  const container = messagesContainer.value
  if (container) {
    container.scrollTo({
      top: 0,
      behavior: 'smooth'
    })
  }
}

const triggerImageUpload = () => {
  imageInput.value?.click()
}

const handleImageSelect = (e) => {
  const files = Array.from(e.target.files)
  files.forEach(file => {
    const reader = new FileReader()
    reader.onload = (e) => {
      selectedImages.value.push({
        preview: e.target.result,
        data: e.target.result.split(',')[1]
      })
    }
    reader.readAsDataURL(file)
  })
}

const removeImage = (idx) => {
  selectedImages.value.splice(idx, 1)
}

const startNewChat = () => {
  const newConv = chatHistoryStore.createConversation()
  messages.value = []
  displayMessageCount.value = MAX_DISPLAY_MESSAGES
  selectedModel.value = ''
}

const loadConversation = (id) => {
  chatHistoryStore.setCurrentConversation(id)
  const conv = chatHistoryStore.currentConversation
  if (conv) {
    messages.value = JSON.parse(JSON.stringify(conv.messages))
    displayMessageCount.value = MAX_DISPLAY_MESSAGES
    selectedModel.value = conv.model || ''
  }
}

const deleteConversation = (id) => {
  chatHistoryStore.deleteConversation(id)
  if (chatHistoryStore.currentConversationId === null) {
    messages.value = []
    selectedModel.value = ''
  }
}

const startEditTitle = (conv) => {
  editingConversationId.value = conv.id
  editingTitle.value = conv.title
}

const saveTitle = (id) => {
  if (editingTitle.value.trim()) {
    chatHistoryStore.renameConversation(id, editingTitle.value.trim())
  }
  editingConversationId.value = null
  editingTitle.value = ''
}

const cancelEdit = () => {
  editingConversationId.value = null
  editingTitle.value = ''
}

const selectModel = async (id) => {
  const model = availableModels.value.find(m => m.id === id)
  if (!model) return
  
  // 如果模型未加载，先加载模型
  if (model.status !== 'loaded') {
    try {
      await modelStore.loadModel(id)
    } catch (error) {
      console.error('Failed to load model:', error)
      alert('模型加载失败: ' + error.message)
      return
    }
  }
  
  selectedModel.value = id
  modelDropdownOpen.value = false
}

const closeModelDropdown = () => {
  modelDropdownOpen.value = false
}

const clearChat = () => {
  messages.value = []
}

const copyMessage = (content) => {
  navigator.clipboard.writeText(content)
}

const regenerateMessage = (index) => {
  // 重新生成
}

const previewImage = (img) => {
  // 预览图片
}

// 设置
const theme = ref('dark')

// 应用主题
const applyTheme = () => {
  if (theme.value === 'dark') {
    document.documentElement.classList.remove('light-theme')
  } else {
    document.documentElement.classList.add('light-theme')
  }
}

const clearAllConversations = () => {
  if (confirm('确定要清空所有对话吗？此操作不可恢复。')) {
    chatHistoryStore.clearAllConversations()
    messages.value = []
    selectedModel.value = ''
  }
}

onMounted(async () => {
  // 加载模型列表
  await modelStore.fetchModels()

  // 加载历史对话
  chatHistoryStore.loadFromStorage()

  // 如果有当前对话，加载其消息
  if (chatHistoryStore.currentConversationId) {
    const conv = chatHistoryStore.currentConversation
    if (conv) {
      messages.value = JSON.parse(JSON.stringify(conv.messages))
      selectedModel.value = conv.model || ''
    }
  }

  // 如果有已加载的模型且当前对话没有模型，自动选择第一个
  if (loadedModels.value.length > 0 && !selectedModel.value) {
    selectedModel.value = loadedModels.value[0]
  }

  // 加载保存的设置
  const saved = localStorage.getItem('chat-settings')
  if (saved) {
    try {
      const settings = JSON.parse(saved)
      theme.value = settings.theme || 'dark'
      applyTheme()
    } catch (e) {
      console.error('Failed to load settings:', e)
    }
  }
})
</script>

<style lang="scss" scoped>
.chat-modern {
  display: flex;
  height: 100vh;
  background: linear-gradient(135deg, #0f0f1a 0%, #1a1a2e 50%, #16213e 100%);
  color: #e4e4e7;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
  overflow: hidden;
}

// 侧边栏
.sidebar {
  width: 260px;
  background: rgba(15, 15, 26, 0.8);
  backdrop-filter: blur(20px);
  border-right: 1px solid rgba(255, 255, 255, 0.05);
  display: flex;
  flex-direction: column;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);

  .sidebar-collapsed & {
    width: 60px;
  }
}

.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;

  .sidebar-collapsed & {
    display: none;
  }
}

.brand-icon {
  width: 32px;
  height: 32px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;

  svg {
    width: 18px;
    height: 18px;
    color: white;
  }
}

.brand-text {
  font-size: 18px;
  font-weight: 700;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.sidebar-toggle {
  width: 32px;
  height: 32px;
  border: none;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 8px;
  color: #9ca3af;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    background: rgba(255, 255, 255, 0.1);
    color: white;
  }
}

.new-chat-btn {
  margin: 16px;
  padding: 12px 16px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
  border-radius: 12px;
  color: white;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  transition: all 0.2s;

  &:hover {
    transform: translateY(-1px);
    box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4);
  }

  .sidebar-collapsed & {
    padding: 12px;

    span {
      display: none;
    }
  }
}

.conversations {
  flex: 1;
  overflow-y: auto;
  padding: 0 12px;
}

.section-title {
  padding: 12px 4px;
  font-size: 11px;
  font-weight: 600;
  color: #6b7280;
  text-transform: uppercase;
  letter-spacing: 0.5px;

  .sidebar-collapsed & {
    display: none;
  }
}

.conversation-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.conversation-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s;
  color: #9ca3af;

  &:hover, &.active {
    background: rgba(255, 255, 255, 0.05);
    color: white;
  }

  &.active {
    background: rgba(102, 126, 234, 0.15);
  }

  .el-icon {
    font-size: 16px;
    flex-shrink: 0;
  }

  .sidebar-collapsed & {
    padding: 10px;
    justify-content: center;

    .conv-title, .conv-actions {
      display: none;
    }
  }
}

.conv-title {
  flex: 1;
  font-size: 13px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.conv-actions {
  display: flex;
  align-items: center;
  gap: 4px;
  opacity: 0;
  transition: all 0.2s;

  .conversation-item:hover & {
    opacity: 1;
  }

  .action-btn {
    width: 24px;
    height: 24px;
    border: none;
    background: transparent;
    border-radius: 6px;
    color: #6b7280;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.2s;

    &:hover {
      background: rgba(255, 255, 255, 0.1);
      color: white;
    }

    &.delete:hover {
      background: rgba(239, 68, 68, 0.2);
      color: #ef4444;
    }
  }
}

.conv-title-input {
  flex: 1;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(102, 126, 234, 0.5);
  border-radius: 6px;
  padding: 4px 8px;
  color: white;
  font-size: 13px;
  outline: none;

  &:focus {
    border-color: #667eea;
  }
}

.sidebar-footer {
  padding: 12px;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
}

.footer-btn {
  width: 100%;
  padding: 10px 12px;
  background: rgba(255, 255, 255, 0.05);
  border: none;
  border-radius: 10px;
  color: #9ca3af;
  font-size: 13px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 10px;
  transition: all 0.2s;

  &:hover {
    background: rgba(255, 255, 255, 0.1);
    color: white;
  }

  .sidebar-collapsed & {
    padding: 10px;
    justify-content: center;

    span {
      display: none;
    }
  }
}

// 主内容区
.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

// 顶部栏
.top-bar {
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  background: rgba(15, 15, 26, 0.5);
  backdrop-filter: blur(20px);
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  position: relative;
  z-index: 100;
}

.page-title {
  font-size: 18px;
  font-weight: 600;
  color: white;
}

.model-selector {
  position: relative;
  z-index: 1001;
}

.model-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 10px;
  color: white;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    background: rgba(255, 255, 255, 0.1);
  }
}

.model-status {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #6b7280;

  &.loaded {
    background: #10b981;
    box-shadow: 0 0 8px #10b981;
  }

  &.loading {
    background: #f59e0b;
    animation: pulse 1.5s infinite;
  }
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.model-dropdown {
  position: absolute;
  top: calc(100% + 8px);
  left: 50%;
  transform: translateX(-50%);
  width: 320px;
  max-height: 400px;
  background: rgba(30, 30, 46, 0.95);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 16px;
  padding: 8px;
  z-index: 1000;
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.5);
  display: flex;
  flex-direction: column;
}

.dropdown-enter-active,
.dropdown-leave-active {
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.dropdown-enter-from,
.dropdown-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(-10px);
}

.dropdown-header {
  padding: 12px 16px;
  font-size: 12px;
  font-weight: 600;
  color: #6b7280;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.model-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  overflow-y: auto;
  max-height: 320px;
  padding-right: 4px;

  &::-webkit-scrollbar {
    width: 4px;
  }

  &::-webkit-scrollbar-track {
    background: transparent;
  }

  &::-webkit-scrollbar-thumb {
    background: rgba(255, 255, 255, 0.2);
    border-radius: 2px;
  }

  &::-webkit-scrollbar-thumb:hover {
    background: rgba(255, 255, 255, 0.3);
  }
}

.model-option {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s;

  &:hover, &.active {
    background: rgba(102, 126, 234, 0.15);
  }

  &.loading {
    opacity: 0.7;
  }
}

.model-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.model-name {
  font-size: 14px;
  font-weight: 500;
  color: white;
}

.model-meta {
  font-size: 12px;
  color: #6b7280;
}

.model-status-indicator {
  font-size: 12px;

  &.loaded {
    color: #10b981;
  }

  &.loading {
    color: #f59e0b;
  }
}

.loading-spinner {
  display: inline-block;
  width: 12px;
  height: 12px;
  border: 2px solid #f59e0b;
  border-top-color: transparent;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.icon-btn {
  width: 36px;
  height: 36px;
  border: none;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 10px;
  color: #9ca3af;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;

  &:hover {
    background: rgba(255, 255, 255, 0.1);
    color: white;
  }
}

// 消息区域
.messages-area {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  position: relative;
}

// 滚动控制按钮
.scroll-controls {
  position: fixed;
  right: 32px;
  bottom: 200px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  z-index: 100;
  
  .scroll-btn {
    width: 44px;
    height: 44px;
    border-radius: 50%;
    border: 1px solid rgba(255, 255, 255, 0.1);
    background: rgba(30, 30, 46, 0.8);
    backdrop-filter: blur(12px);
    color: rgba(255, 255, 255, 0.7);
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    box-shadow: 
      0 4px 20px rgba(0, 0, 0, 0.3),
      0 0 0 1px rgba(255, 255, 255, 0.05) inset;
    
    &:hover {
      background: rgba(102, 126, 234, 0.9);
      color: white;
      transform: translateY(-2px);
      box-shadow: 
        0 8px 30px rgba(102, 126, 234, 0.4),
        0 0 0 1px rgba(255, 255, 255, 0.1) inset;
    }
    
    &:active {
      transform: translateY(0);
    }
    
    .el-icon {
      font-size: 18px;
    }
  }
  
  .scroll-to-top {
    &::before {
      content: '';
      position: absolute;
      inset: -2px;
      border-radius: 50%;
      background: linear-gradient(135deg, rgba(102, 126, 234, 0.3), transparent);
      opacity: 0;
      transition: opacity 0.3s;
      z-index: -1;
    }
    
    &:hover::before {
      opacity: 1;
    }
  }
}

.welcome-screen {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.welcome-content {
  text-align: center;
  max-width: 600px;
}

.welcome-logo {
  position: relative;
  width: 80px;
  height: 80px;
  margin: 0 auto 32px;
  display: flex;
  align-items: center;
  justify-content: center;

  .el-icon {
    font-size: 36px;
    color: #667eea;
    z-index: 10;
  }
}

.logo-ring {
  position: absolute;
  border: 2px solid rgba(102, 126, 234, 0.3);
  border-radius: 50%;
  animation: ripple 2s ease-out infinite;

  &:nth-child(1) {
    width: 100%;
    height: 100%;
  }

  &:nth-child(2) {
    width: 140%;
    height: 140%;
    animation-delay: 0.5s;
  }

  &:nth-child(3) {
    width: 180%;
    height: 180%;
    animation-delay: 1s;
  }
}

@keyframes ripple {
  0% {
    transform: scale(0.8);
    opacity: 1;
  }
  100% {
    transform: scale(1.2);
    opacity: 0;
  }
}

.load-more {
  display: flex;
  justify-content: center;
  padding: 16px;
  
  .load-more-btn {
    padding: 8px 16px;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 8px;
    color: #9ca3af;
    font-size: 13px;
    cursor: pointer;
    transition: all 0.2s;
    
    &:hover {
      background: rgba(102, 126, 234, 0.1);
      border-color: rgba(102, 126, 234, 0.3);
      color: #667eea;
    }
  }
}

.welcome-title {
  font-size: 32px;
  font-weight: 700;
  color: white;
  margin-bottom: 12px;
}

.welcome-subtitle {
  font-size: 16px;
  color: #6b7280;
  margin-bottom: 40px;
}

.quick-actions {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.quick-btn {
  padding: 16px 20px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  color: #e4e4e7;
  font-size: 14px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 12px;
  transition: all 0.2s;

  &:hover {
    background: rgba(102, 126, 234, 0.1);
    border-color: rgba(102, 126, 234, 0.3);
    transform: translateY(-2px);
  }

  .el-icon {
    font-size: 20px;
    color: #667eea;
  }
}

// 消息列表
.messages-list {
  display: flex;
  flex-direction: column;
  gap: 24px;
  max-width: 900px;
  margin: 0 auto;
}

.message {
  display: flex;
  gap: 16px;
  animation: messageIn 0.3s ease-out;

  &.user {
    flex-direction: row-reverse;

    .message-body {
      align-items: flex-end;
    }

    .message-text {
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white;
      border-radius: 18px 18px 4px 18px;
    }
  }

  &.assistant {
    .message-text {
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 4px 18px 18px 18px;
    }
  }
}

@keyframes messageIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.message-avatar {
  flex-shrink: 0;
}

.avatar {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;

  &.user {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
  }

  &.ai {
    background: rgba(255, 255, 255, 0.1);
    color: #667eea;

    svg {
      width: 20px;
      height: 20px;
    }
  }

  .el-icon {
    font-size: 18px;
  }
}

.message-body {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-width: calc(100% - 60px);
}

.thinking-block {
  background: #fafafa;
  border: 1px solid #e5e5e5;
  border-radius: 8px;
  overflow: hidden;
  margin-bottom: 12px;
}

.thinking-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    background: rgba(0, 0, 0, 0.02);
  }

  .thinking-title {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 14px;
    font-weight: 500;
    color: #374151;

    .thinking-icon {
      width: 18px;
      height: 18px;
      color: #6b7280;
    }
  }

  .expand-icon {
    font-size: 14px;
    color: #9ca3af;
    transition: transform 0.2s;

    &.expanded {
      transform: rotate(180deg);
    }
  }
}

.thinking-content {
  padding: 0 16px 16px;

  .thinking-label {
    font-size: 13px;
    font-weight: 600;
    color: #374151;
    margin-bottom: 12px;
  }

  .thinking-text {
    font-size: 13px;
    line-height: 1.7;
    color: #4b5563;

    :deep(p) {
      margin: 0 0 10px 0;

      &:last-child {
        margin-bottom: 0;
      }
    }

    :deep(ul), :deep(ol) {
      margin: 0 0 10px 0;
      padding-left: 20px;
    }

    :deep(li) {
      margin-bottom: 6px;
    }

    :deep(strong) {
      font-weight: 600;
      color: #1f2937;
    }

    :deep(code) {
      background: rgba(0, 0, 0, 0.05);
      padding: 2px 6px;
      border-radius: 4px;
      font-family: 'JetBrains Mono', monospace;
      font-size: 12px;
    }
  }
}

.expand-enter-active,
.expand-leave-active {
  transition: all 0.2s ease;
}

.expand-enter-from,
.expand-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

.message-images {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 8px;
}

.image-frame {
  width: 200px;
  height: 150px;
  border-radius: 12px;
  overflow: hidden;
  cursor: pointer;
  transition: transform 0.2s;

  &:hover {
    transform: scale(1.02);
  }

  img {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }
}

.message-text {
  padding: 14px 18px;
  font-size: 15px;
  line-height: 1.8;
  color: #e4e4e7;

  // 段落
  :deep(p) {
    margin: 0 0 14px;

    &:last-child {
      margin-bottom: 0;
    }
  }

  // 标题 - 使用渐变色彩区分层级
  :deep(h1) {
    font-size: 22px;
    font-weight: 700;
    margin: 28px 0 18px;
    padding: 12px 0;
    background: linear-gradient(135deg, #fff 0%, #a0aec0 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    border-bottom: 2px solid rgba(102, 126, 234, 0.3);
  }

  :deep(h2) {
    font-size: 19px;
    font-weight: 650;
    margin: 24px 0 14px;
    padding: 8px 0;
    color: #f0f0f5;
    border-left: 4px solid #667eea;
    padding-left: 12px;
  }

  :deep(h3) {
    font-size: 16px;
    font-weight: 600;
    margin: 20px 0 12px;
    color: #d4d4d8;
    display: flex;
    align-items: center;
    gap: 8px;

    &::before {
      content: '';
      width: 6px;
      height: 6px;
      background: linear-gradient(135deg, #667eea, #764ba2);
      border-radius: 50%;
    }
  }

  :deep(h4, h5, h6) {
    font-size: 14px;
    font-weight: 600;
    margin: 16px 0 10px;
    color: #a1a1aa;
  }

  // 列表 - 彩色标记点
  :deep(ul, ol) {
    margin: 14px 0;
    padding-left: 0;
    list-style: none;
  }

  :deep(ul li) {
    margin: 10px 0;
    padding-left: 20px;
    position: relative;

    &::before {
      content: '';
      position: absolute;
      left: 0;
      top: 10px;
      width: 6px;
      height: 6px;
      background: linear-gradient(135deg, #667eea, #764ba2);
      border-radius: 50%;
    }
  }

  :deep(ol) {
    counter-reset: item;
  }

  :deep(ol li) {
    margin: 10px 0;
    padding-left: 28px;
    position: relative;

    &::before {
      content: counter(item);
      counter-increment: item;
      position: absolute;
      left: 0;
      top: 2px;
      width: 20px;
      height: 20px;
      background: linear-gradient(135deg, #667eea, #764ba2);
      border-radius: 50%;
      font-size: 11px;
      font-weight: 600;
      color: white;
      display: flex;
      align-items: center;
      justify-content: center;
    }
  }

  :deep(ul ul, ol ol, ul ol, ol ul) {
    margin: 8px 0;
  }

  // 引用 - 玻璃拟态效果
  :deep(blockquote) {
    margin: 18px 0;
    padding: 16px 20px;
    border-left: 3px solid #f093fb;
    background: linear-gradient(135deg, rgba(240, 147, 251, 0.08) 0%, rgba(245, 87, 108, 0.05) 100%);
    border-radius: 0 12px 12px 0;
    color: #d4d4d8;
    font-style: italic;

    p:last-child {
      margin-bottom: 0;
    }
  }

  // 代码 - 彩色高亮
  :deep(code) {
    background: rgba(102, 126, 234, 0.15);
    padding: 3px 8px;
    border-radius: 6px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 13px;
    color: #a5b4fc;
    border: 1px solid rgba(102, 126, 234, 0.2);
  }

  :deep(pre) {
    background: linear-gradient(135deg, rgba(10, 10, 20, 0.8) 0%, rgba(20, 20, 35, 0.8) 100%);
    padding: 20px;
    border-radius: 12px;
    overflow-x: auto;
    margin: 18px 0;
    border: 1px solid rgba(102, 126, 234, 0.15);

    code {
      background: none;
      padding: 0;
      color: #e2e8f0;
      font-size: 13px;
      line-height: 1.7;
      border: none;
    }
  }

  // 表格 - 渐变表头
  :deep(table) {
    width: 100%;
    border-collapse: separate;
    border-spacing: 0;
    margin: 18px 0;
    font-size: 14px;
    border-radius: 12px;
    overflow: hidden;
    border: 1px solid rgba(255, 255, 255, 0.08);
  }

  :deep(th, td) {
    padding: 12px 16px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.06);
    text-align: left;
  }

  :deep(th) {
    background: linear-gradient(135deg, rgba(102, 126, 234, 0.2) 0%, rgba(118, 75, 162, 0.15) 100%);
    font-weight: 600;
    color: #fff;
    text-transform: uppercase;
    font-size: 12px;
    letter-spacing: 0.5px;
  }

  :deep(tr:last-child td) {
    border-bottom: none;
  }

  :deep(tr:nth-child(even)) {
    background: rgba(255, 255, 255, 0.02);
  }

  :deep(tr:hover) {
    background: rgba(102, 126, 234, 0.05);
  }

  // 链接 - 发光效果
  :deep(a) {
    color: #818cf8;
    text-decoration: none;
    border-bottom: 1px solid rgba(129, 140, 248, 0.3);
    transition: all 0.2s;
    font-weight: 500;

    &:hover {
      color: #a5b4fc;
      border-bottom-color: #a5b4fc;
      text-shadow: 0 0 20px rgba(129, 140, 248, 0.5);
    }
  }

  // 分割线 - 渐变
  :deep(hr) {
    border: none;
    height: 1px;
    background: linear-gradient(90deg, transparent 0%, rgba(102, 126, 234, 0.5) 50%, transparent 100%);
    margin: 28px 0;
  }

  // 强调 - 使用色彩而非仅加粗
  :deep(strong, b) {
    font-weight: 650;
    color: #c7d2fe;
    background: linear-gradient(135deg, rgba(102, 126, 234, 0.25) 0%, rgba(118, 75, 162, 0.2) 100%);
    padding: 3px 8px;
    border-radius: 6px;
    border: 1px solid rgba(165, 180, 252, 0.3);
    text-shadow: 0 0 20px rgba(165, 180, 252, 0.3);
  }

  :deep(em, i) {
    font-style: italic;
    color: #f093fb;
  }

  // 删除线
  :deep(del, s) {
    text-decoration: line-through;
    color: #6b7280;
    opacity: 0.7;
  }

  // 图片 - 带边框和阴影
  :deep(img) {
    max-width: 100%;
    border-radius: 12px;
    margin: 16px 0;
    border: 1px solid rgba(255, 255, 255, 0.08);
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
  }

  // 任务列表
  :deep(input[type="checkbox"]) {
    accent-color: #667eea;
    margin-right: 8px;
  }

  // 定义列表
  :deep(dt) {
    font-weight: 600;
    color: #f0f0f5;
    margin-top: 12px;
  }

  :deep(dd) {
    margin-left: 20px;
    color: #a1a1aa;
    margin-top: 4px;
  }
}

.tool-calls {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.tool-call {
  background: rgba(102, 126, 234, 0.1);
  border: 1px solid rgba(102, 126, 234, 0.2);
  border-radius: 8px;
  padding: 10px 14px;
}

.tool-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #667eea;
}

.message-stats {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  font-size: 12px;
  color: #6b7280;

  .stat-item {
    display: flex;
    align-items: center;
    gap: 4px;

    .el-icon {
      font-size: 14px;
    }

    &.token-toggle,
    &.mode-toggle {
      cursor: pointer;
      padding: 2px 6px;
      border-radius: 4px;
      transition: all 0.2s;

      &:hover {
        background: rgba(255, 255, 255, 0.1);
        color: #a0aec0;
      }
    }

    &.mode-toggle {
      background: rgba(102, 126, 234, 0.15);
      color: #667eea;
      font-weight: 500;

      &:hover {
        background: rgba(102, 126, 234, 0.25);
        color: #7c8ce8;
      }
    }
  }
}

.message-actions {
  display: flex;
  gap: 4px;
  opacity: 0;
  transition: opacity 0.2s;

  .message:hover & {
    opacity: 1;
  }
}

.action-btn {
  width: 28px;
  height: 28px;
  border: none;
  background: transparent;
  border-radius: 6px;
  color: #6b7280;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;

  &:hover {
    background: rgba(255, 255, 255, 0.1);
    color: white;
  }
}

// 加载动画
.typing-indicator {
  display: flex;
  gap: 4px;
  padding: 18px;

  span {
    width: 8px;
    height: 8px;
    background: #667eea;
    border-radius: 50%;
    animation: typing 1.4s ease-in-out infinite;

    &:nth-child(2) {
      animation-delay: 0.2s;
    }

    &:nth-child(3) {
      animation-delay: 0.4s;
    }
  }
}

@keyframes typing {
  0%, 60%, 100% {
    transform: translateY(0);
    opacity: 0.4;
  }
  30% {
    transform: translateY(-10px);
    opacity: 1;
  }
}

// 输入区域
.input-area {
  padding: 20px 24px;
  background: rgba(15, 15, 26, 0.8);
  backdrop-filter: blur(20px);
  border-top: 1px solid rgba(255, 255, 255, 0.05);
}

// 上下文使用量指示器
.context-usage-bar {
  max-width: 900px;
  margin: 0 auto 12px;
  padding: 8px 12px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 8px;
  
  .context-usage-info {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 6px;
    font-size: 12px;
    
    .context-label {
      color: rgba(255, 255, 255, 0.5);
    }
    
    .context-stats {
      color: rgba(255, 255, 255, 0.8);
      font-family: 'Monaco', 'Consolas', monospace;
      
      .context-percentage {
        font-weight: 600;
        margin-left: 4px;
      }
    }
  }
  
  .context-progress {
    height: 3px;
    background: rgba(255, 255, 255, 0.1);
    border-radius: 2px;
    overflow: hidden;
    
    .context-progress-fill {
      height: 100%;
      border-radius: 2px;
      transition: width 0.3s ease, background-color 0.3s ease;
    }
  }
}

.input-container {
  max-width: 900px;
  margin: 0 auto;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  padding: 12px;
  transition: all 0.2s;

  &:focus-within {
    background: rgba(255, 255, 255, 0.05);
    border-color: rgba(102, 126, 234, 0.3);
    box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
  }
}

.image-preview-bar {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.preview-item {
  position: relative;
  width: 60px;
  height: 60px;
  border-radius: 8px;
  overflow: hidden;

  img {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }
}

.remove-image {
  position: absolute;
  top: 4px;
  right: 4px;
  width: 20px;
  height: 20px;
  border: none;
  background: rgba(0, 0, 0, 0.6);
  border-radius: 50%;
  color: white;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;

  &:hover {
    background: #ef4444;
  }
}

.input-row {
  display: flex;
  align-items: flex-end;
  gap: 8px;
}

.attach-btn {
  width: 36px;
  height: 36px;
  border: none;
  background: transparent;
  border-radius: 10px;
  color: #6b7280;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: all 0.2s;

  &:hover {
    background: rgba(255, 255, 255, 0.1);
    color: white;
  }
}

.input-wrapper {
  flex: 1;
  min-height: 36px;

  textarea {
    width: 100%;
    min-height: 36px;
    max-height: 200px;
    background: transparent;
    border: none;
    color: white;
    font-size: 15px;
    line-height: 1.5;
    resize: none;
    outline: none;

    &::placeholder {
      color: #6b7280;
    }
  }
}

.send-btn {
  width: 36px;
  height: 36px;
  border: none;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 10px;
  color: #6b7280;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: all 0.2s;

  &.active {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    cursor: pointer;

    &:hover {
      transform: scale(1.05);
      box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
    }
  }

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .spinning {
    animation: spin 1s linear infinite;
  }
}

.input-hint {
  margin-top: 8px;
  text-align: center;
  font-size: 11px;
  color: #4b5563;
}
</style>
