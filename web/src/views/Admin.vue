<template>
  <div class="admin-container">
    <!-- 顶部状态栏 -->
    <div class="status-bar">
      <div class="status-item">
        <span class="status-label">后端服务</span>
        <span class="status-value">{{ backendServices.length }} 个</span>
      </div>
      <div class="status-item">
        <span class="status-label">已加载模型</span>
        <span class="status-value">{{ totalModels }}</span>
      </div>
      <div class="status-item">
        <span class="status-label">活跃请求</span>
        <span class="status-value">{{ totalActiveRequests }}</span>
      </div>
      <div class="status-item">
        <span class="status-label">Token 速度</span>
        <span class="status-value highlight">{{ totalTokenSpeed.toFixed(1) }} t/s</span>
      </div>
    </div>

    <!-- 后端服务列表 -->
    <div class="section">
      <div class="section-header">
        <h2 class="section-title">🖥️ 后端服务</h2>
        <div class="section-actions">
          <button class="btn btn-sm" @click="addBackend" :disabled="isLoading">+ 添加后端</button>
          <button class="btn btn-sm" @click="scanAllBackends" :disabled="isLoading">扫描所有</button>
          <button class="btn btn-sm" @click="refreshAllData" :disabled="isLoading">刷新</button>
        </div>
      </div>
      
      <div class="backend-list">
        <div v-for="backend in backendServices" :key="backend.url" class="backend-card" :class="{ offline: !backend.online }">
          <div class="backend-header">
            <div class="backend-info">
              <span class="backend-name">{{ backend.name }}</span>
              <span class="backend-url">{{ backend.url }}</span>
              <span class="backend-status" :class="backend.online ? 'online' : 'offline'">
                {{ backend.online ? '在线' : '离线' }}
              </span>
            </div>
            <div class="backend-actions">
              <button class="btn btn-sm" @click="scanBackendModels(backend)" :disabled="isLoading">扫描模型</button>
              <button class="btn btn-sm btn-danger" @click="removeBackend(backend)" :disabled="isLoading">移除</button>
            </div>
          </div>
          
          <div class="backend-stats" v-if="backend.online">
            <div class="stat-mini">
              <span class="label">模型:</span>
              <span class="value">{{ backend.status?.model_count || 0 }}</span>
            </div>
            <div class="stat-mini">
              <span class="label">请求:</span>
              <span class="value">{{ backend.inference?.current_active_requests || 0 }}</span>
            </div>
            <div class="stat-mini">
              <span class="label">速度:</span>
              <span class="value">{{ (backend.inference?.current_speed_tokens_per_sec || 0).toFixed(1) }} t/s</span>
            </div>
            <div class="stat-mini">
              <span class="label">CPU:</span>
              <span class="value">{{ backend.system?.cpu?.percent?.toFixed(1) || 0 }}%</span>
            </div>
            <div class="stat-mini">
              <span class="label">内存:</span>
              <span class="value">{{ backend.system?.memory?.percent?.toFixed(1) || 0 }}%</span>
            </div>
          </div>
          
          <div class="backend-models" v-if="backend.online && backend.status?.loaded_models?.length">
            <div class="model-tag" v-for="modelId in backend.status.loaded_models" :key="modelId">
              {{ modelId }}
              <button class="btn-unload" @click="unloadModel(backend, modelId)" title="卸载">×</button>
            </div>
          </div>
        </div>
        
        <div v-if="!backendServices.length" class="empty-state">
          暂无后端服务，点击"添加后端"添加
        </div>
      </div>
    </div>

    <!-- 汇总推理性能 -->
    <div class="section">
      <h2 class="section-title">🔥 推理性能汇总</h2>
      <div class="stats-grid">
        <div class="stat-card highlight">
          <div class="stat-icon">⚡</div>
          <div class="stat-content">
            <div class="stat-label">总 Token 速度</div>
            <div class="stat-value">{{ totalTokenSpeed.toFixed(1) }}</div>
            <div class="stat-detail">tokens/sec</div>
          </div>
        </div>
        
        <div class="stat-card">
          <div class="stat-icon">📝</div>
          <div class="stat-content">
            <div class="stat-label">总生成 Token</div>
            <div class="stat-value">{{ formatNumber(totalTokens) }}</div>
            <div class="stat-detail">输出: {{ formatNumber(totalOutputTokens) }}</div>
          </div>
        </div>
        
        <div class="stat-card">
          <div class="stat-icon">🔄</div>
          <div class="stat-content">
            <div class="stat-label">活跃请求</div>
            <div class="stat-value">{{ totalActiveRequests }}</div>
            <div class="stat-detail">完成: {{ formatNumber(totalCompletedRequests) }}</div>
          </div>
        </div>
        
        <div class="stat-card">
          <div class="stat-icon">⏱️</div>
          <div class="stat-content">
            <div class="stat-label">平均响应</div>
            <div class="stat-value">{{ formatResponseTime(avgResponseTime) }}</div>
            <div class="stat-detail">{{ avgTokensPerSec.toFixed(1) }} t/s</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 添加后端对话框 -->
    <div class="modal" v-if="showAddModal" @click.self="showAddModal = false">
      <div class="modal-content">
        <h3>添加后端服务</h3>
        <div class="form-group">
          <label>名称:</label>
          <input v-model="newBackend.name" placeholder="例如: 主服务" />
        </div>
        <div class="form-group">
          <label>URL:</label>
          <input v-model="newBackend.url" placeholder="例如: http://localhost:38520" />
        </div>
        <div class="modal-actions">
          <button class="btn" @click="confirmAddBackend">添加</button>
          <button class="btn btn-secondary" @click="showAddModal = false">取消</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'

