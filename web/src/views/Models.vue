<template>
  <div class="models-container">
    <!-- 背景装饰 -->
    <div class="bg-decoration">
      <div class="gradient-orb orb-1" />
      <div class="gradient-orb orb-2" />
      <div class="gradient-orb orb-3" />
    </div>

    <!-- 顶部导航 -->
    <header class="page-header">
      <div class="header-left">
        <button class="back-btn" @click="$router.push('/')">
          <el-icon><ArrowLeft /></el-icon>
          <span>返回聊天</span>
        </button>
      </div>
      <div class="header-center">
        <div class="title-wrapper">
          <div class="title-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
            </svg>
          </div>
          <h1>模型管理</h1>
        </div>
        <p class="subtitle">管理和配置您的 AI 模型</p>
      </div>
      <div class="header-right">
        <button class="refresh-btn" :class="{ 'is-loading': loading }" @click="refreshModels">
          <el-icon><Refresh /></el-icon>
          <span>刷新</span>
        </button>
      </div>
    </header>

    <!-- 统计信息 -->
    <div class="stats-bar">
      <div class="stat-item">
        <div class="stat-value">{{ models.length }}</div>
        <div class="stat-label">总模型</div>
      </div>
      <div class="stat-divider" />
      <div class="stat-item">
        <div class="stat-value">{{ loadedModelsCount }}</div>
        <div class="stat-label">已加载</div>
      </div>
      <div class="stat-divider" />
      <div class="stat-item">
        <div class="stat-value">{{ availableModelsCount }}</div>
        <div class="stat-label">可用</div>
      </div>
    </div>

    <!-- 模型类型筛选 -->
    <div class="filter-section">
      <div class="filter-label">
        <el-icon><Filter /></el-icon>
        <span>筛选</span>
      </div>
      <div class="filter-chips">
        <button
          class="filter-chip"
          :class="{ active: selectedType === '' }"
          @click="selectedType = ''"
        >
          <el-icon class="chip-icon"><Grid /></el-icon>
          <span class="chip-text">全部</span>
          <span class="chip-count">{{ models.length }}</span>
        </button>
        <button
          v-for="type in modelTypes"
          :key="type.id"
          class="filter-chip"
          :class="{ active: selectedType === type.id }"
          :style="{ '--chip-color': type.color }"
          @click="selectedType = type.id"
        >
          <el-icon class="chip-icon">
            <component :is="getTypeIcon(type.id)" />
          </el-icon>
          <span class="chip-text">{{ type.description }}</span>
          <span class="chip-count">{{ type.count }}</span>
        </button>
      </div>
    </div>

    <!-- 模型列表 -->
    <div class="models-grid">
      <div
        v-for="model in filteredModels"
        :key="model.id"
        class="model-card"
        :class="{ 'is-loaded': model.status === 'loaded', 'is-missing': !model.file_exists }"
        :style="{ '--model-color': getTypeColor(model.type) }"
      >
        <!-- 卡片头部 -->
        <div class="card-header">
          <div class="model-icon-wrapper">
              <div class="model-icon" :style="{ background: getTypeGradient(model.type) }">
                <el-icon :size="24" color="white">
                  <component :is="getTypeIcon(model.type)" />
                </el-icon>
              </div>
              <div v-if="model.status === 'loaded'" class="status-indicator" />
            </div>
          <div class="model-title-section">
            <h3 class="model-name">{{ model.name }}</h3>
            <div class="model-badges">
              <span
                class="badge"
                :class="model.file_exists ? 'badge-success' : 'badge-error'"
              >
                <el-icon><CircleCheck v-if="model.file_exists" /><CircleClose v-else /></el-icon>
                {{ model.file_exists ? '文件存在' : '文件缺失' }}
              </span>
              <span v-if="model.status === 'loaded'" class="badge badge-active">
                <span class="pulse-dot" />
                已加载
              </span>
            </div>
          </div>
        </div>

        <!-- 规格信息 -->
        <div class="specs-grid">
          <div class="spec-item">
            <div class="spec-icon">
              <el-icon><Folder /></el-icon>
            </div>
            <div class="spec-content">
              <div class="spec-label">类型</div>
              <div class="spec-value">{{ formatType(model.type) }}</div>
            </div>
          </div>
          <div class="spec-item">
            <div class="spec-icon">
              <el-icon><Files /></el-icon>
            </div>
            <div class="spec-content">
              <div class="spec-label">大小</div>
              <div class="spec-value">{{ model.size }}</div>
            </div>
          </div>
          <div class="spec-item">
            <div class="spec-icon">
              <el-icon><ScaleToOriginal /></el-icon>
            </div>
            <div class="spec-content">
              <div class="spec-label">量化</div>
              <div class="spec-value">{{ model.quantization }}</div>
            </div>
          </div>
          <div class="spec-item">
            <div class="spec-icon">
              <el-icon><Monitor /></el-icon>
            </div>
            <div class="spec-content">
              <div class="spec-label">上下文</div>
              <div class="spec-value">{{ formatContext(model.max_context) }}</div>
            </div>
          </div>
          <div class="spec-item">
            <div class="spec-icon">
              <el-icon><Tools /></el-icon>
            </div>
            <div class="spec-content">
              <div class="spec-label">后端</div>
              <div class="spec-value">{{ model.backend }}</div>
            </div>
          </div>
        </div>

        <!-- 标签 -->
        <div v-if="model.tags?.length" class="tags-section">
          <span
            v-for="tag in model.tags"
            :key="tag"
            class="tag"
          >
            {{ tag }}
          </span>
        </div>

        <!-- 描述 -->
        <p class="model-description">{{ model.description }}</p>

        <!-- 操作按钮 -->
        <div class="card-actions">
          <button
            v-if="model.status !== 'loaded'"
            class="action-btn btn-primary"
            :class="{ 'is-loading': loadingModel === model.id }"
            :disabled="!model.file_exists || loadingModel === model.id"
            @click="loadModel(model)"
          >
            <el-icon v-if="loadingModel !== model.id"><Download /></el-icon>
            <el-icon v-else class="is-loading"><Loading /></el-icon>
            <span>{{ loadingModel === model.id ? '加载中...' : '加载模型' }}</span>
          </button>
          <button
            v-else
            class="action-btn btn-danger"
            @click="unloadModel(model)"
          >
            <el-icon><Close /></el-icon>
            <span>卸载模型</span>
          </button>
        </div>

        <!-- 加载动画遮罩 -->
        <div v-if="loadingModel === model.id" class="loading-overlay">
          <div class="loading-spinner">
            <div class="spinner-ring" />
            <div class="spinner-ring" />
            <div class="spinner-ring" />
          </div>
          <p>正在加载模型...</p>
        </div>
      </div>
    </div>

    <!-- 空状态 -->
    <div v-if="filteredModels.length === 0" class="empty-state">
      <div class="empty-icon">
        <el-icon><Search /></el-icon>
      </div>
      <h3>没有找到模型</h3>
      <p>尝试选择其他分类或刷新列表</p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useModelStore } from '@/stores/models'
