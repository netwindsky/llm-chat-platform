<template>
  <div class="settings-page">
    <!-- 顶部栏 -->
    <header class="settings-header">
      <div class="header-left">
        <button class="back-btn" @click="$router.push('/')">
          <el-icon><ArrowLeft /></el-icon>
          <span>返回</span>
        </button>
        <h1 class="page-title">
          <el-icon><Setting /></el-icon>
          设置
        </h1>
      </div>
    </header>

    <!-- 主内容区 -->
    <div class="settings-layout">
      <!-- 左侧导航 -->
      <nav class="settings-nav">
        <div
          v-for="item in navItems"
          :key="item.id"
          :class="['nav-item', { active: currentTab === item.id }]"
          @click="currentTab = item.id"
        >
          <el-icon>
            <component :is="item.icon" />
          </el-icon>
          <span>{{ item.label }}</span>
        </div>
      </nav>

      <!-- 右侧内容 -->
      <main class="settings-content">
        <!-- 常规设置 -->
        <section v-show="currentTab === 'general'" class="settings-section">
          <div class="section-header">
            <el-icon><Setting /></el-icon>
            <h2>常规</h2>
          </div>

          <div class="setting-group">
            <div class="setting-item">
              <div class="setting-header">
                <label>主题</label>
                <span class="setting-value">{{ themeLabel }}</span>
              </div>
              <p class="setting-desc">选择界面颜色主题，可跟随系统设置或手动选择浅色/深色模式</p>
              <div class="theme-selector">
                <button
                  v-for="t in themeOptions"
                  :key="t.value"
                  :class="['theme-card', { active: settings.theme === t.value }]"
                  @click="settings.theme = t.value"
                >
                  <div class="theme-preview" :class="t.value">
                    <div class="preview-header" />
                    <div class="preview-body">
                      <div class="preview-line" />
                      <div class="preview-line short" />
                    </div>
                  </div>
                  <span class="theme-name">{{ t.label }}</span>
                  <div v-if="settings.theme === t.value" class="check-icon">
                    <el-icon><Check /></el-icon>
                  </div>
                </button>
              </div>
            </div>

            <div class="setting-item">
              <div class="setting-header">
                <label>系统提示词</label>
              </div>
              <p class="setting-desc">定义模型行为的起始消息，会影响模型的回复风格</p>
              <textarea
                v-model="settings.systemMessage"
                class="setting-textarea"
                rows="4"
                placeholder="你是一个有帮助的 AI 助手..."
              />
              <label class="checkbox-label">
                <input v-model="settings.showSystemMessage" type="checkbox">
                <span>在对话中显示系统提示词</span>
              </label>
            </div>

            <div class="setting-item">
              <div class="setting-header">
                <label>长文本粘贴阈值</label>
                <span class="setting-value">{{ settings.pasteThreshold }} 字符</span>
              </div>
              <p class="setting-desc">超过此长度的粘贴文本将自动转换为文件上传</p>
              <input
                v-model.number="settings.pasteThreshold"
                type="range"
                min="1000"
                max="10000"
                step="500"
                class="custom-slider"
              >
            </div>
          </div>
        </section>

        <!-- 模型列表 -->
        <section v-show="currentTab === 'models'" class="settings-section">
          <div class="section-header">
            <el-icon><Cpu /></el-icon>
            <h2>模型管理</h2>
            <button class="refresh-btn" :disabled="modelLoading" @click="refreshModels">
              <el-icon><Refresh /></el-icon>
              刷新
            </button>
          </div>

          <!-- 模型类型筛选 -->
          <div class="model-filter">
            <button
              class="filter-btn"
              :class="{ active: selectedType === '' }"
              @click="selectedType = ''"
            >
              <el-icon class="filter-icon"><Grid /></el-icon>
              全部
            </button>
            <button
              v-for="type in modelTypes"
              :key="type.id"
              class="filter-btn"
              :class="{ active: selectedType === type.id }"
              :style="selectedType === type.id ? { borderColor: type.color, color: type.color, background: type.color + '15' } : {}"
              @click="selectedType = type.id"
            >
              <el-icon class="filter-icon">
                <component :is="getTypeIcon(type.id)" />
              </el-icon>
              {{ type.description }}
              <span class="filter-count">({{ type.count }})</span>
            </button>
          </div>

          <!-- 模型列表 -->
          <div class="models-grid">
            <div
              v-for="model in filteredModels"
              :key="model.id"
              class="model-card"
              :class="{ 'is-loaded': model.status === 'loaded' }"
            >
              <div class="model-header">
                <div
                class="model-icon"
                :style="{ background: getTypeGradient(model.type) }"
              >
                <el-icon :size="20" color="white">
                  <component :is="getTypeIcon(model.type)" />
                </el-icon>
              </div>
                <div class="model-info">
                  <h3>{{ model.name }}</h3>
                  <div class="model-status">
                    <span
                      class="status-badge"
                      :class="model.file_exists ? 'exists' : 'missing'"
                    >
                      {{ model.file_exists ? '文件存在' : '文件缺失' }}
                    </span>
                    <span
                      v-if="model.status === 'loaded'"
                      class="status-badge loaded"
                    >
                      已加载
                    </span>
                  </div>
                </div>
              </div>

              <div class="model-details">
                <div class="detail-item">
                  <span class="label">类型</span>
                  <span class="value">{{ model.type }}</span>
                </div>
                <div class="detail-item">
                  <span class="label">大小</span>
                  <span class="value">{{ model.size }}</span>
                </div>
                <div class="detail-item">
                  <span class="label">量化</span>
                  <span class="value">{{ model.quantization }}</span>
                </div>
                <div class="detail-item">
                  <span class="label">上下文</span>
                  <span class="value">{{ formatContext(model.max_context) }}</span>
                </div>
                <div class="detail-item">
                  <span class="label">后端</span>
                  <span class="value">{{ model.backend }}</span>
                </div>
              </div>

              <div class="model-tags">
                <span v-for="tag in model.tags" :key="tag" class="tag">
                  {{ tag }}
                </span>
              </div>

              <p class="model-desc">{{ model.description }}</p>

              <div class="model-actions">
                <button
                  v-if="model.status !== 'loaded'"
                  class="action-btn primary"
                  :disabled="!model.file_exists || loadingModel === model.id"
                  @click="loadModel(model)"
                >
                  <span v-if="loadingModel === model.id">加载中...</span>
                  <span v-else>加载模型</span>
                </button>
                <button
                  v-else
                  class="action-btn danger"
                  @click="unloadModel(model)"
                >
                  卸载模型
                </button>
              </div>
            </div>
          </div>
        </section>

        <!-- 显示设置 -->
        <section v-show="currentTab === 'display'" class="settings-section">
          <div class="section-header">
            <el-icon><Monitor /></el-icon>
            <h2>显示</h2>
          </div>

          <div class="setting-group">
            <label class="setting-checkbox">
              <input v-model="settings.showGenerationStats" type="checkbox">
              <div class="checkbox-content">
                <span class="checkbox-title">显示生成统计</span>
                <span class="checkbox-desc">在每条助手消息下方显示 token/秒、token 数量、生成时长等统计信息</span>
              </div>
            </label>

            <label class="setting-checkbox">
              <input v-model="settings.showThinking" type="checkbox">
              <div class="checkbox-content">
                <span class="checkbox-title">显示思考过程</span>
                <span class="checkbox-desc">生成消息时默认展开思考过程（如果模型支持）</span>
              </div>
            </label>

            <label class="setting-checkbox">
              <input v-model="settings.keepStatsVisible" type="checkbox">
              <div class="checkbox-content">
                <span class="checkbox-title">保持统计显示</span>
                <span class="checkbox-desc">生成完成后继续显示处理统计信息</span>
              </div>
            </label>

            <label class="setting-checkbox">
              <input v-model="settings.renderMarkdown" type="checkbox">
              <div class="checkbox-content">
                <span class="checkbox-title">渲染 Markdown</span>
                <span class="checkbox-desc">使用 Markdown 格式渲染用户消息</span>
              </div>
            </label>

            <label class="setting-checkbox">
              <input v-model="settings.fullHeightCode" type="checkbox">
              <div class="checkbox-content">
                <span class="checkbox-title">代码块完整高度</span>
                <span class="checkbox-desc">代码块显示完整内容，不限制高度</span>
              </div>
            </label>

            <label class="setting-checkbox">
              <input v-model="settings.disableAutoScroll" type="checkbox">
              <div class="checkbox-content">
                <span class="checkbox-title">禁用自动滚动</span>
                <span class="checkbox-desc">消息流式输出时不自动滚动，可手动控制视口位置</span>
              </div>
            </label>

            <label class="setting-checkbox">
              <input v-model="settings.alwaysShowSidebar" type="checkbox">
              <div class="checkbox-content">
                <span class="checkbox-title">始终显示侧边栏</span>
                <span class="checkbox-desc">桌面端始终显示侧边栏，不自动隐藏</span>
              </div>
            </label>
          </div>

          <div class="setting-group">
            <div class="setting-item">
              <div class="setting-header">
                <label>Markdown 主题</label>
              </div>
              <div class="markdown-theme-grid">
                <div
                  v-for="theme in markdownThemes"
                  :key="theme.id"
                  :class="['markdown-theme-item', { active: settings.markdownTheme === theme.id }]"
                  @click="settings.markdownTheme = theme.id"
                >
                  <div class="theme-preview-mini" :style="{ background: theme.preview }">
                    <span :style="{ color: theme.strong }">A</span>
                    <span :style="{ color: theme.em }">a</span>
                  </div>
                  <span class="theme-name">{{ theme.name }}</span>
                </div>
              </div>
            </div>
          </div>
        </section>

        <!-- 采样设置 -->
        <section v-show="currentTab === 'sampling'" class="settings-section">
          <div class="section-header">
            <el-icon><Collection /></el-icon>
            <h2>采样参数</h2>
          </div>

          <div class="setting-group">
            <div class="setting-item">
              <div class="setting-header">
                <label>Temperature</label>
                <span class="setting-value">{{ settings.temperature }}</span>
              </div>
              <p class="setting-desc">控制生成文本的随机性。值越高输出越随机，值越低输出越聚焦</p>
              <div class="slider-with-labels">
                <span>精确</span>
                <input
                  v-model.number="settings.temperature"
                  type="range"
                  min="0"
                  max="2"
                  step="0.1"
                  class="custom-slider"
                >
                <span>创意</span>
              </div>
            </div>

            <div class="setting-item">
              <div class="setting-header">
                <label>Top P</label>
                <span class="setting-value">{{ settings.topP }}</span>
              </div>
              <p class="setting-desc">核采样概率阈值，控制采样时的概率质量</p>
              <input
                v-model.number="settings.topP"
                type="range"
                min="0"
                max="1"
                step="0.05"
                class="custom-slider"
              >
            </div>

            <div class="setting-item">
              <div class="setting-header">
                <label>Top K</label>
                <span class="setting-value">{{ settings.topK }}</span>
              </div>
              <p class="setting-desc">只保留概率最高的 K 个 token 进行采样</p>
              <input
                v-model.number="settings.topK"
                type="range"
                min="1"
                max="100"
                step="1"
                class="custom-slider"
              >
              <div class="range-marks">
                <span>1</span>
                <span>25</span>
                <span>50</span>
                <span>75</span>
                <span>100</span>
              </div>
            </div>

            <div class="setting-item">
              <div class="setting-header">
                <label>最大生成长度</label>
                <span class="setting-value">{{ settings.maxTokens }} tokens</span>
              </div>
              <p class="setting-desc">限制模型生成的最大 token 数量</p>
              <input
                v-model.number="settings.maxTokens"
                type="range"
                min="256"
                max="8192"
                step="256"
                class="custom-slider"
              >
              <div class="range-marks">
                <span>256</span>
                <span>2K</span>
                <span>4K</span>
                <span>8K</span>
              </div>
            </div>

            <div class="setting-item">
              <div class="setting-header">
                <label>上下文大小</label>
                <span class="setting-value">{{ formatContextSize }}</span>
              </div>
              <p class="setting-desc">模型处理的最大上下文长度</p>
              <div class="context-options">
                <button
                  v-for="size in contextSizes"
                  :key="size.value"
                  :class="['context-btn', { active: settings.contextSize === size.value }]"
                  @click="settings.contextSize = size.value"
                >
                  {{ size.label }}
                </button>
              </div>
            </div>

            <div class="setting-item">
              <div class="setting-header">
                <label>GPU 层数</label>
                <span class="setting-value">{{ settings.gpuLayers }} 层</span>
              </div>
              <p class="setting-desc">加载到 GPU 的模型层数，更多层数 = 更快推理但需要更多显存</p>
              <input
                v-model.number="settings.gpuLayers"
                type="range"
                min="0"
                max="99"
                step="1"
                class="custom-slider"
              >
            </div>
          </div>
        </section>

        <!-- 惩罚设置 -->
        <section v-show="currentTab === 'penalties'" class="settings-section">
          <div class="section-header">
            <el-icon><Warning /></el-icon>
            <h2>惩罚设置</h2>
          </div>

          <div class="setting-group">
            <div class="setting-item">
              <div class="setting-header">
                <label>重复惩罚</label>
                <span class="setting-value">{{ settings.repeatPenalty }}</span>
              </div>
              <p class="setting-desc">降低重复 token 的概率</p>
              <input
                v-model.number="settings.repeatPenalty"
                type="range"
                min="1"
                max="2"
                step="0.05"
                class="custom-slider"
              >
            </div>

            <div class="setting-item">
              <div class="setting-header">
                <label>频率惩罚</label>
                <span class="setting-value">{{ settings.frequencyPenalty }}</span>
              </div>
              <p class="setting-desc">根据 token 出现频率进行惩罚</p>
              <input
                v-model.number="settings.frequencyPenalty"
                type="range"
                min="-2"
                max="2"
                step="0.1"
                class="custom-slider"
              >
            </div>

            <div class="setting-item">
              <div class="setting-header">
                <label>存在惩罚</label>
                <span class="setting-value">{{ settings.presencePenalty }}</span>
              </div>
              <p class="setting-desc">根据 token 是否存在进行惩罚</p>
              <input
                v-model.number="settings.presencePenalty"
                type="range"
                min="-2"
                max="2"
                step="0.1"
                class="custom-slider"
              >
            </div>
          </div>
        </section>

        <!-- 导入/导出 -->
        <section v-show="currentTab === 'import-export'" class="settings-section">
          <div class="section-header">
            <el-icon><Document /></el-icon>
            <h2>导入/导出</h2>
          </div>

          <div class="setting-group">
            <div class="export-section">
              <h3>导出设置</h3>
              <p class="section-desc">将所有设置导出为 JSON 文件，方便备份或迁移</p>
              <button class="action-btn primary" @click="exportSettings">
                <el-icon><Download /></el-icon>
                导出设置
              </button>
            </div>

            <div class="import-section">
              <h3>导入设置</h3>
              <p class="section-desc">从 JSON 文件导入设置</p>
              <div class="file-input-wrapper">
                <input
                  ref="fileInput"
                  type="file"
                  accept=".json"
                  style="display: none"
                  @change="handleFileImport"
                >
                <button class="action-btn secondary" @click="triggerFileInput">
                  <el-icon><Upload /></el-icon>
                  选择文件
                </button>
              </div>
            </div>

            <div class="danger-zone">
              <h3>危险区域</h3>
              <p class="section-desc">以下操作不可撤销，请谨慎操作</p>
              <button class="action-btn danger" @click="resetAllSettings">
                <el-icon><Delete /></el-icon>
                恢复默认设置
              </button>
            </div>
          </div>
        </section>

        <!-- 开发者选项 -->
        <section v-show="currentTab === 'developer'" class="settings-section">
          <div class="section-header">
            <el-icon><Code /></el-icon>
            <h2>开发者</h2>
          </div>

          <div class="setting-group">
            <label class="setting-checkbox">
              <input v-model="settings.disableReasoningParsing" type="checkbox">
              <div class="checkbox-content">
                <span class="checkbox-title">禁用推理内容解析</span>
                <span class="checkbox-desc">发送 reasoning_format=none 以防止服务器端将推理 token 提取到单独字段</span>
              </div>
            </label>

            <label class="setting-checkbox">
              <input v-model="settings.enableRawOutput" type="checkbox">
              <div class="checkbox-content">
                <span class="checkbox-title">启用原始输出切换</span>
                <span class="checkbox-desc">显示切换按钮以纯文本形式显示消息，而不是 Markdown 格式</span>
              </div>
            </label>

            <div class="setting-item">
              <div class="setting-header">
                <label>自定义 JSON 参数</label>
              </div>
              <p class="setting-desc">发送到 API 的自定义 JSON 参数，必须是有效的 JSON 格式</p>
              <textarea
                v-model="settings.customJson"
                class="setting-textarea code"
                rows="6"
                placeholder='{ "key": "value" }'
              />
              <p v-if="jsonError" class="error-text">{{ jsonError }}</p>
            </div>

            <div class="info-box">
              <el-icon><InfoFilled /></el-icon>
              <span>设置保存在浏览器的 localStorage 中</span>
            </div>
          </div>
        </section>

        <!-- 关于 -->
        <section v-show="currentTab === 'about'" class="settings-section">
          <div class="section-header">
            <el-icon><InfoFilled /></el-icon>
            <h2>关于</h2>
          </div>

          <div class="about-content">
            <div class="logo-section">
              <div class="app-logo">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
                </svg>
              </div>
              <h3 class="app-name">NeuralChat</h3>
              <p class="app-version">版本 1.0.0</p>
            </div>

            <div class="info-list">
              <div class="info-item">
                <span class="info-label">后端框架</span>
                <span class="info-value">llama.cpp</span>
              </div>
              <div class="info-item">
                <span class="info-label">API 兼容</span>
                <span class="info-value">OpenAI Compatible</span>
              </div>
              <div class="info-item">
                <span class="info-label">前端框架</span>
                <span class="info-value">Vue 3 + Element Plus</span>
              </div>
            </div>
          </div>
        </section>

        <!-- 底部保存栏 -->
        <div class="settings-footer">
          <button class="btn-secondary" @click="resetCurrentTab">
            <el-icon><RefreshLeft /></el-icon>
            重置当前页
          </button>
          <button class="btn-primary" @click="saveSettings">
            <el-icon><Check /></el-icon>
            保存设置
          </button>
        </div>
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useModelStore } from '@/stores/models'
import { storeToRefs } from 'pinia'
import { ElMessage } from 'element-plus'
import {
  Setting, Monitor, Collection, Warning, Document,
  EditPen, InfoFilled, ArrowLeft, Check, Download, Upload,
  Delete, RefreshLeft, Cpu, Refresh, ChatLineRound, View, DataLine, Box, Grid
} from '@element-plus/icons-vue'

