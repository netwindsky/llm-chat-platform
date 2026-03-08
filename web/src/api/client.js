import axios from 'axios'
import logger from '../utils/logger.js'

const api = axios.create({
  baseURL: '/api',
  timeout: 180000
})

// 请求拦截器
api.interceptors.request.use(
  config => {
    // 添加请求ID到头部
    config.headers['X-Frontend-Request-ID'] = generateRequestId()
    return config
  },
  error => {
    logger.error('API Request Error', error)
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  response => {
    const duration = response.config.metadata?.duration || 0
    const frontendRequestId = response.config.headers['X-Frontend-Request-ID']
    const backendRequestId = response.headers['x-request-id']
    
    logger.logResponse(
      response.config.method.toUpperCase(),
      response.config.url,
      response.status,
      duration,
      backendRequestId || frontendRequestId,
      response.data
    )
    
    return response.data
  },
  error => {
    logger.error('API Response Error', error, {
      url: error.config?.url,
      method: error.config?.method
    })
    return Promise.reject(error)
  }
)

// 生成请求ID
function generateRequestId() {
  return `fe_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
}

// API 方法
export const modelApi = {
  // 获取模型列表
  list: (params) => {
    logger.logRequest('GET', '/v1/models/', params)
    return api.get('/v1/models/', { params })
  },
  
  // 获取模型类型
  getTypes: () => {
    logger.logRequest('GET', '/v1/models/types')
    return api.get('/v1/models/types')
  },
  
  // 获取模型详情
  get: (modelId) => {
    logger.logRequest('GET', `/v1/models/${modelId}`)
    return api.get(`/v1/models/${modelId}`)
  },
  
  // 加载模型
  load: (modelId, data) => {
    logger.logRequest('POST', `/v1/models/${modelId}/load`, data)
    return api.post(`/v1/models/${modelId}/load`, data)
  },
  
  // 卸载模型
  unload: (modelId) => {
    logger.logRequest('POST', `/v1/models/${modelId}/unload`)
    return api.post(`/v1/models/${modelId}/unload`)
  }
}

export const chatApi = {
  // 发送聊天请求（非流式）
  completions: (data) => {
    const requestId = generateRequestId()
    logger.logRequest('POST', '/v1/chat/completions', data, requestId)
    
    const startTime = Date.now()
    return api.post('/v1/chat/completions', data, {
      metadata: { startTime }
    }).then(response => {
      const duration = Date.now() - startTime
      logger.logResponse('POST', '/v1/chat/completions', 200, duration, requestId, response)
      return response
    })
  },
  
  // 流式聊天
  stream: async function* (data) {
    const frontendRequestId = generateRequestId()
    const startTime = Date.now()
    
    logger.logRequest('POST', '/v1/chat/completions', { ...data, stream: true }, frontendRequestId)
    
    try {
      const response = await fetch('/api/v1/chat/completions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Frontend-Request-ID': frontendRequestId
        },
        body: JSON.stringify({ ...data, stream: true })
      })
      
      const backendRequestId = response.headers.get('X-Request-ID')
      logger.info(`Request ID mapping: Frontend=${frontendRequestId}, Backend=${backendRequestId}`)
      
      if (!response.ok) {
        const error = new Error(`HTTP error! status: ${response.status}`)
        logger.error('Stream request failed', error, { 
          status: response.status,
          frontendRequestId,
          backendRequestId 
        })
        throw error
      }
      
      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let chunkCount = 0
      
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const dataStr = line.slice(6)
            if (dataStr === '[DONE]') {
              const duration = Date.now() - startTime
              logger.logStreamComplete(backendRequestId || frontendRequestId, chunkCount, duration)
              logger.flush() // 立即刷新日志
              return
            }
            try {
              const parsed = JSON.parse(dataStr)
              chunkCount++
              
              const delta = parsed.choices?.[0]?.delta || {}
              logger.logStreamChunk(
                backendRequestId || frontendRequestId,
                chunkCount,
                !!delta.content,
                !!(delta.thinking || delta.reasoning_content)
              )
              
              yield parsed
            } catch (e) {
              logger.error('Failed to parse SSE data', e, { data: dataStr })
            }
          }
        }
      }
    } catch (error) {
      const duration = Date.now() - startTime
      logger.error(`Stream error after ${duration}ms`, error, { frontendRequestId })
      logger.flush()
      throw error
    }
  }
}

export const systemApi = {
  // 健康检查
  health: () => {
    logger.logRequest('GET', '/health')
    return api.get('/health')
  },
  
  // 根路径
  root: () => {
    logger.logRequest('GET', '/')
    return api.get('/')
  }
}

export default api
