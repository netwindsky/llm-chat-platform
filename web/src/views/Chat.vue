<template>
  <div class="chat-container">
    <!-- 顶部导航 -->
    <header class="chat-header">
      <div class="header-brand">
        <div class="brand-icon">
          <svg viewBox="0 0 32 32" fill="none">
            <circle cx="16" cy="16" r="14" stroke="currentColor" stroke-width="2"/>
            <path d="M10 16l4 4 8-8" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </div>
        <h1>LLM Platform</h1>
      </div>
      
      <div class="header-center">
        <div class="model-indicator" v-if="selectedModel">
          <span class="indicator-dot" :class="{ active: currentModelConfig?.status === 'loaded' }"></span>
          <span class="model-name">{{ currentModelConfig?.name || '未选择模型' }}</span>
          <el-tag v-if="currentModelConfig?.status === 'loaded'" size="small" class="status-tag">Ready</el-tag>
        </div>
      </div>
      
      <div class="header-actions">
        <el-select 
          v-model="selectedModel" 
          placeholder="选择模型" 
          @change="onModelChange"
          class="model-select"
          :disabled="loading"
        >
          <template #prefix>
            <el-icon><Cpu /></el-icon>
          </template>
          <el-option
            v-for="model in availableModels"
            :key="model.id"
            :label="model.name"
            :value="model.id"
          >
            <div class="model-option">
              <span class="model-option-name">{{ model.name }}</span>
              <span class="model-option-status" :class="model.status">
                {{ model.status === 'loaded' ? '●' : '○' }}
              </span>
            </div>
          </el-option>
        </el-select>
        
        <el-button class="icon-btn" @click="$router.push('/models')">
          <el-icon><Setting /></el-icon>
        </el-button>
      </div>
    </header>

    <!-- 聊天内容区 -->
    <main class="chat-main">
      <!-- 消息列表 -->
      <div class="messages-container" ref="messagesContainer">
        <!-- 空状态 -->
        <div v-if="messages.length === 0" class="empty-state">
          <div class="empty-illustration">
            <div class="chat-bubble">
              <span class="bubble-text">?</span>
            </div>
          </div>
          <h2>开始对话</h2>
          <p>选择一个 AI 模型，开始智能对话之旅</p>
        </div>
        
        <!-- 消息列表 -->
        <div v-else class="messages-list">
          <div v-for="(msg, index) in messages" :key="index" 
               class="message" 
               :class="msg.role"
          >
            <!-- 用户消息 -->
            <template v-if="msg.role === 'user'">
              <div class="message-avatar user-avatar">
                <span>U</span>
              </div>
              <div class="message-content">
                <div class="message-bubble">
                  {{ msg.content }}
                </div>
              </div>
            </template>
            
            <!-- AI 消息 -->
            <template v-else>
              <div class="message-avatar ai-avatar">
                <span>AI</span>
              </div>
              <div class="message-content">
                <!-- 思考内容 -->
                <div v-if="msg.thinking" class="thinking-box" :class="{ 'thinking-complete': msg.isThinkingComplete }">
                  <div class="thinking-header" @click="toggleThinking(index)">
                    <span class="thinking-icon">
                      <!-- 思考中：旋转的大脑图标 -->
                      <svg v-if="!msg.isThinkingComplete" class="brain-spinner" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                        <path d="M9.5 2A2.5 2.5 0 0 1 12 4.5v15a2.5 2.5 0 0 1-4.96.44 5.5 5.5 0 0 1 4.96-8.96V6.5A2.5 2.5 0 0 0 7 4.5v-.006A2.5 2.5 0 0 1 9.5 2Z"/>
                        <path d="M14.5 22A2.5 2.5 0 0 1 12 19.5v-15a2.5 2.5 0 0 1 4.96-.44 5.5 5.5 0 0 1-4.96 8.96V17.5a2.5 2.5 0 0 0 5 0v.006A2.5 2.5 0 0 1 14.5 22Z"/>
                        <path d="M12 4.5V6"/>
                        <path d="M12 18v1.5"/>
                      </svg>
                      <!-- 思考完成：填充绿色的大脑图标 -->
                      <svg v-else class="brain-complete" viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" stroke-width="1.5">
                        <path d="M9.5 2A2.5 2.5 0 0 1 12 4.5v15a2.5 2.5 0 0 1-4.96.44 5.5 5.5 0 0 1 4.96-8.96V6.5A2.5 2.5 0 0 0 7 4.5v-.006A2.5 2.5 0 0 1 9.5 2Z"/>
                        <path d="M14.5 22A2.5 2.5 0 0 1 12 19.5v-15a2.5 2.5 0 0 1 4.96-.44 5.5 5.5 0 0 1-4.96 8.96V17.5a2.5 2.5 0 0 0 5 0v.006A2.5 2.5 0 0 1 14.5 22Z"/>
                        <path d="M12 4.5V6"/>
                        <path d="M12 18v1.5"/>
                      </svg>
                    </span>
                    <span class="thinking-title">{{ msg.isThinkingComplete ? '思考完成' : '思考中...' }}</span>
                    <span class="thinking-toggle">
                      <svg :class="{ 'is-collapsed': msg.isThinkingCollapsed }" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M6 9l6 6 6-6"/>
                      </svg>
                    </span>
                  </div>
                  <div v-show="!msg.isThinkingCollapsed" class="thinking-body">
                    <MarkdownRenderer :content="msg.thinking" :is-thinking="true" />
                  </div>
                </div>
                
                <!-- 回复内容 -->
                <div class="message-bubble" :class="{ 'has-thinking': msg.thinking }">
                  <MarkdownRenderer :content="msg.content" />
                </div>
                
                <!-- 统计信息 -->
                <div v-if="index === messages.length - 1 && stats.totalTokens > 0" 
                     class="message-meta"
                >
                  <span class="meta-item">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/>
                      <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>
                    </svg>
                    {{ stats.promptTokens }}
                  </span>
                  <span class="meta-item">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M12 6v6l4 2"/>
                      <circle cx="12" cy="12" r="10"/>
                    </svg>
                    {{ stats.completionTokens }}
                  </span>
                  <span class="meta-item">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/>
                    </svg>
                    {{ stats.speed.toFixed(1) }} t/s
                  </span>
                </div>
              </div>
            </template>
          </div>
          
          <!-- 加载状态 -->
          <div v-if="loading && (!messages.length || messages[messages.length - 1]?.role === 'user')" 
               class="message assistant loading"
          >
            <div class="message-avatar ai-avatar">
              <span>AI</span>
            </div>
            <div class="message-content">
              <div class="typing-indicator">
                <span class="typing-dot"></span>
                <span class="typing-dot"></span>
                <span class="typing-dot"></span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 输入区 -->
      <footer class="input-area">
        <div class="input-wrapper">
          <div class="input-container">
            <el-input
              v-model="inputMessage"
              type="textarea"
              :rows="1"
              placeholder="输入消息..."
              @keydown.enter.exact.prevent="sendMessage"
              :disabled="loading || !selectedModel"
              :autosize="{ minRows: 1, maxRows: 6 }"
              resize="none"
              class="message-input"
            />
            <el-button 
              class="send-btn"
              :class="{ 'send-btn-active': inputMessage.trim() && !loading }"
              :loading="loading"
              :disabled="!inputMessage.trim() || !selectedModel"
              @click="sendMessage"
            >
              <svg v-if="!loading" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z"/>
              </svg>
            </el-button>
          </div>
          
          <!-- 参数显示 -->
          <div class="params-bar" v-if="currentModelConfig">
            <div class="param-item">
              <span class="param-label">Temp</span>
              <span class="param-value">{{ currentModelConfig.default_temp }}</span>
            </div>
            <div class="param-divider"></div>
            <div class="param-item">
              <span class="param-label">Top-P</span>
              <span class="param-value">{{ currentModelConfig.default_top_p }}</span>
            </div>
            <div class="param-divider"></div>
            <div class="param-item">
              <span class="param-label">Context</span>
              <span class="param-value">{{ formatContextSize(currentModelConfig.max_context) }}</span>
            </div>
          </div>
        </div>
      </footer>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, watch } from 'vue'