// 模型 store
const modelStore = useModelStore()
const { models, modelTypes, loading: modelLoading } = storeToRefs(modelStore)

// 导航项
const navItems = [
  { id: 'general', label: '常规', icon: 'Setting' },
  { id: 'models', label: '模型', icon: 'Cpu' },
  { id: 'display', label: '显示', icon: 'Monitor' },
  { id: 'sampling', label: '采样', icon: 'Collection' },
  { id: 'penalties', label: '惩罚', icon: 'Warning' },
  { id: 'import-export', label: '导入/导出', icon: 'Document' },
  { id: 'developer', label: '开发者', icon: 'EditPen' },
  { id: 'about', label: '关于', icon: 'InfoFilled' }
]

const currentTab = ref('general')
const fileInput = ref(null)
const jsonError = ref('')

// 主题选项
const themeOptions = [
  { value: 'system', label: '跟随系统' },
  { value: 'light', label: '浅色' },
  { value: 'dark', label: '深色' }
]

// Markdown 主题
const markdownThemes = [
  { id: 'default', name: '默认', preview: '#f5f5f5', strong: '#333', em: '#666' },
  { id: 'github', name: 'GitHub', preview: '#ffffff', strong: '#24292e', em: '#586069' },
  { id: 'dark', name: '深色', preview: '#1a1a2e', strong: '#e4e4e7', em: '#a1a1aa' },
  { id: 'solarized', name: 'Solarized', preview: '#fdf6e3', strong: '#073642', em: '#586e75' },
  { id: 'dracula', name: 'Dracula', preview: '#282a36', strong: '#f8f8f2', em: '#6272a4' }
]

