/**
 * 前端日志系统
 * 将日志发送到后端保存，便于前后端联调
 */

// 日志级别
const LOG_LEVELS = {
  DEBUG: 0,
  INFO: 1,
  WARN: 2,
  ERROR: 3
}

// 当前日志级别
const CURRENT_LEVEL = LOG_LEVELS.DEBUG

// 日志队列（用于批量发送）
let logQueue = []
let flushTimer = null

/**
 * 发送日志到后端
 */
async function sendLogsToBackend(logs) {
  try {
    await fetch('/api/v1/logs/frontend', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ logs })
    })
  } catch (e) {
    // 如果发送失败，保留在控制台
    console.warn('[Logger] Failed to send logs to backend:', e)
  }
}

/**
 * 刷新日志队列
 */
function flushLogs() {
  if (logQueue.length === 0) return
  
  const logsToSend = [...logQueue]
  logQueue = []
  
  sendLogsToBackend(logsToSend)
}

/**
 * 添加日志到队列
 */
function queueLog(level, message, data = null) {
  const logEntry = {
    timestamp: new Date().toISOString(),
    level,
    message,
    data,
    url: window.location.href,
    userAgent: navigator.userAgent
  }
  
  logQueue.push(logEntry)
  
  // 立即刷新错误日志
  if (level === 'ERROR') {
    flushLogs()
  } else {
    // 批量刷新其他日志
    if (!flushTimer) {
      flushTimer = setTimeout(() => {
        flushLogs()
        flushTimer = null
      }, 5000) // 5秒批量发送
    }
  }
}

/**
 * 日志记录函数
 */
export const logger = {
  debug(message, data) {
    if (CURRENT_LEVEL <= LOG_LEVELS.DEBUG) {
      console.log(`[DEBUG] ${message}`, data || '')
      queueLog('DEBUG', message, data)
    }
  },
  
  info(message, data) {
    if (CURRENT_LEVEL <= LOG_LEVELS.INFO) {
      console.log(`[INFO] ${message}`, data || '')
      queueLog('INFO', message, data)
    }
  },
  
  warn(message, data) {
    if (CURRENT_LEVEL <= LOG_LEVELS.WARN) {
      console.warn(`[WARN] ${message}`, data || '')
      queueLog('WARN', message, data)
    }
  },
  
  error(message, error, data) {
    if (CURRENT_LEVEL <= LOG_LEVELS.ERROR) {
      console.error(`[ERROR] ${message}`, error, data || '')
      queueLog('ERROR', message, {
        error: error?.message || error,
        stack: error?.stack,
        ...data
      })
    }
  },
  
  /**
   * 记录 API 请求
   */
  logRequest(method, url, data, requestId) {
    this.info(`API Request: ${method} ${url}`, {
      type: 'api_request',
      method,
      url,
      requestId,
      data: this._sanitizeData(data)
    })
  },
  
  /**
   * 记录 API 响应
   */
  logResponse(method, url, status, duration, requestId, data) {
    this.info(`API Response: ${method} ${url} ${status} ${duration}ms`, {
      type: 'api_response',
      method,
      url,
      status,
      duration,
      requestId,
      data: this._sanitizeData(data)
    })
  },
  
  /**
   * 记录流式响应 chunk
   */
  logStreamChunk(requestId, chunkIndex, hasContent, hasThinking) {
    this.debug(`Stream chunk #${chunkIndex}`, {
      type: 'stream_chunk',
      requestId,
      chunkIndex,
      hasContent,
      hasThinking
    })
  },
  
  /**
   * 记录流式响应完成
   */
  logStreamComplete(requestId, chunkCount, duration) {
    this.info(`Stream completed: ${chunkCount} chunks, ${duration}ms`, {
      type: 'stream_complete',
      requestId,
      chunkCount,
      duration
    })
  },
  
  /**
   * 清理敏感数据
   */
  _sanitizeData(data) {
    if (!data || typeof data !== 'object') return data
    
    const sensitive = ['password', 'token', 'api_key', 'secret', 'authorization']
    const sanitized = {}
    
    for (const [key, value] of Object.entries(data)) {
      if (sensitive.some(s => key.toLowerCase().includes(s))) {
        sanitized[key] = '***'
      } else if (typeof value === 'object') {
        sanitized[key] = this._sanitizeData(value)
      } else {
        sanitized[key] = value
      }
    }
    
    return sanitized
  },
  
  /**
   * 立即刷新所有日志
   */
  flush() {
    flushLogs()
  }
}

// 页面卸载时刷新日志
window.addEventListener('beforeunload', () => {
  flushLogs()
})

export default logger