// 后端服务列表
const backendServices = ref([
  { name: '服务-38520', url: 'http://localhost:38520', online: false, status: null, inference: null, system: null },
  { name: '服务-39520', url: 'http://localhost:39520', online: false, status: null, inference: null, system: null }
])

const isLoading = ref(false)
const showAddModal = ref(false)
const newBackend = ref({ name: '', url: '' })

let refreshTimer = null

// 计算属性 - 汇总数据
const totalModels = computed(() => {
  return backendServices.value.reduce((sum, b) => sum + (b.status?.model_count || 0), 0)
})

const totalActiveRequests = computed(() => {
  return backendServices.value.reduce((sum, b) => sum + (b.inference?.current_active_requests || 0), 0)
})

const totalTokenSpeed = computed(() => {
  return backendServices.value.reduce((sum, b) => sum + (b.inference?.current_speed_tokens_per_sec || 0), 0)
})

const totalTokens = computed(() => {
  return backendServices.value.reduce((sum, b) => sum + (b.inference?.total_tokens || 0), 0)
})

const totalOutputTokens = computed(() => {
  return backendServices.value.reduce((sum, b) => sum + (b.inference?.total_output_tokens || 0), 0)
})

const totalCompletedRequests = computed(() => {
  return backendServices.value.reduce((sum, b) => sum + (b.inference?.completed_requests || 0), 0)
})

const avgResponseTime = computed(() => {
  const onlineBackends = backendServices.value.filter(b => b.online && b.inference?.avg_response_time)
  if (!onlineBackends.length) return 0
  return onlineBackends.reduce((sum, b) => sum + b.inference.avg_response_time, 0) / onlineBackends.length
})

const avgTokensPerSec = computed(() => {
  const onlineBackends = backendServices.value.filter(b => b.online && b.inference?.avg_tokens_per_second)
  if (!onlineBackends.length) return 0
  return onlineBackends.reduce((sum, b) => sum + b.inference.avg_tokens_per_second, 0) / onlineBackends.length
})