// 上下文大小选项
const contextSizes = [
  { label: '8K', value: 8192 },
  { label: '16K', value: 16384 },
  { label: '32K', value: 32768 },
  { label: '64K', value: 65536 },
  { label: '128K', value: 131072 }
]

// 设置数据
const settings = ref({
  // 常规
  theme: 'system',
  systemMessage: '',
  showSystemMessage: false,
  pasteThreshold: 3000,

  // 显示
  showGenerationStats: true,
  showThinking: false,
  keepStatsVisible: false,
  renderMarkdown: true,
  fullHeightCode: false,
  disableAutoScroll: false,
  alwaysShowSidebar: false,
  markdownTheme: 'default',

  // 采样
  temperature: 0.7,
  topP: 0.9,
  topK: 40,
  maxTokens: 4096,
  contextSize: 32768,
  gpuLayers: 99,

  // 惩罚
  repeatPenalty: 1.1,
  frequencyPenalty: 0,
  presencePenalty: 0,

  // 开发者
  disableReasoningParsing: false,
  enableRawOutput: false,
  customJson: ''
})

// 模型相关
const selectedType = ref('')
const loadingModel = ref(null)

// 筛选后的模型
const filteredModels = computed(() => {
  if (!selectedType.value) return models.value
  return models.value.filter(m => m.type === selectedType.value)
})

