import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

const THEME_KEY = 'md-theme'

const themes = {
  gold: {
    name: '金色阳光',
    strong: '#fbbf24',
    em: '#60a5fa',
    del: '#f87171'
  },
  neon: {
    name: '霓虹炫彩',
    strong: '#00ff88',
    em: '#ff00ff',
    del: '#ff3366'
  },
  ocean: {
    name: '海洋蓝',
    strong: '#22d3ee',
    em: '#a78bfa',
    del: '#f472b6'
  },
  sunset: {
    name: '日落橙',
    strong: '#fb923c',
    em: '#818cf8',
    del: '#e879f9'
  },
  forest: {
    name: '森林绿',
    strong: '#4ade80',
    em: '#2dd4bf',
    del: '#fb7185'
  },
  rose: {
    name: '玫瑰粉',
    strong: '#fb7185',
    em: '#a78bfa',
    del: '#94a3b8'
  }
}

export const useThemeStore = defineStore('theme', () => {
  const currentTheme = ref(localStorage.getItem(THEME_KEY) || 'gold')
  
  function setTheme(themeId) {
    if (themes[themeId]) {
      currentTheme.value = themeId
      localStorage.setItem(THEME_KEY, themeId)
      applyTheme(themes[themeId])
    }
  }
  
  function applyTheme(theme) {
    const root = document.documentElement
    root.style.setProperty('--md-strong', theme.strong)
    root.style.setProperty('--md-em', theme.em)
    root.style.setProperty('--md-del', theme.del)
  }
  
  function getThemes() {
    return Object.entries(themes).map(([id, theme]) => ({
      id,
      name: theme.name,
      ...theme
    }))
  }
  
  watch(currentTheme, (newTheme) => {
    applyTheme(themes[newTheme])
  }, { immediate: true })
  
  return {
    currentTheme,
    setTheme,
    getThemes
  }
})