import { storeToRefs } from 'pinia'
import { ElMessage } from 'element-plus'
import {
  ArrowLeft, Refresh, Filter, Download, Close, Loading,
  CircleCheck, CircleClose, Grid, Folder, ScaleToOriginal, Monitor, Files, Search, Tools,
  ChatLineRound, View, Cpu, DataLine, Box, EditPen
} from '@element-plus/icons-vue'

const modelStore = useModelStore()
const { models, modelTypes, loading } = storeToRefs(modelStore)

const selectedType = ref('')
const loadingModel = ref(null)

// 计算属性
const filteredModels = computed(() => {
  if (!selectedType.value) return models.value
  return models.value.filter(m => m.type === selectedType.value)
})

const loadedModelsCount = computed(() => {
  return models.value.filter(m => m.status === 'loaded').length
})

const availableModelsCount = computed(() => {
  return models.value.filter(m => m.file_exists).length
})

// 类型图标映射（使用 Element Plus 简化图标）
const typeIconMap = {
  'language-model': 'ChatLineRound',
  'vision-language-model': 'View',
  'code-model': 'EditPen',
  'reasoning-model': 'Cpu',
  'embedding-model': 'DataLine'
}

// 类型渐变色映射
const typeGradientMap = {
  'language-model': 'linear-gradient(135deg, #667eea, #764ba2)',
  'vision-language-model': 'linear-gradient(135deg, #f093fb, #f5576c)',
  'code-model': 'linear-gradient(135deg, #4facfe, #00f2fe)',
  'reasoning-model': 'linear-gradient(135deg, #43e97b, #38f9d7)',
  'embedding-model': 'linear-gradient(135deg, #fa709a, #fee140)'
}