// 类型图标映射（使用 Element Plus 简化图标）
const typeIconMap = {
  'language-model': 'ChatLineRound',
  'vision-language-model': 'View',
  'code-model': 'EditPen',
  'reasoning-model': 'Cpu',
  'embedding-model': 'DataLine'
}

// 获取类型图标组件名
function getTypeIcon(type) {
  return typeIconMap[type] || 'Box'
}

// 类型渐变色映射
const typeGradientMap = {
  'language-model': 'linear-gradient(135deg, #667eea, #764ba2)',
  'vision-language-model': 'linear-gradient(135deg, #f093fb, #f5576c)',
  'code-model': 'linear-gradient(135deg, #4facfe, #00f2fe)',
  'reasoning-model': 'linear-gradient(135deg, #43e97b, #38f9d7)',
  'embedding-model': 'linear-gradient(135deg, #fa709a, #fee140)'
}

// 获取类型渐变色
function getTypeGradient(type) {
  return typeGradientMap[type] || 'linear-gradient(135deg, #667eea, #764ba2)'
}

// 获取类型颜色
function getTypeColor(type) {
  const typeInfo = modelTypes.value.find(t => t.id === type)
  return typeInfo?.color || '#666'
}

// 格式化上下文
function formatContext(size) {
  if (size >= 131072) return '128K'
  if (size >= 65536) return '64K'
  if (size >= 32768) return '32K'
  return size
}