import { useModelStore } from '@/stores/models'
import { useChatStore } from '@/stores/chat'
import { storeToRefs } from 'pinia'
import { ElMessage } from 'element-plus'
import { Setting, Cpu } from '@element-plus/icons-vue'
import MarkdownRenderer from '@/components/MarkdownRenderer.vue'

const modelStore = useModelStore()
const chatStore = useChatStore()

const { models, currentModel } = storeToRefs(modelStore)
const { messages, loading, stats } = storeToRefs(chatStore)

const inputMessage = ref('')
const selectedModel = ref(null)
const messagesContainer = ref(null)

const availableModels = computed(() => {
  return models.value.filter(m => m.file_exists)
})

const currentModelConfig = computed(() => {
  if (!selectedModel.value) return null
  return models.value.find(m => m.id === selectedModel.value)
})

function formatContextSize(size) {
  if (size >= 131072) return '128K'
  if (size >= 65536) return '64K'
  if (size >= 32768) return '32K'
  if (size >= 16384) return '16K'
  return size
}

function formatThinkingText(text) {
  if (!text) return ''
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/\n/g, '<br>')
}

async function onModelChange(modelId) {
  const model = models.value.find(m => m.id === modelId)
  if (!model) return
  
  selectedModel.value = modelId
  
  if (model.status !== 'loaded') {
    ElMessage.info('正在加载模型...')
    try {
      await modelStore.loadModel(modelId)
      ElMessage.success('模型已就绪')
    } catch (e) {
      ElMessage.error('加载失败: ' + e.message)
    }
  } else {
    modelStore.currentModel = modelId
  }
}

