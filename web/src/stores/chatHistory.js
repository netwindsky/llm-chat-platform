import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

// 生成唯一ID
const generateId = () => Date.now().toString(36) + Math.random().toString(36).substr(2)

// 生成对话标题（基于第一条消息）
const generateTitle = (messages) => {
  if (!messages || messages.length === 0) return '新对话'
  const firstUserMessage = messages.find(m => m.role === 'user')
  if (!firstUserMessage) return '新对话'
  const content = firstUserMessage.content
  // 取前20个字符作为标题
  return content.length > 20 ? content.slice(0, 20) + '...' : content
}

export const useChatHistoryStore = defineStore('chatHistory', () => {
  // State
  const conversations = ref([])
  const currentConversationId = ref(null)
  const loading = ref(false)

  // Getters
  const currentConversation = computed(() => {
    return conversations.value.find(c => c.id === currentConversationId.value)
  })

  const sortedConversations = computed(() => {
    return [...conversations.value].sort((a, b) => b.updatedAt - a.updatedAt)
  })

  // Actions
  // 从本地存储加载
  const loadFromStorage = () => {
    try {
      const stored = localStorage.getItem('chat_conversations')
      if (stored) {
        conversations.value = JSON.parse(stored)
      }
    } catch (error) {
      console.error('Failed to load conversations:', error)
    }
  }

  // 保存到本地存储
  const saveToStorage = () => {
    try {
      localStorage.setItem('chat_conversations', JSON.stringify(conversations.value))
    } catch (error) {
      console.error('Failed to save conversations:', error)
    }
  }

  // 新建对话
  const createConversation = () => {
    const newConversation = {
      id: generateId(),
      title: '新对话',
      messages: [],
      model: null,
      createdAt: Date.now(),
      updatedAt: Date.now()
    }
    conversations.value.unshift(newConversation)
    currentConversationId.value = newConversation.id
    saveToStorage()
    return newConversation
  }

  // 设置当前对话
  const setCurrentConversation = (id) => {
    currentConversationId.value = id
  }

  // 更新对话消息
  const updateMessages = (conversationId, messages) => {
    const conversation = conversations.value.find(c => c.id === conversationId)
    if (conversation) {
      conversation.messages = messages
      conversation.updatedAt = Date.now()
      // 如果还没有标题，根据第一条消息生成
      if (conversation.title === '新对话' && messages.length > 0) {
        conversation.title = generateTitle(messages)
      }
      saveToStorage()
    }
  }

  // 更新对话使用的模型
  const updateModel = (conversationId, model) => {
    const conversation = conversations.value.find(c => c.id === conversationId)
    if (conversation) {
      conversation.model = model
      saveToStorage()
    }
  }

  // 删除对话
  const deleteConversation = (id) => {
    const index = conversations.value.findIndex(c => c.id === id)
    if (index > -1) {
      conversations.value.splice(index, 1)
      // 如果删除的是当前对话，切换到第一个对话或清空
      if (currentConversationId.value === id) {
        currentConversationId.value = conversations.value.length > 0 ? conversations.value[0].id : null
      }
      saveToStorage()
    }
  }

  // 重命名对话
  const renameConversation = (id, newTitle) => {
    const conversation = conversations.value.find(c => c.id === id)
    if (conversation) {
      conversation.title = newTitle
      saveToStorage()
    }
  }

  // 清空所有对话
  const clearAllConversations = () => {
    conversations.value = []
    currentConversationId.value = null
    saveToStorage()
  }

  // 获取对话消息
  const getMessages = (conversationId) => {
    const conversation = conversations.value.find(c => c.id === conversationId)
    return conversation ? conversation.messages : []
  }

  // 初始化
  loadFromStorage()

  return {
    conversations,
    currentConversationId,
    currentConversation,
    sortedConversations,
    loading,
    createConversation,
    setCurrentConversation,
    updateMessages,
    updateModel,
    deleteConversation,
    renameConversation,
    clearAllConversations,
    getMessages,
    loadFromStorage,
    saveToStorage
  }
})