// 刷新模型列表
async function refreshModels() {
  await modelStore.fetchModels()
  await modelStore.fetchTypes()
  ElMessage.success('模型列表已刷新')
}

// 加载模型
async function loadModel(model) {
  loadingModel.value = model.id
  try {
    await modelStore.loadModel(model.id)
    ElMessage.success(`${model.name} 加载成功`)
  } catch (e) {
    ElMessage.error(`加载失败: ${e.message}`)
  } finally {
    loadingModel.value = null
  }
}

// 卸载模型
async function unloadModel(model) {
  loadingModel.value = model.id
  try {
    await modelStore.unloadModel(model.id)
    ElMessage.success(`${model.name} 已卸载`)
  } catch (e) {
    ElMessage.error(`卸载失败: ${e.message}`)
  } finally {
    loadingModel.value = null
  }
}

// 计算属性
const themeLabel = computed(() => {
  const t = themeOptions.find(item => item.value === settings.value.theme)
  return t ? t.label : '跟随系统'
})

const formatContextSize = computed(() => {
  const size = settings.value.contextSize
  if (size >= 1024) {
    return `${(size / 1024).toFixed(0)}K`
  }
  return size.toString()
})

// 验证 JSON
watch(() => settings.value.customJson, (val) => {
  if (!val) {
    jsonError.value = ''
    return
  }
  try {
    JSON.parse(val)
    jsonError.value = ''
  } catch (e) {
    jsonError.value = '无效的 JSON 格式'
  }
})

// 方法
const saveSettings = () => {
  localStorage.setItem('neuralchat-settings', JSON.stringify(settings.value))
  // 应用主题
  applyTheme()
  alert('设置已保存')
}

const applyTheme = () => {
  const theme = settings.value.theme
  if (theme === 'dark') {
    document.documentElement.classList.add('dark-theme')
    document.documentElement.classList.remove('light-theme')
  } else if (theme === 'light') {
    document.documentElement.classList.add('light-theme')
    document.documentElement.classList.remove('dark-theme')
  } else {
    // 跟随系统
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
    if (prefersDark) {
      document.documentElement.classList.add('dark-theme')
      document.documentElement.classList.remove('light-theme')
    } else {
      document.documentElement.classList.add('light-theme')
      document.documentElement.classList.remove('dark-theme')
    }
  }
}

const resetCurrentTab = () => {
  if (confirm('确定要重置当前页面的设置吗？')) {
    // 根据当前 tab 重置对应设置
    const defaults = {
      general: { theme: 'system', systemMessage: '', showSystemMessage: false, pasteThreshold: 3000 },
      display: { showGenerationStats: true, showThinking: false, keepStatsVisible: false, renderMarkdown: true, fullHeightCode: false, disableAutoScroll: false, alwaysShowSidebar: false, markdownTheme: 'default' },
      sampling: { temperature: 0.7, topP: 0.9, topK: 40, maxTokens: 4096, contextSize: 32768, gpuLayers: 99 },
      penalties: { repeatPenalty: 1.1, frequencyPenalty: 0, presencePenalty: 0 },
      developer: { disableReasoningParsing: false, enableRawOutput: false, customJson: '' }
    }

    if (defaults[currentTab.value]) {
      Object.assign(settings.value, defaults[currentTab.value])
    }
  }
}