// 获取类型图标组件名
function getTypeIcon(type) {
  return typeIconMap[type] || 'Box'
}

// 获取类型渐变色
function getTypeGradient(type) {
  return typeGradientMap[type] || 'linear-gradient(135deg, #667eea, #764ba2)'
}

// 获取类型颜色
function getTypeColor(type) {
  const typeInfo = modelTypes.value.find(t => t.id === type)
  return typeInfo?.color || '#667eea'
}

// 格式化类型名称
function formatType(type) {
  const typeMap = {
    'language-model': '语言模型',
    'vision-language-model': '视觉语言模型',
    'code-model': '代码模型',
    'reasoning-model': '推理模型',
    'embedding-model': '嵌入模型'
  }
  return typeMap[type] || type
}

// 格式化上下文
function formatContext(size) {
  if (size >= 131072) return '128K'
  if (size >= 65536) return '64K'
  if (size >= 32768) return '32K'
  if (size >= 16384) return '16K'
  if (size >= 8192) return '8K'
  return size.toString()
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

onMounted(async () => {
  await modelStore.fetchModels()
  await modelStore.fetchTypes()
})
</script>

<style lang="scss" scoped>
.models-container {
  min-height: 100vh;
  background: linear-gradient(135deg, #0a0a0f 0%, #12121a 50%, #0d0d14 100%);
  padding: 32px;
  position: relative;
  overflow-x: hidden;
  color: #e4e4e7;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}

// 背景装饰
.bg-decoration {
  position: fixed;
  inset: 0;
  pointer-events: none;
  overflow: hidden;
  z-index: 0;
}

.gradient-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.15;

  &.orb-1 {
    width: 600px;
    height: 600px;
    background: linear-gradient(135deg, #667eea, #764ba2);
    top: -200px;
    right: -200px;
  }

  &.orb-2 {
    width: 400px;
    height: 400px;
    background: linear-gradient(135deg, #f093fb, #f5576c);
    bottom: 10%;
    left: -100px;
  }

  &.orb-3 {
    width: 300px;
    height: 300px;
    background: linear-gradient(135deg, #4facfe, #00f2fe);
    top: 40%;
    right: 10%;
  }
}

// 顶部导航
.page-header {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 32px;
  padding-bottom: 24px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.header-left, .header-right {
  flex: 1;
}

.header-right {
  display: flex;
  justify-content: flex-end;
}

.header-center {
  text-align: center;
}

.title-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  margin-bottom: 8px;
}

.title-icon {
  width: 40px;
  height: 40px;
  background: linear-gradient(135deg, #667eea, #764ba2);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 20px rgba(102, 126, 234, 0.3);

  svg {
    width: 24px;
    height: 24px;
    color: white;
  }
}

h1 {
  font-size: 28px;
  font-weight: 700;
  margin: 0;
  background: linear-gradient(135deg, #fff 0%, #a0aec0 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.subtitle {
  font-size: 14px;
  color: #6b7280;
  margin: 0;
}

// 按钮样式
.back-btn, .refresh-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 18px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 10px;
  color: #9ca3af;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.3s ease;

  &:hover {
    background: rgba(255, 255, 255, 0.1);
    color: white;
    transform: translateY(-2px);
  }

  &.is-loading {
    opacity: 0.7;
    pointer-events: none;

    .el-icon {
      animation: spin 1s linear infinite;
    }
  }
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

// 统计栏
.stats-bar {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 32px;
  margin-bottom: 32px;
  padding: 20px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 16px;
  backdrop-filter: blur(10px);
}

.stat-item {
  text-align: center;
}

.stat-value {
  font-size: 32px;
  font-weight: 700;
  background: linear-gradient(135deg, #667eea, #764ba2);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.stat-label {
  font-size: 13px;
  color: #6b7280;
  margin-top: 4px;
}

.stat-divider {
  width: 1px;
  height: 40px;
  background: rgba(255, 255, 255, 0.1);
}

// 筛选区域
.filter-section {
  position: relative;
  z-index: 1;
  margin-bottom: 32px;
}

.filter-label {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
  color: #6b7280;
  font-size: 14px;
}

.filter-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.filter-chip {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 100px;
  color: #9ca3af;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.3s ease;

  &:hover {
    background: rgba(255, 255, 255, 0.1);
    transform: translateY(-2px);
  }

  &.active {
    background: linear-gradient(135deg, #667eea, #764ba2);
    border-color: transparent;
    color: white;
    box-shadow: 0 4px 20px rgba(102, 126, 234, 0.4);

    .chip-count {
      background: rgba(255, 255, 255, 0.2);
      color: white;
    }
  }
}

.chip-icon {
  font-size: 14px;
  margin-right: 4px;
}

.chip-count {
  padding: 2px 8px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 100px;
  font-size: 12px;
  font-weight: 600;
  color: #9ca3af;
}

// 模型网格
.models-grid {
  position: relative;
  z-index: 1;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
  gap: 24px;
}

// 模型卡片
.model-card {
  position: relative;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 20px;
  padding: 24px;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;

  &::before {
    content: '';
    position: absolute;
    inset: 0;
    background: linear-gradient(135deg, var(--model-color, #667eea) 0%, transparent 60%);
    opacity: 0;
    transition: opacity 0.4s ease;
    pointer-events: none;
  }

  &:hover {
    transform: translateY(-4px);
    border-color: rgba(255, 255, 255, 0.15);
    box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);

    &::before {
      opacity: 0.05;
    }
  }

  &.is-loaded {
    border-color: rgba(16, 185, 129, 0.3);
    background: linear-gradient(135deg, rgba(16, 185, 129, 0.05) 0%, rgba(255, 255, 255, 0.03) 100%);

    &::before {
      background: linear-gradient(135deg, #10b981 0%, transparent 60%);
      opacity: 0.08;
    }
  }

  &.is-missing {
    opacity: 0.7;
  }
}

// 卡片头部
.card-header {
  display: flex;
  gap: 16px;
  margin-bottom: 20px;
}

.model-icon-wrapper {
  position: relative;
}

.model-icon {
  width: 56px;
  height: 56px;
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
}

.status-indicator {
  position: absolute;
  bottom: -4px;
  right: -4px;
  width: 16px;
  height: 16px;
  background: #10b981;
  border: 3px solid #0a0a0f;
  border-radius: 50%;
  box-shadow: 0 0 0 2px #10b981;
}

.model-title-section {
  flex: 1;
  min-width: 0;
}

.model-name {
  font-size: 18px;
  font-weight: 600;
  margin: 0 0 10px 0;
  color: white;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.model-badges {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.badge {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;

  .el-icon {
    font-size: 12px;
  }
}

.badge-success {
  background: rgba(16, 185, 129, 0.15);
  color: #34d399;
}

.badge-error {
  background: rgba(239, 68, 68, 0.15);
  color: #f87171;
}

.badge-active {
  background: rgba(16, 185, 129, 0.2);
  color: #34d399;
}

.pulse-dot {
  width: 6px;
  height: 6px;
  background: #10b981;
  border-radius: 50%;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(0.8); }
}

// 规格网格
.specs-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}

.spec-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 12px;
  transition: all 0.3s ease;

  &:hover {
    background: rgba(255, 255, 255, 0.06);
  }
}

.spec-icon {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(102, 126, 234, 0.1);
  border-radius: 8px;
  color: #667eea;
  font-size: 16px;
}

.spec-content {
  flex: 1;
  min-width: 0;
}

.spec-label {
  font-size: 11px;
  color: #6b7280;
  margin-bottom: 2px;
}

.spec-value {
  font-size: 13px;
  font-weight: 600;
  color: #e4e4e7;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

// 标签区域
.tags-section {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 16px;
}

.tag {
  padding: 4px 10px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 6px;
  font-size: 12px;
  color: #9ca3af;
  transition: all 0.2s ease;

  &:hover {
    background: rgba(255, 255, 255, 0.1);
    color: white;
  }
}

// 描述
.model-description {
  font-size: 13px;
  line-height: 1.6;
  color: #6b7280;
  margin: 0 0 20px 0;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

// 操作按钮
.card-actions {
  display: flex;
  gap: 10px;
}

.action-btn {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px 20px;
  border: none;
  border-radius: 12px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  &.is-loading {
    pointer-events: none;
  }

  .el-icon.is-loading {
    animation: spin 1s linear infinite;
  }
}

.btn-primary {
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: white;
  box-shadow: 0 4px 16px rgba(102, 126, 234, 0.3);

  &:hover:not(:disabled) {
    transform: translateY(-2px);
    box-shadow: 0 6px 24px rgba(102, 126, 234, 0.4);
  }
}

.btn-danger {
  background: rgba(239, 68, 68, 0.1);
  color: #f87171;
  border: 1px solid rgba(239, 68, 68, 0.2);

  &:hover {
    background: rgba(239, 68, 68, 0.2);
    border-color: rgba(239, 68, 68, 0.3);
  }
}

// 加载遮罩
.loading-overlay {
  position: absolute;
  inset: 0;
  background: rgba(10, 10, 15, 0.9);
  backdrop-filter: blur(4px);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  z-index: 10;
  border-radius: 20px;

  p {
    color: #9ca3af;
    font-size: 14px;
    margin: 0;
  }
}

.loading-spinner {
  position: relative;
  width: 60px;
  height: 60px;
}

.spinner-ring {
  position: absolute;
  inset: 0;
  border: 3px solid transparent;
  border-top-color: #667eea;
  border-radius: 50%;
  animation: spin 1s linear infinite;

  &:nth-child(2) {
    inset: 8px;
    border-top-color: #764ba2;
    animation-duration: 1.5s;
    animation-direction: reverse;
  }

  &:nth-child(3) {
    inset: 16px;
    border-top-color: #f093fb;
    animation-duration: 2s;
  }
}

// 空状态
.empty-state {
  position: relative;
  z-index: 1;
  text-align: center;
  padding: 80px 20px;

  .empty-icon {
    width: 80px;
    height: 80px;
    margin: 0 auto 20px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(102, 126, 234, 0.1);
    border-radius: 20px;
    color: #667eea;
    font-size: 40px;
  }

  h3 {
    font-size: 20px;
    font-weight: 600;
    color: white;
    margin: 0 0 8px 0;
  }

  p {
    font-size: 14px;
    color: #6b7280;
    margin: 0;
  }
}

// 响应式
@media (max-width: 768px) {
  .models-container {
    padding: 20px;
  }

  .page-header {
    flex-direction: column;
    gap: 16px;
    text-align: center;
  }

  .header-left, .header-right {
    width: 100%;
    justify-content: center;
  }

  .stats-bar {
    flex-direction: column;
    gap: 16px;
  }

  .stat-divider {
    width: 60px;
    height: 1px;
  }

  .models-grid {
    grid-template-columns: 1fr;
  }

  .specs-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