async function sendMessage() {
  if (!inputMessage.value.trim() || !selectedModel.value) return
  
  const content = inputMessage.value.trim()
  inputMessage.value = ''
  
  try {
    await chatStore.sendMessage(selectedModel.value, content, {
      temperature: currentModelConfig.value?.default_temp || 0.7,
      top_p: currentModelConfig.value?.default_top_p || 0.8
    })
    
    await nextTick()
    scrollToBottom()
    
  } catch (e) {
    ElMessage.error('发送失败: ' + e.message)
  }
}

function scrollToBottom() {
  if (messagesContainer.value) {
    messagesContainer.value.scrollTo({
      top: messagesContainer.value.scrollHeight,
      behavior: 'smooth'
    })
  }
}

function toggleThinking(index) {
  const msg = messages.value[index]
  if (msg && msg.thinking) {
    msg.isThinkingCollapsed = !msg.isThinkingCollapsed
    // 阻止事件冒泡，防止触发其他点击事件
    event?.stopPropagation()
  }
}

// 监听消息变化，但只在新增消息或内容变化时滚动，不响应折叠状态变化
watch(() => messages.value.map(m => ({ 
  role: m.role, 
  content: m.content, 
  thinking: m.thinking,
  timestamp: m.timestamp 
})), 
(newVal, oldVal) => {
  // 只在消息数量变化或最后一条消息内容变化时滚动
  if (newVal.length !== oldVal?.length || 
      JSON.stringify(newVal[newVal.length - 1]) !== JSON.stringify(oldVal?.[oldVal.length - 1])) {
    nextTick(scrollToBottom)
  }
}, { deep: true })

onMounted(async () => {
  await modelStore.fetchModels()
  await modelStore.fetchTypes()
  
  const loadedModel = models.value.find(m => m.status === 'loaded')
  if (loadedModel) {
    selectedModel.value = loadedModel.id
    modelStore.currentModel = loadedModel.id
  }
})
</script>

<style lang="scss" scoped>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@300;400;500;600&family=Space+Grotesk:wght@400;500;600&display=swap');

