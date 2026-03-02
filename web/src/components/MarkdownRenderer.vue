<template>
  <div class="markdown-body" v-html="sanitizedHtml"></div>
</template>

<script setup>
import { computed } from 'vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'

const props = defineProps({
  content: {
    type: String,
    default: ''
  },
  isThinking: {
    type: Boolean,
    default: false
  }
})

marked.setOptions({
  breaks: true,
  gfm: true,
  headerIds: false,
  mangle: false
})

function cleanContent(text) {
  if (!text) return ''
  if (props.isThinking) {
    return text
  }
  return text
    .split('\n')
    .filter(line => line.trim().length > 0)
    .join('\n')
    .trim()
}

const sanitizedHtml = computed(() => {
  if (!props.content) return ''
  const cleaned = cleanContent(props.content)
  const rawHtml = marked.parse(cleaned)
  return DOMPurify.sanitize(rawHtml)
})
</script>

<style scoped>
.markdown-body {
  --md-text-primary: #fafafa;
  --md-text-secondary: #a1a1aa;
  --md-text-tertiary: #71717a;
  --md-bg-code: rgba(255, 255, 255, 0.08);
  --md-bg-blockquote: rgba(99, 102, 241, 0.1);
  --md-bg-table: #1c1c1f;
  --md-bg-table-header: #232328;
  --md-border: rgba(255, 255, 255, 0.1);
  --md-accent: #818cf8;
  --md-accent-hover: #6366f1;
  --md-code-pink: #f472b6;
  --md-code-cyan: #67e8f9;
  
  line-height: 1.6;
  color: var(--md-text-primary);
  font-size: 14px;
  padding: 0 25px;
}

.markdown-body :deep(br) {
  display: none !important;
}

.markdown-body :deep(p:empty),
.markdown-body :deep(p br:only-child) {
  display: none !important;
}

.markdown-body :deep(h1),
.markdown-body :deep(h2),
.markdown-body :deep(h3),
.markdown-body :deep(h4),
.markdown-body :deep(h5),
.markdown-body :deep(h6) {
  margin: 15px 0;
  font-weight: 600;
  line-height: 1.4;
  color: var(--md-text-primary);
}

.markdown-body :deep(h1) {
  font-size: 1.5em;
  border-bottom: 1px solid var(--md-border);
  padding-bottom: 4px;
}

.markdown-body :deep(h2) {
  font-size: 1.3em;
  border-bottom: 0px solid var(--md-border);
  padding-bottom: 3px;
}

.markdown-body :deep(h3) {
  font-size: 1.15em;
  color: var(--md-text-secondary);
}

.markdown-body :deep(h3) {
  font-size: 1.15em;
  color: var(--md-text-secondary);
  padding-left: 16px;
}

.markdown-body :deep(h4) {
  font-size: 1.05em;
  padding-left: 32px;
}

.markdown-body :deep(h5) {
  font-size: 1em;
  padding-left: 48px;
}

.markdown-body :deep(h6) {
  font-size: 0.95em;
  padding-left: 64px;
}

.markdown-body :deep(p) {
  margin: 15px 0;
  color: var(--md-text-primary);
}

.markdown-body :deep(h2 + p) {
  padding-left: 16px;
}

.markdown-body :deep(h3 + p) {
  padding-left: 32px;
}

.markdown-body :deep(h4 + p) {
  padding-left: 48px;
}

.markdown-body :deep(h5 + p) {
  padding-left: 64px;
}

.markdown-body :deep(h6 + p) {
  padding-left: 80px;
}

.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  margin: 15px 0;
  padding-left: 24px;
}

.markdown-body :deep(h2 + ul),
.markdown-body :deep(h2 + ol) {
  padding-left: 40px;
}

.markdown-body :deep(h3 + ul),
.markdown-body :deep(h3 + ol) {
  padding-left: 56px;
}

.markdown-body :deep(h4 + ul),
.markdown-body :deep(h4 + ol) {
  padding-left: 72px;
}

.markdown-body :deep(h5 + ul),
.markdown-body :deep(h5 + ol) {
  padding-left: 88px;
}

.markdown-body :deep(h6 + ul),
.markdown-body :deep(h6 + ol) {
  padding-left: 104px;
}

.markdown-body :deep(ul ul),
.markdown-body :deep(ol ol),
.markdown-body :deep(ul ol),
.markdown-body :deep(ol ul) {
  padding-left: 32px;
  margin: 8px 0;
}

.markdown-body :deep(li) {
  margin: 15px 0;
  line-height: 1.5;
  color: var(--md-text-primary);
}

.markdown-body :deep(li > p) {
  margin: 15px 0;
}

.markdown-body :deep(li + li) {
  margin-top: 1px;
}

.markdown-body :deep(code) {
  background-color: var(--md-bg-code);
  padding: 1px 4px;
  border-radius: 3px;
  font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
  font-size: 0.9em;
  color: var(--md-code-pink);
}

.markdown-body :deep(pre) {
  background-color: #0a0a0b;
  padding: 10px;
  border-radius: 6px;
  overflow-x: auto;
  margin: 15px 0;
  border: 1px solid var(--md-border);
}

.markdown-body :deep(pre code) {
  background-color: transparent;
  padding: 0;
  color: var(--md-text-secondary);
  border: none;
  font-size: 13px;
  line-height: 1.5;
}

.markdown-body :deep(blockquote) {
  width: 90%;
  margin: 15px auto;
  padding: 5px 8px;
  border-left: 3px solid var(--md-accent);
  background-color: var(--md-bg-blockquote);
  border-radius: 0 4px 4px 0;
  color: var(--md-text-secondary);
}

.markdown-body :deep(blockquote p) {
  margin: 0;
}

.markdown-body :deep(table) {
  width: 90%;
  border-collapse: collapse;
  margin: 15px auto;
  border-radius: 4px;
  overflow: hidden;
  border: 1px solid var(--md-border);
}

.markdown-body :deep(th),
.markdown-body :deep(td) {
  padding: 6px 10px;
  text-align: left;
  border-bottom: 1px solid var(--md-border);
  color: var(--md-text-primary);
}

.markdown-body :deep(th) {
  background-color: var(--md-bg-table-header);
  font-weight: 600;
}

.markdown-body :deep(td) {
  background-color: var(--md-bg-table);
}

.markdown-body :deep(tr:last-child td) {
  border-bottom: none;
}

.markdown-body :deep(a) {
  color: var(--md-accent);
  text-decoration: none;
}

.markdown-body :deep(a:hover) {
  color: var(--md-accent-hover);
  text-decoration: underline;
}

.markdown-body :deep(hr) {
  border: none;
  border-top: 0px solid var(--md-border);
  margin: 15px 0;
}

.markdown-body :deep(img) {
  max-width: 100%;
  height: auto;
  border-radius: 4px;
}

.markdown-body :deep(strong) {
  color: var(--md-text-primary);
  font-weight: 600;
}

.markdown-body :deep(em) {
  color: var(--md-text-secondary);
}

.markdown-body :deep(del) {
  color: var(--md-text-tertiary);
}

.markdown-body :deep(input[type="checkbox"]) {
  margin-right: 4px;
  accent-color: var(--md-accent);
}
</style>