// API 调用
async function fetchBackendData(backend) {
  try {
    const [statusRes, inferenceRes, systemRes] = await Promise.all([
      fetch(`${backend.url}/api/v1/admin/backend/status`).catch(() => null),
      fetch(`${backend.url}/api/v1/admin/inference/stats`).catch(() => null),
      fetch(`${backend.url}/api/v1/admin/system/stats`).catch(() => null)
    ])
    
    backend.online = !!statusRes?.ok
    backend.status = statusRes?.ok ? await statusRes.json() : null
    backend.inference = inferenceRes?.ok ? await inferenceRes.json() : null
    backend.system = systemRes?.ok ? await systemRes.json() : null
  } catch (error) {
    backend.online = false
    console.error(`获取后端 ${backend.url} 数据失败:`, error)
  }
}

async function refreshAllData() {
  isLoading.value = true
  await Promise.all(backendServices.value.map(fetchBackendData))
  isLoading.value = false
}

async function scanBackendModels(backend) {
  isLoading.value = true
  try {
    const response = await fetch(`${backend.url}/api/v1/admin/backend/scan-running`, { method: 'POST' })
    const data = await response.json()
    alert(data.message || `扫描完成: ${data.registered_count} 个模型`)
    await fetchBackendData(backend)
  } catch (error) {
    alert('扫描失败: ' + error.message)
  }
  isLoading.value = false
}

async function scanAllBackends() {
  isLoading.value = true
  for (const backend of backendServices.value) {
    if (backend.online) {
      try {
        await fetch(`${backend.url}/api/v1/admin/backend/scan-running`, { method: 'POST' })
      } catch (e) {}
    }
  }
  await refreshAllData()
  isLoading.value = false
}

async function unloadModel(backend, modelId) {
  if (!confirm(`确定要从 ${backend.name} 卸载模型 ${modelId}？`)) return
  
  isLoading.value = true
  try {
    const response = await fetch(`${backend.url}/api/v1/admin/backend/control`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: 'unload', model_id: modelId })
    })
    const data = await response.json()
    if (data.success) {
      await fetchBackendData(backend)
    } else {
      alert('卸载失败: ' + (data.error || '未知错误'))
    }
  } catch (error) {
    alert('卸载失败: ' + error.message)
  }
  isLoading.value = false
}

function addBackend() {
  newBackend.value = { name: '', url: '' }
  showAddModal.value = true
}

function confirmAddBackend() {
  if (!newBackend.value.url) {
    alert('请输入后端 URL')
    return
  }
  backendServices.value.push({
    name: newBackend.value.name || newBackend.value.url,
    url: newBackend.value.url,
    online: false,
    status: null,
    inference: null,
    system: null
  })
  showAddModal.value = false
  fetchBackendData(backendServices.value[backendServices.value.length - 1])
}

function removeBackend(backend) {
  if (!confirm(`确定要移除后端 ${backend.name}？`)) return
  const index = backendServices.value.indexOf(backend)
  if (index > -1) {
    backendServices.value.splice(index, 1)
  }
}

// 工具函数
function formatNumber(num) {
  if (!num) return '0'
  if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M'
  if (num >= 1000) return (num / 1000).toFixed(1) + 'K'
  return num.toString()
}

function formatResponseTime(seconds) {
  if (!seconds) return '0ms'
  if (seconds < 1) return (seconds * 1000).toFixed(0) + 'ms'
  return seconds.toFixed(1) + 's'
}

// 生命周期
onMounted(() => {
  refreshAllData()
  refreshTimer = setInterval(refreshAllData, 5000)
})

onUnmounted(() => {
  if (refreshTimer) clearInterval(refreshTimer)
})
</script>

<style scoped>
.admin-container {
  padding: 20px;
  max-width: 1400px;
  margin: 0 auto;
}

.status-bar {
  display: flex;
  gap: 30px;
  padding: 15px 20px;
  background: #1a1a2e;
  border-radius: 10px;
  margin-bottom: 20px;
}

.status-item {
  display: flex;
  align-items: center;
  gap: 10px;
}