$bg-primary: #0a0a0b;
$bg-secondary: #141416;
$bg-tertiary: #1c1c1f;
$bg-elevated: #232328;
$accent-primary: #6366f1;
$accent-secondary: #818cf8;
$accent-glow: rgba(99, 102, 241, 0.3);
$text-primary: #fafafa;
$text-secondary: #a1a1aa;
$text-tertiary: #71717a;
$border-subtle: rgba(255, 255, 255, 0.06);
$border-active: rgba(255, 255, 255, 0.12);
$success: #22c55e;
$user-bubble: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
$ai-bubble: linear-gradient(135deg, #27272a 0%, #18181b 100%);

.chat-container {
  --bg-primary: #{$bg-primary};
  --bg-secondary: #{$bg-secondary};
  --bg-tertiary: #{$bg-tertiary};
  --bg-elevated: #{$bg-elevated};
  --accent-primary: #{$accent-primary};
  --accent-secondary: #{$accent-secondary};
  --text-primary: #{$text-primary};
  --text-secondary: #{$text-secondary};
  --text-tertiary: #{$text-tertiary};
  
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: var(--bg-primary);
  font-family: 'Noto Sans SC', 'Space Grotesk', -apple-system, sans-serif;
  color: var(--text-primary);
}

.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  background: var(--bg-secondary);
  border-bottom: 1px solid $border-subtle;
  backdrop-filter: blur(12px);
  position: relative;
  z-index: 100;
  
  &::after {
    content: '';
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    height: 1px;
    background: linear-gradient(90deg, transparent, var(--accent-primary), transparent);
    opacity: 0.5;
  }
}

.header-brand {
  display: flex;
  align-items: center;
  gap: 12px;
  
  .brand-icon {
    width: 36px;
    height: 36px;
    color: var(--accent-primary);
    
    svg {
      width: 100%;
      height: 100%;
    }
  }
  
  h1 {
    margin: 0;
    font-size: 18px;
    font-weight: 600;
    letter-spacing: -0.02em;
    background: linear-gradient(135deg, var(--text-primary) 0%, var(--text-secondary) 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }
}

.header-center {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
}

.model-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: var(--bg-tertiary);
  border-radius: 20px;
  border: 1px solid $border-subtle;
  
  .indicator-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--text-tertiary);
    transition: all 0.3s ease;
    
    &.active {
      background: $success;
      box-shadow: 0 0 8px rgba(34, 197, 94, 0.5);
    }
  }
  
  .model-name {
    font-size: 13px;
    font-weight: 500;
    color: var(--text-primary);
  }
  
  .status-tag {
    background: rgba(34, 197, 94, 0.15);
    color: $success;
    border: none;
    font-size: 10px;
    padding: 2px 8px;
  }
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.model-select {
  width: 220px;
  
  :deep(.el-select__wrapper) {
    background: var(--bg-tertiary);
    border: 1px solid $border-subtle;
    box-shadow: none;
    border-radius: 10px;
    padding: 4px 12px;
    
    &:hover {
      border-color: $border-active;
    }
    
    &.is-focused {
      border-color: var(--accent-primary);
      box-shadow: 0 0 0 3px $accent-glow;
    }
  }
  
  :deep(.el-select__selected-item) {
    color: var(--text-primary);
  }
}

.model-option {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  
  .model-option-name {
    font-size: 13px;
  }
  
  .model-option-status {
    font-size: 10px;
    color: var(--text-tertiary);
    
    &.loaded {
      color: $success;
    }
  }
}

.icon-btn {
  background: var(--bg-tertiary);
  border: 1px solid $border-subtle;
  color: var(--text-secondary);
  width: 40px;
  height: 40px;
  border-radius: 10px;
  transition: all 0.2s ease;
  
  &:hover {
    background: var(--bg-elevated);
    color: var(--text-primary);
    border-color: $border-active;
  }
}

