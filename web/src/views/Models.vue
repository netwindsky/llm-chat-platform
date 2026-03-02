<template>
  <div class="models-container">
    <!-- 顶部导航 -->
    <div class="page-header">
      <el-button @click="$router.push('/')">
        <el-icon><Back /></el-icon>
        返回聊天
      </el-button>
      <h1>模型管理</h1>
      <el-button @click="refreshModels" :loading="loading">
        <el-icon><Refresh /></el-icon>
        刷新
      </el-button>
    </div>

    <!-- 模型类型筛选 -->
    <div class="type-filter">
      <el-radio-group v-model="selectedType" @change="filterModels">
        <el-radio-button label="">全部</el-radio-button>
        <el-radio-button 
          v-for="type in modelTypes" 
          :key="type.id" 
          :label="type.id"
        >
          {{ type.icon }} {{ type.description }} ({{ type.count }})
        </el-radio-button>
      </el-radio-group>
    </div>

    <!-- 模型列表 -->
    <div class="models-grid">
      <el-card 
        v-for="model in filteredModels" 
        :key="model.id" 
        class="model-card"
        :class="{ 'is-loaded': model.status === 'loaded' }"
      >
        <div class="model-header">
          <div class="model-icon" :style="{ background: getTypeColor(model.type) }">
            {{ getTypeIcon(model.type) }}
          </div>
          <div class="model-info">
            <h3>{{ model.name }}</h3>
            <el-tag size="small" :type="model.file_exists ? 'success' : 'danger'">
              {{ model.file_exists ? '文件存在' : '文件缺失' }}
            </el-tag>
            <el-tag v-if="model.status === 'loaded'" type="success" size="small">
              已加载
            </el-tag>
          </div>
        </div>
        
        <div class="model-details">
          <div class="detail-item">
            <span class="label">类型:</span>
            <span class="value">{{ model.type }}</span>
          </div>
          <div class="detail-item">
            <span class="label">大小:</span>
            <span class="value">{{ model.size }}</span>
          </div>
          <div class="detail-item">
            <span class="label">量化:</span>
            <span class="value">{{ model.quantization }}</span>
          </div>
          <div class="detail-item">
            <span class="label">上下文:</span>
            <span class="value">{{ formatContext(model.max_context) }}</span>
          </div>
          <div class="detail-item">
            <span class="label">后端:</span>
            <span class="value">{{ model.backend }}</span>
          </div>
        </div>
        
        <div class="model-tags">
          <el-tag v-for="tag in model.tags" :key="tag" size="small" type="info">
            {{ tag }}
          </el-tag>
        </div>
        
        <p class="model-desc">{{ model.description }}</p>
        
        <div class="model-actions">
          <el-button 
            v-if="model.status !== 'loaded'" 
            type="primary" 
            :loading="loadingModel === model.id"
            :disabled="!model.file_exists"
            @click="loadModel(model)"
          >
            加载模型
          </el-button>
          <el-button 
            v-else 
            type="danger" 
            plain
            @click="unloadModel(model)"
          >
            卸载模型
          </el-button>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useModelStore } from '@/stores/models'
import { storeToRefs } from 'pinia'
import { ElMessage } from 'element-plus'
import { Back, Refresh } from '@element-plus/icons-vue'

const modelStore = useModelStore()
const { models, modelTypes, loading } = storeToRefs(modelStore)

const selectedType = ref('')
const loadingModel = ref(null)

// 筛选后的模型
const filteredModels = computed(() => {
  if (!selectedType.value) return models.value
  return models.value.filter(m => m.type === selectedType.value)
})

// 获取类型图标
function getTypeIcon(type) {
  const typeInfo = modelTypes.value.find(t => t.id === type)
  return typeInfo?.icon || '📦'
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

// 筛选模型
function filterModels() {
  // 自动触发 computed 更新
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
  background: #f5f7fa;
  padding: 24px;
}

.page-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 24px;
  
  h1 {
    margin: 0;
    flex: 1;
  }
}

.type-filter {
  margin-bottom: 24px;
}

.models-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 20px;
}

.model-card {
  transition: transform 0.2s, box-shadow 0.2s;
  
  &:hover {
    transform: translateY(-4px);
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1);
  }
  
  &.is-loaded {
    border-color: #67c23a;
  }
}

.model-header {
  display: flex;
  gap: 16px;
  margin-bottom: 16px;
  
  .model-icon {
    width: 48px;
    height: 48px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 24px;
    border-radius: 12px;
    color: #fff;
  }
  
  .model-info {
    flex: 1;
    
    h3 {
      margin: 0 0 8px 0;
      font-size: 16px;
    }
  }
}

.model-details {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
  margin-bottom: 12px;
  padding: 12px;
  background: #f5f7fa;
  border-radius: 8px;
  
  .detail-item {
    display: flex;
    gap: 8px;
    
    .label {
      color: #909399;
      font-size: 12px;
    }
    
    .value {
      font-size: 12px;
      color: #606266;
    }
  }
}

.model-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-bottom: 12px;
}

.model-desc {
  color: #606266;
  font-size: 13px;
  line-height: 1.5;
  margin: 0 0 16px 0;
}

.model-actions {
  display: flex;
  gap: 8px;
}
</style>
