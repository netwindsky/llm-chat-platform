import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { modelApi, chatApi } from '@/api/client'

export const useModelStore = defineStore('models', () => {
  // 状态
  const models = ref([])
  const modelTypes = ref([])
  const loadedModels = ref([])
  const currentModel = ref(null)
  const loading = ref(false)
  const error = ref(null)

  // 获取模型列表
  async function fetchModels(params = {}) {
    loading.value = true
    error.value = null
    try {
      const res = await modelApi.list(params)
      models.value = res.models
      
      // 同步 loadedModels 数组 - 只保留实际状态为 loaded 的模型
      const actuallyLoaded = res.models
        .filter(m => m.status === 'loaded')
        .map(m => m.id)
      loadedModels.value = actuallyLoaded
      
      // 如果当前模型不再加载状态，清空 currentModel
      if (currentModel.value && !actuallyLoaded.includes(currentModel.value)) {
        currentModel.value = null
      }
      
      return res
    } catch (e) {
      error.value = e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  // 获取模型类型
  async function fetchTypes() {
    try {
      const res = await modelApi.getTypes()
      modelTypes.value = res.types
      return res
    } catch (e) {
      error.value = e.message
      throw e
    }
  }

  // 加载模型
  async function loadModel(modelId, config = {}) {
    loading.value = true
    error.value = null
    try {
      const res = await modelApi.load(modelId, config)
      console.log('Load model response:', res)
      if (res.success) {
        // 更新模型状态为 loading
        const model = models.value.find(m => m.id === modelId)
        if (model) {
          model.status = 'loading'
        }
        
        // 轮询等待模型完全加载
        await waitForModelLoaded(modelId)
        
        // 重新获取模型列表以更新所有状态
        await fetchModels()
        
        loadedModels.value.push(modelId)
        currentModel.value = modelId
      }
      return res
    } catch (e) {
      console.error('Load model error:', e)
      error.value = e.response?.data?.detail || e.message
      throw e
    } finally {
      loading.value = false
    }
  }
  
  // 轮询等待模型加载完成
  async function waitForModelLoaded(modelId, maxAttempts = 120, interval = 1000) {
    for (let i = 0; i < maxAttempts; i++) {
      await new Promise(resolve => setTimeout(resolve, interval))
      
      try {
        const model = await modelApi.get(modelId)
        if (model.status === 'loaded') {
          console.log(`Model ${modelId} fully loaded`)
          const modelData = models.value.find(m => m.id === modelId)
          if (modelData) {
            modelData.status = 'loaded'
          }
          return true
        } else if (model.status === 'error') {
          throw new Error(`Model ${modelId} loading failed`)
        }
      } catch (e) {
        console.error(`Polling model ${modelId} status error:`, e)
      }
    }
    throw new Error(`Model ${modelId} loading timeout`)
  }

  // 卸载模型
  async function unloadModel(modelId) {
    loading.value = true
    try {
      const res = await modelApi.unload(modelId)
      if (res.success) {
        const index = loadedModels.value.indexOf(modelId)
        if (index > -1) {
          loadedModels.value.splice(index, 1)
        }
        if (currentModel.value === modelId) {
          currentModel.value = loadedModels.value[0] || null
        }
      }
      return res
    } catch (e) {
      error.value = e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  return {
    models,
    modelTypes,
    loadedModels,
    currentModel,
    loading,
    error,
    fetchModels,
    fetchTypes,
    loadModel,
    unloadModel
  }
})