.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  scroll-behavior: smooth;
  
  &::-webkit-scrollbar {
    width: 6px;
  }
  
  &::-webkit-scrollbar-track {
    background: transparent;
  }
  
  &::-webkit-scrollbar-thumb {
    background: var(--bg-elevated);
    border-radius: 3px;
  }
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  text-align: center;
  
  .empty-illustration {
    margin-bottom: 32px;
    
    .chat-bubble {
      width: 80px;
      height: 80px;
      background: var(--bg-tertiary);
      border-radius: 24px;
      display: flex;
      align-items: center;
      justify-content: center;
      border: 1px solid $border-subtle;
      animation: float 3s ease-in-out infinite;
      
      .bubble-text {
        font-size: 32px;
        font-weight: 300;
        color: var(--text-tertiary);
      }
    }
  }
  
  h2 {
    margin: 0 0 8px;
    font-size: 24px;
    font-weight: 500;
    letter-spacing: -0.02em;
  }
  
  p {
    margin: 0;
    font-size: 14px;
    color: var(--text-tertiary);
  }
}

@keyframes float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-10px); }
}

.messages-list {
  max-width: 800px;
  margin: 0 auto;
}

.message {
  display: flex;
  gap: 16px;
  margin-bottom: 24px;
  animation: fadeInUp 0.3s ease;
  
  &.user {
    flex-direction: row-reverse;
    
    .message-avatar {
      background: $user-bubble;
    }
    
    .message-bubble {
      background: $user-bubble;
      color: #fff;
      border-top-left-radius: 18px;
      border-top-right-radius: 4px;
    }
  }
}

@keyframes fadeInUp {
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
  width: 40px;
  height: 40px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 600;
  letter-spacing: -0.02em;
  
  &.user-avatar {
    background: $user-bubble;
    color: #fff;
  }
  
  &.ai-avatar {
    background: $ai-bubble;
    border: 1px solid $border-subtle;
    color: var(--accent-secondary);
  }
}

.message-content {
  flex: 1;
  min-width: 0;
  max-width: calc(100% - 56px);
}

.message-bubble {
  padding: 14px 18px;
  background: $ai-bubble;
  border-radius: 18px;
  border-top-left-radius: 4px;
  line-height: 1.6;
  font-size: 14px;
  border: 1px solid $border-subtle;
  word-break: break-word;
  
  &.has-thinking {
    border-top-left-radius: 18px;
  }
}

.thinking-box {
  background: var(--bg-tertiary);
  border-radius: 14px;
  border: 1px solid $border-subtle;
  margin-bottom: 8px;
  overflow: hidden;
  transition: all 0.3s ease;
  
  &.thinking-complete {
    border-color: rgba(34, 197, 94, 0.3);
    
    .thinking-header {
      background: rgba(34, 197, 94, 0.1);
    }
  }
  
  .thinking-header {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 10px 14px;
    background: var(--bg-elevated);
    border-bottom: 1px solid $border-subtle;
    font-size: 12px;
    color: var(--text-tertiary);
    cursor: pointer;
    user-select: none;
    transition: all 0.2s ease;
    
    &:hover {
      background: var(--bg-hover);
    }
    
    .thinking-icon {
      width: 18px;
      height: 18px;
      display: flex;
      align-items: center;
      justify-content: center;
      
      .brain-spinner {
        animation: brain-pulse 1.5s ease-in-out infinite;
        color: var(--text-tertiary);
      }
      
      .brain-complete {
        color: #22c55e;
        animation: brain-complete 0.5s ease-out;
      }
    }
    
    .thinking-title {
      flex: 1;
      font-weight: 500;
    }
    
    .thinking-toggle {
      width: 16px;
      height: 16px;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: transform 0.3s ease;
      
      svg {
        width: 14px;
        height: 14px;
        transition: transform 0.3s ease;
        
        &.is-collapsed {
          transform: rotate(-90deg);
        }
      }
    }
  }
  
  .thinking-body {
    padding: 8px 14px !important;
    font-size: 12px !important;
    line-height: 1.6 !important;
    max-height: 400px;
    overflow-y: auto;
    animation: slide-down 0.3s ease;
    background: linear-gradient(135deg, rgba(99, 102, 241, 0.03) 0%, rgba(139, 92, 246, 0.03) 100%);
    
    :deep(.markdown-body) {
      font-size: 11px !important;
      line-height: 1.6 !important;
      color: var(--text-secondary) !important;
      padding: 0 !important;
      font-style: italic !important;
      
      * {
        font-size: inherit !important;
        line-height: inherit !important;
        font-style: inherit !important;
      }
      
      p {
        margin: 4px 0 !important;
      }
      
      ul, ol {
        margin: 4px 0 !important;
        padding-left: 12px !important;
      }
      
      li {
        margin: 2px 0 !important;
      }
      
      code {
        font-size: 7px !important;
      }
    }
  }
}