const resetAllSettings = () => {
  if (confirm('确定要恢复所有默认设置吗？此操作不可撤销。')) {
    settings.value = {
      theme: 'system',
      systemMessage: '',
      showSystemMessage: false,
      pasteThreshold: 3000,
      showGenerationStats: true,
      showThinking: false,
      keepStatsVisible: false,
      renderMarkdown: true,
      fullHeightCode: false,
      disableAutoScroll: false,
      alwaysShowSidebar: false,
      markdownTheme: 'default',
      temperature: 0.7,
      topP: 0.9,
      topK: 40,
      maxTokens: 4096,
      contextSize: 32768,
      gpuLayers: 99,
      repeatPenalty: 1.1,
      frequencyPenalty: 0,
      presencePenalty: 0,
      disableReasoningParsing: false,
      enableRawOutput: false,
      customJson: ''
    }
    saveSettings()
  }
}

const exportSettings = () => {
  const data = {
    ...settings.value,
    exportDate: new Date().toISOString(),
    appVersion: '1.0.0'
  }
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `neuralchat-settings-${Date.now()}.json`
  a.click()
  URL.revokeObjectURL(url)
}

const triggerFileInput = () => {
  fileInput.value?.click()
}

const handleFileImport = (event) => {
  const file = event.target.files[0]
  if (!file) return

  const reader = new FileReader()
  reader.onload = (e) => {
    try {
      const imported = JSON.parse(e.target.result)
      // 合并导入的设置
      Object.keys(settings.value).forEach(key => {
        if (imported[key] !== undefined) {
          settings.value[key] = imported[key]
        }
      })
      alert('设置导入成功')
      saveSettings()
    } catch (err) {
      alert('导入失败：无效的文件格式')
    }
  }
  reader.readAsText(file)
  event.target.value = ''
}

// 加载保存的设置
const loadSettings = () => {
  const saved = localStorage.getItem('neuralchat-settings')
  if (saved) {
    try {
      const parsed = JSON.parse(saved)
      Object.assign(settings.value, parsed)
      applyTheme()
    } catch (e) {
      console.error('Failed to load settings:', e)
    }
  }
}

loadSettings()

// 页面加载时获取模型数据
onMounted(async () => {
  await modelStore.fetchModels()
  await modelStore.fetchTypes()
})
</script>

<style lang="scss" scoped>
.settings-page {
  min-height: 100vh;
  background: linear-gradient(135deg, #0f0f1a 0%, #1a1a2e 50%, #16213e 100%);
  color: #e4e4e7;
}

// 顶部栏
.settings-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  background: rgba(15, 15, 26, 0.8);
  backdrop-filter: blur(20px);

  .header-left {
    display: flex;
    align-items: center;
    gap: 20px;
  }
}

.back-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 10px;
  color: #9ca3af;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    background: rgba(255, 255, 255, 0.1);
    color: #fff;
  }
}

.page-title {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 0;
  font-size: 20px;
  font-weight: 600;

  .el-icon {
    font-size: 24px;
    color: #667eea;
  }
}

// 布局
.settings-layout {
  display: flex;
  max-width: 1200px;
  margin: 0 auto;
  min-height: calc(100vh - 73px);
}

// 左侧导航
.settings-nav {
  width: 240px;
  padding: 24px 16px;
  border-right: 1px solid rgba(255, 255, 255, 0.05);
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  margin-bottom: 4px;
  border-radius: 10px;
  color: #9ca3af;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;

  .el-icon {
    font-size: 18px;
  }

  &:hover {
    background: rgba(255, 255, 255, 0.05);
    color: #e4e4e7;
  }

  &.active {
    background: rgba(102, 126, 234, 0.15);
    color: #667eea;
    font-weight: 500;
  }
}

// 右侧内容
.settings-content {
  flex: 1;
  padding: 32px;
  overflow-y: auto;
}

.settings-section {
  max-width: 640px;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 24px;

  .el-icon {
    font-size: 24px;
    color: #667eea;
  }

  h2 {
    margin: 0;
    font-size: 24px;
    font-weight: 600;
  }
}

// 设置组
.setting-group {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 16px;
  padding: 24px;
  margin-bottom: 24px;
}

// 设置项
.setting-item {
  margin-bottom: 24px;

  &:last-child {
    margin-bottom: 0;
  }
}

.setting-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;

  label {
    font-size: 15px;
    font-weight: 500;
    color: #e4e4e7;
  }
}

.setting-value {
  font-size: 13px;
  font-weight: 600;
  color: #667eea;
  background: rgba(102, 126, 234, 0.15);
  padding: 4px 10px;
  border-radius: 6px;
}

.setting-desc {
  font-size: 13px;
  color: #6b7280;
  margin-bottom: 12px;
  line-height: 1.5;
}

// 自定义滑块
.custom-slider {
  width: 100%;
  -webkit-appearance: none;
  appearance: none;
  height: 6px;
  background: rgba(255, 255, 255, 0.08);
  border-radius: 3px;
  outline: none;
  cursor: pointer;

  &::-webkit-slider-thumb {
    -webkit-appearance: none;
    appearance: none;
    width: 18px;
    height: 18px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border-radius: 50%;
    cursor: pointer;
    box-shadow: 0 2px 8px rgba(102, 126, 234, 0.4);
    transition: all 0.2s;
    border: 2px solid #fff;

    &:hover {
      transform: scale(1.1);
    }
  }
}

