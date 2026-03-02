import { defineStore } from 'pinia'
import { ref } from 'vue'
import { chatApi } from '@/api/client'

export const useChatStore = defineStore('chat', () => {
  // 状态
  const messages = ref([])
  const streaming = ref(false)
  const loading = ref(false)
  const error = ref(null)
  
  // Token 统计
  const stats = ref({
    promptTokens: 0,
    completionTokens: 0,
    totalTokens: 0,
    speed: 0,
    responseTime: 0
  })

  // 添加消息
  function addMessage(role, content, thinking = '') {
    messages.value.push({
      role,
      content,
      thinking,
      timestamp: Date.now()
    })
  }

  // 更新最后一条消息
  function updateLastMessage(content) {
    if (messages.value.length > 0) {
      const lastMsg = messages.value[messages.value.length - 1]
      if (lastMsg.role === 'assistant') {
        lastMsg.content = content
      }
    }
  }

  // 更新思考内容
  function updateThinkingMessage(thinking) {
    if (messages.value.length > 0) {
      const lastMsg = messages.value[messages.value.length - 1]
      if (lastMsg.role === 'assistant') {
        lastMsg.thinking = thinking
      }
    }
  }

  // 发送消息（支持流式和非流式）
  async function sendMessage(modelId, content, config = {}) {
    console.log('sendMessage called:', modelId, content, config)
    loading.value = true
    error.value = null
    
    // 添加用户消息
    addMessage('user', content)
    
    const userMessages = messages.value.map(m => ({
      role: m.role,
      content: m.content
    }))
    
    const useStream = config.stream !== false  // 默认使用流式
    
    try {
      const startTime = Date.now()
      
      if (useStream) {
        // 流式响应
        console.log('Using stream mode')
        streaming.value = true
        
        // 预先添加空的助手消息
        addMessage('assistant', '')
        
        let fullContent = ''
        let chunkCount = 0
        
        let currentThinking = ''
        
        for await (const chunk of chatApi.stream({
          model: modelId,
          messages: userMessages,
          temperature: config.temperature || 0.7,
          top_p: config.top_p || 0.8,
          max_tokens: config.max_tokens || 8192
        })) {
          chunkCount++
          const delta = chunk.choices?.[0]?.delta || {}
          const content = delta.content || ''
          const thinking = delta.thinking || ''
          
          // 更新消息内容
          if (content) {
            fullContent += content
            updateLastMessage(fullContent)
          }
          
          // 更新思考内容
          if (thinking) {
            currentThinking += thinking
            updateThinkingMessage(currentThinking)
          }
        }
        
        const endTime = Date.now()
        console.log(`Stream completed: ${chunkCount} chunks, ${(endTime - startTime) / 1000}s`)
        
        // 更新统计（流式模式下没有准确的 token 统计）
        stats.value = {
          promptTokens: 0,
          completionTokens: 0,
          totalTokens: 0,
          speed: fullContent.length / ((endTime - startTime) / 1000),
          responseTime: (endTime - startTime) / 1000
        }
        
        return { content: fullContent }
        
      } else {
        // 非流式响应
        console.log('Using non-stream mode')
        
        console.log('Sending to API:', { model: modelId, messages: userMessages })
        
        const response = await chatApi.completions({
          model: modelId,
          messages: userMessages,
          temperature: config.temperature || 0.7,
          top_p: config.top_p || 0.8,
          max_tokens: config.max_tokens || 8192,
          stream: false
        })
        
        console.log('API Response:', response)
        
        const endTime = Date.now()
        
        // 添加助手消息（收到响应后）
        const assistantMessage = response.choices[0].message.content
        addMessage('assistant', assistantMessage)
        
        // 更新统计
        if (response.usage) {
          stats.value = {
            promptTokens: response.usage.prompt_tokens,
            completionTokens: response.usage.completion_tokens,
            totalTokens: response.usage.total_tokens,
            speed: response.usage.completion_tokens / ((endTime - startTime) / 1000),
            responseTime: (endTime - startTime) / 1000
          }
        }
        
        return response
      }
      
    } catch (e) {
      error.value = e.response?.data?.detail || e.message
      // 移除失败的助手消息（如果有的话）
      if (messages.value.length > 0 && messages.value[messages.value.length - 1].role === 'assistant') {
        const lastMsg = messages.value[messages.value.length - 1]
        if (!lastMsg.content) {
          messages.value.pop()
        }
      }
      throw e
    } finally {
      loading.value = false
      streaming.value = false
    }
  }

  // 清空对话
  function clearMessages() {
    messages.value = []
    stats.value = {
      promptTokens: 0,
      completionTokens: 0,
      totalTokens: 0,
      speed: 0,
      responseTime: 0
    }
  }

  return {
    messages,
    streaming,
    loading,
    error,
    stats,
    addMessage,
    updateLastMessage,
    sendMessage,
    clearMessages
  }
})