@keyframes brain-pulse {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.7;
    transform: scale(0.95);
  }
}

@keyframes brain-complete {
  0% {
    transform: scale(0.5);
    opacity: 0;
  }
  50% {
    transform: scale(1.2);
  }
  100% {
    transform: scale(1);
    opacity: 1;
  }
}

@keyframes slide-down {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.message-meta {
  display: flex;
  gap: 16px;
  margin-top: 8px;
  padding-left: 4px;
  
  .meta-item {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 11px;
    color: var(--text-tertiary);
    
    svg {
      width: 12px;
      height: 12px;
    }
  }
}

.typing-indicator {
  display: flex;
  gap: 4px;
  padding: 14px 18px;
  background: var(--bg-tertiary);
  border-radius: 18px;
  border: 1px solid $border-subtle;
  
  .typing-dot {
    width: 8px;
    height: 8px;
    background: var(--text-tertiary);
    border-radius: 50%;
    animation: typing 1.4s infinite ease-in-out;
    
    &:nth-child(1) { animation-delay: 0s; }
    &:nth-child(2) { animation-delay: 0.2s; }
    &:nth-child(3) { animation-delay: 0.4s; }
  }
}

@keyframes typing {
  0%, 60%, 100% { transform: translateY(0); opacity: 0.4; }
  30% { transform: translateY(-4px); opacity: 1; }
}

.input-area {
  padding: 16px 24px 24px;
  background: var(--bg-secondary);
  border-top: 1px solid $border-subtle;
}

.input-wrapper {
  max-width: 800px;
  margin: 0 auto;
}

.input-container {
  display: flex;
  align-items: flex-end;
  gap: 12px;
  background: var(--bg-tertiary);
  border: 1px solid $border-subtle;
  border-radius: 16px;
  padding: 8px 8px 8px 16px;
  transition: all 0.2s ease;
  
  &:focus-within {
    border-color: var(--accent-primary);
    box-shadow: 0 0 0 3px $accent-glow;
  }
}

.message-input {
  flex: 1;
  
  :deep(.el-textarea__inner) {
    background: transparent;
    border: none;
    color: var(--text-primary);
    font-size: 14px;
    line-height: 20px;
    resize: none;
    box-shadow: none;
    padding: 12px 16px;
    min-height: 44px;
    max-height: 44px;
    overflow-y: hidden;
    
    &::placeholder {
      color: var(--text-tertiary);
    }
    
    &:focus {
      box-shadow: none;
    }
  }
}

.send-btn {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  background: var(--bg-elevated);
  border: 1px solid $border-subtle;
  color: var(--text-tertiary);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
  
  svg {
    width: 18px;
    height: 18px;
  }
  
  &:hover:not(:disabled) {
    background: var(--accent-primary);
    border-color: var(--accent-primary);
    color: #fff;
    transform: scale(1.05);
  }
  
  &-active {
    background: var(--accent-primary);
    border-color: var(--accent-primary);
    color: #fff;
    box-shadow: 0 4px 12px $accent-glow;
  }
  
  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
}

.params-bar {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  margin-top: 12px;
  
  .param-item {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 12px;
    
    .param-label {
      color: var(--text-tertiary);
    }
    
    .param-value {
      color: var(--text-secondary);
      font-weight: 500;
    }
  }
  
  .param-divider {
    width: 1px;
    height: 12px;
    background: $border-subtle;
  }

  
}
</style>