.slider-with-labels {
  display: flex;
  align-items: center;
  gap: 12px;

  span {
    font-size: 12px;
    color: #6b7280;
    white-space: nowrap;
  }

  .custom-slider {
    flex: 1;
  }
}

.range-marks {
  display: flex;
  justify-content: space-between;
  margin-top: 8px;
  padding: 0 4px;

  span {
    font-size: 11px;
    color: #4b5563;
  }
}

// 复选框设置
.setting-checkbox {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 16px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  cursor: pointer;

  &:last-child {
    border-bottom: none;
  }

  input[type="checkbox"] {
    width: 20px;
    height: 20px;
    margin-top: 2px;
    accent-color: #667eea;
    cursor: pointer;
  }
}

.checkbox-content {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.checkbox-title {
  font-size: 14px;
  font-weight: 500;
  color: #e4e4e7;
}

.checkbox-desc {
  font-size: 13px;
  color: #6b7280;
  line-height: 1.5;
}

// 主题选择器
.theme-selector {
  display: flex;
  gap: 12px;
}

.theme-card {
  flex: 1;
  position: relative;
  padding: 16px;
  background: rgba(255, 255, 255, 0.03);
  border: 2px solid rgba(255, 255, 255, 0.06);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;

  &:hover {
    border-color: rgba(255, 255, 255, 0.1);
  }

  &.active {
    border-color: #667eea;
    background: rgba(102, 126, 234, 0.1);
  }
}

.theme-preview {
  width: 64px;
  height: 48px;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.1);

  .preview-header {
    height: 12px;
    background: rgba(0, 0, 0, 0.1);
  }

  .preview-body {
    padding: 6px;

    .preview-line {
      height: 4px;
      background: rgba(0, 0, 0, 0.15);
      border-radius: 2px;
      margin-bottom: 4px;

      &.short {
        width: 60%;
      }
    }
  }

  &.dark {
    background: #1a1a2e;

    .preview-header {
      background: rgba(255, 255, 255, 0.05);
    }

    .preview-line {
      background: rgba(255, 255, 255, 0.1);
    }
  }

  &.light {
    background: #f8fafc;
  }

  &.system {
    background: linear-gradient(135deg, #f8fafc 50%, #1a1a2e 50%);
  }
}

.theme-name {
  font-size: 13px;
  color: #e4e4e7;
}

.check-icon {
  position: absolute;
  top: 8px;
  right: 8px;
  width: 18px;
  height: 18px;
  background: #667eea;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 10px;
}

// Markdown 主题网格
.markdown-theme-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 12px;
}

.markdown-theme-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.03);
  border: 2px solid rgba(255, 255, 255, 0.06);
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    border-color: rgba(255, 255, 255, 0.1);
  }

  &.active {
    border-color: #667eea;
    background: rgba(102, 126, 234, 0.1);
  }
}

.theme-preview-mini {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  font-size: 16px;
  font-weight: bold;
}

// 上下文选项
.context-options {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.context-btn {
  padding: 8px 16px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  color: #9ca3af;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    background: rgba(255, 255, 255, 0.08);
    color: #e4e4e7;
  }

  &.active {
    background: rgba(102, 126, 234, 0.2);
    border-color: #667eea;
    color: #667eea;
    font-weight: 500;
  }
}

// 文本域
.setting-textarea {
  width: 100%;
  padding: 12px;
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 10px;
  color: #e4e4e7;
  font-size: 14px;
  line-height: 1.6;
  resize: vertical;
  font-family: inherit;

  &:focus {
    outline: none;
    border-color: #667eea;
  }

  &.code {
    font-family: 'JetBrains Mono', monospace;
    font-size: 13px;
  }
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 12px;
  font-size: 13px;
  color: #9ca3af;
  cursor: pointer;

  input {
    accent-color: #667eea;
  }
}

// 导入/导出
.export-section,
.import-section,
.danger-zone {
  margin-bottom: 24px;

  h3 {
    margin: 0 0 8px 0;
    font-size: 15px;
    font-weight: 600;
    color: #e4e4e7;
  }
}

.section-desc {
  font-size: 13px;
  color: #6b7280;
  margin-bottom: 16px;
}

.action-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  border: none;

  &.primary {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;

    &:hover {
      transform: translateY(-1px);
      box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
    }
  }

  &.secondary {
    background: rgba(255, 255, 255, 0.08);
    border: 1px solid rgba(255, 255, 255, 0.1);
    color: #e4e4e7;

    &:hover {
      background: rgba(255, 255, 255, 0.12);
    }
  }

  &.danger {
    background: rgba(239, 68, 68, 0.1);
    border: 1px solid rgba(239, 68, 68, 0.3);
    color: #ef4444;

    &:hover {
      background: rgba(239, 68, 68, 0.2);
    }
  }
}

.danger-zone {
  padding: 20px;
  background: rgba(239, 68, 68, 0.05);
  border: 1px solid rgba(239, 68, 68, 0.1);
  border-radius: 12px;

  h3 {
    color: #ef4444;
  }
}

// 错误文本
.error-text {
  color: #ef4444;
  font-size: 12px;
  margin-top: 8px;
}

