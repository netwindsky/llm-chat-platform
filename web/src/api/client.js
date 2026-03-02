import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 180000
})

// 请求拦截器
api.interceptors.request.use(
  config => {
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  response => {
    return response.data
  },
  error => {
    console.error('API Error:', error)
    return Promise.reject(error)
  }
)

// API 方法
export const modelApi = {
  // 获取模型列表
  list: (params) => {
    console.log('API call: list', params)
    return api.get('/v1/models/', { params })
  },
  
  // 获取模型类型
  getTypes: () => {
    console.log('API call: getTypes')
    return api.get('/v1/models/types')
  },
  
  // 获取模型详情
  get: (modelId) => {
    console.log('API call: get', modelId)
    return api.get(`/v1/models/${modelId}`)
  },
  
  // 加载模型
  load: (modelId, data) => {
    console.log('API call: load', modelId, data)
    return api.post(`/v1/models/${modelId}/load`, data)
  },
  
  // 卸载模型
  unload: (modelId) => {
    console.log('API call: unload', modelId)
    return api.post(`/v1/models/${modelId}/unload`)
  }
}

export const chatApi = {
  // 发送聊天请求（非流式）
  completions: (data) => {
    console.log('API call: completions', data)
    return api.post('/v1/chat/completions', data)
  },
  
  // 流式聊天
  stream: async function* (data) {
    console.log('API call: stream', data)
    const response = await fetch('/api/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ ...data, stream: true })
    })
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    
    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''
      
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6)
          if (data === '[DONE]') {
            return
          }
          try {
            yield JSON.parse(data)
          } catch (e) {
            console.error('Failed to parse SSE data:', data, e)
          }
        }
      }
    }
  }
}

export const systemApi = {
  // 健康检查
  health: () => api.get('/health'),
  
  // 根路径
  root: () => api.get('/')
}

export default api