.status-label {
  color: #888;
  font-size: 14px;
}

.status-value {
  font-weight: 600;
  font-size: 16px;
  color: #fff;
}

.status-value.highlight {
  color: #4ade80;
}

.section {
  background: #1a1a2e;
  border-radius: 10px;
  padding: 20px;
  margin-bottom: 20px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.section-title {
  font-size: 18px;
  font-weight: 600;
  color: #fff;
  margin: 0;
}

.section-actions {
  display: flex;
  gap: 10px;
}

.backend-list {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.backend-card {
  background: #252542;
  border-radius: 10px;
  padding: 15px;
  border: 1px solid #333;
}

.backend-card.offline {
  opacity: 0.5;
  border-color: #ef4444;
}

.backend-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.backend-info {
  display: flex;
  align-items: center;
  gap: 10px;
}

.backend-name {
  font-weight: 600;
  color: #fff;
  font-size: 16px;
}

.backend-url {
  color: #888;
  font-size: 12px;
}

.backend-status {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
}

.backend-status.online {
  background: #22c55e20;
  color: #4ade80;
}

.backend-status.offline {
  background: #ef444420;
  color: #ef4444;
}

.backend-actions {
  display: flex;
  gap: 8px;
}

.backend-stats {
  display: flex;
  gap: 20px;
  padding: 10px 0;
  border-top: 1px solid #333;
  border-bottom: 1px solid #333;
  margin-bottom: 10px;
}

.stat-mini {
  display: flex;
  gap: 5px;
}

.stat-mini .label {
  color: #888;
  font-size: 12px;
}

.stat-mini .value {
  color: #fff;
  font-size: 12px;
  font-weight: 600;
}

.backend-models {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.model-tag {
  background: #3b82f620;
  color: #60a5fa;
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 12px;
  display: flex;
  align-items: center;
  gap: 5px;
}

.btn-unload {
  background: none;
  border: none;
  color: #ef4444;
  cursor: pointer;
  font-size: 14px;
  padding: 0 2px;
}

.btn-unload:hover {
  color: #f87171;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 15px;
}

.stat-card {
  background: #252542;
  border-radius: 10px;
  padding: 15px;
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.stat-card.highlight {
  background: linear-gradient(135deg, #1a1a2e 0%, #2d1f3d 100%);
  border: 1px solid #8b5cf6;
}

.stat-icon {
  font-size: 24px;
}

.stat-content {
  flex: 1;
}

.stat-label {
  color: #888;
  font-size: 12px;
  margin-bottom: 3px;
}

.stat-value {
  font-size: 24px;
  font-weight: 700;
  color: #fff;
}

.stat-detail {
  font-size: 11px;
  color: #666;
}

.btn {
  padding: 8px 16px;
  border: none;
  border-radius: 6px;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
  background: #3b82f6;
  color: white;
}

.btn:hover:not(:disabled) {
  background: #2563eb;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-secondary {
  background: #4b5563;
}

.btn-secondary:hover:not(:disabled) {
  background: #6b7280;
}

.btn-danger {
  background: #ef4444;
}

.btn-danger:hover:not(:disabled) {
  background: #dc2626;
}

.btn-sm {
  padding: 5px 10px;
  font-size: 12px;
}

.empty-state {
  text-align: center;
  color: #666;
  padding: 30px;
}

.modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: #1a1a2e;
  padding: 25px;
  border-radius: 10px;
  min-width: 350px;
}

.modal-content h3 {
  margin: 0 0 20px 0;
  color: #fff;
}

.form-group {
  margin-bottom: 15px;
}

.form-group label {
  display: block;
  color: #888;
  font-size: 13px;
  margin-bottom: 5px;
}

.form-group input {
  width: 100%;
  padding: 10px;
  border-radius: 6px;
  border: 1px solid #333;
  background: #252542;
  color: #fff;
  font-size: 14px;
  box-sizing: border-box;
}

.modal-actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
  margin-top: 20px;
}
</style>