// 信息框
.info-box {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  background: rgba(102, 126, 234, 0.1);
  border: 1px solid rgba(102, 126, 234, 0.2);
  border-radius: 10px;
  font-size: 13px;
  color: #667eea;

  .el-icon {
    font-size: 16px;
  }
}

// 关于页面
.about-content {
  text-align: center;
  padding: 40px 0;
}

.logo-section {
  margin-bottom: 32px;
}

.app-logo {
  width: 80px;
  height: 80px;
  margin: 0 auto 16px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 8px 30px rgba(102, 126, 234, 0.3);

  svg {
    width: 40px;
    height: 40px;
    color: white;
  }
}

.app-name {
  margin: 0 0 8px 0;
  font-size: 24px;
  font-weight: 600;
}

.app-version {
  margin: 0;
  font-size: 14px;
  color: #6b7280;
}

.info-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-width: 300px;
  margin: 0 auto;
}

.info-item {
  display: flex;
  justify-content: space-between;
  padding: 12px 16px;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 10px;
}

.info-label {
  font-size: 13px;
  color: #9ca3af;
}

.info-value {
  font-size: 13px;
  color: #e4e4e7;
  font-weight: 500;
}

// 底部保存栏
.settings-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 32px;
  padding-top: 24px;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
}

.btn-secondary,
.btn-primary {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 24px;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  border: none;
}

.btn-secondary {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #9ca3af;

  &:hover {
    background: rgba(255, 255, 255, 0.1);
    color: #e4e4e7;
  }
}

.btn-primary {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 25px rgba(102, 126, 234, 0.5);
  }
}

// 模型列表样式
.refresh-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: rgba(102, 126, 234, 0.15);
  border: 1px solid rgba(102, 126, 234, 0.3);
  border-radius: 8px;
  color: #667eea;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;

  &:hover:not(:disabled) {
    background: rgba(102, 126, 234, 0.25);
  }

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
}

.model-filter {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 24px;
}

.filter-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 20px;
  color: #9ca3af;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    background: rgba(255, 255, 255, 0.06);
    border-color: rgba(255, 255, 255, 0.12);
  }

  &.active {
    background: rgba(102, 126, 234, 0.15);
    border-color: #667eea;
    color: #667eea;
    font-weight: 500;
  }
}

.filter-icon {
  font-size: 14px;
}

.filter-count {
  font-size: 11px;
  opacity: 0.7;
}

.models-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
}

.model-card {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 16px;
  padding: 20px;
  transition: all 0.3s ease;

  &:hover {
    transform: translateY(-2px);
    border-color: rgba(255, 255, 255, 0.1);
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
  }

  &.is-loaded {
    border-color: #22c55e;
    background: rgba(34, 197, 94, 0.05);

    &:hover {
      border-color: #4ade80;
      box-shadow: 0 8px 32px rgba(34, 197, 94, 0.15);
    }
  }
}

.model-header {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;

  .model-icon {
    width: 44px;
    height: 44px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 20px;
    border-radius: 12px;
    flex-shrink: 0;
  }

  .model-info {
    flex: 1;
    min-width: 0;

    h3 {
      margin: 0 0 8px 0;
      font-size: 15px;
      font-weight: 600;
      color: #e4e4e7;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
  }
}

.model-status {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.status-badge {
  padding: 3px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 500;

  &.exists {
    background: rgba(34, 197, 94, 0.15);
    color: #22c55e;
  }

  &.missing {
    background: rgba(239, 68, 68, 0.15);
    color: #ef4444;
  }

  &.loaded {
    background: rgba(102, 126, 234, 0.15);
    color: #667eea;
  }
}

.model-details {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
  margin-bottom: 12px;
  padding: 12px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 10px;

  .detail-item {
    display: flex;
    flex-direction: column;
    gap: 2px;

    .label {
      font-size: 11px;
      color: #6b7280;
    }

    .value {
      font-size: 12px;
      color: #e4e4e7;
      font-weight: 500;
    }
  }
}

.model-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 12px;

  .tag {
    padding: 3px 8px;
    background: rgba(255, 255, 255, 0.05);
    border-radius: 4px;
    font-size: 11px;
    color: #9ca3af;
  }
}

.model-desc {
  font-size: 12px;
  color: #6b7280;
  line-height: 1.5;
  margin: 0 0 16px 0;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.model-actions {
  .action-btn {
    width: 100%;
    padding: 10px 16px;
    border-radius: 10px;
    font-size: 13px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s;
    border: none;

    &.primary {
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white;

      &:hover:not(:disabled) {
        transform: translateY(-1px);
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
      }

      &:disabled {
        opacity: 0.5;
        cursor: not-allowed;
      }
    }

    &.danger {
      background: rgba(239, 68, 68, 0.1);
      border: 1px solid rgba(239, 68, 68, 0.3);
      color: #ef4444;

      &:hover {
        background: rgba(239, 68, 68, 0.2);
      }
    }
  }
}

// 响应式
@media (max-width: 768px) {
  .settings-layout {
    flex-direction: column;
  }

  .settings-nav {
    width: 100%;
    display: flex;
    overflow-x: auto;
    padding: 16px;
    border-right: none;
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);

    .nav-item {
      white-space: nowrap;
      margin-bottom: 0;
      margin-right: 8px;
    }
  }

  .settings-content {
    padding: 20px;
  }

  .markdown-theme-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}
</style>
