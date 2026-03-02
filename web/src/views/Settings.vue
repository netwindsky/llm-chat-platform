<template>
  <div class="settings-container">
    <!-- 顶部导航 -->
    <div class="page-header">
      <el-button @click="$router.push('/')">
        <el-icon><Back /></el-icon>
        返回聊天
      </el-button>
      <h1>系统设置</h1>
    </div>

    <div class="settings-content">
      <el-card>
        <template #header>
          <div class="card-header">
            <span>推理设置</span>
          </div>
        </template>
        
        <el-form label-width="120px">
          <el-form-item label="GPU 层数">
            <el-slider v-model="settings.gpuLayers" :min="0" :max="99" show-input />
          </el-form-item>
          
          <el-form-item label="上下文大小">
            <el-select v-model="settings.contextSize">
              <el-option label="16K" :value="16384" />
              <el-option label="32K" :value="32768" />
              <el-option label="64K" :value="65536" />
              <el-option label="128K" :value="131072" />
            </el-select>
          </el-form-item>
          
          <el-form-item label="默认 Temperature">
            <el-slider v-model="settings.temperature" :min="0" :max="2" :step="0.1" show-input />
          </el-form-item>
          
          <el-form-item label="默认 Top-P">
            <el-slider v-model="settings.topP" :min="0" :max="1" :step="0.05" show-input />
          </el-form-item>
          
          <el-form-item label="默认 Top-K">
            <el-input-number v-model="settings.topK" :min="1" :max="100" />
          </el-form-item>
          
          <el-form-item label="最大生成长度">
            <el-input-number v-model="settings.maxTokens" :min="1" :max="8192" />
          </el-form-item>
        </el-form>
      </el-card>
      
      <el-card class="mt-4">
        <template #header>
          <div class="card-header">
            <span>关于</span>
          </div>
        </template>
        
        <el-descriptions :column="1" border>
          <el-descriptions-item label="版本">1.0.0</el-descriptions-item>
          <el-descriptions-item label="框架">llama.cpp</el-descriptions-item>
          <el-descriptions-item label="API">OpenAI Compatible</el-descriptions-item>
        </el-descriptions>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { Back } from '@element-plus/icons-vue'

const settings = ref({
  gpuLayers: 99,
  contextSize: 32768,
  temperature: 0.7,
  topP: 0.8,
  topK: 20,
  maxTokens: 4096
})
</script>

<style lang="scss" scoped>
.settings-container {
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
  }
}

.settings-content {
  max-width: 800px;
}

.mt-4 {
  margin-top: 16px;
}

.card-header {
  font-weight: bold;
}
</style>
