<script setup>
import { computed, ref } from 'vue'
import { withBase } from 'vitepress'
import guide from './method-guide.json'
import portal from '../portal.json'
const selected = ref(guide.chapters[0].id)
const branch = ref('table')
const chapter = computed(() => guide.chapters.find(c => c.id === selected.value))
const active = computed(() => selected.value === 'prediction' ? chapter.value.branches[branch.value] : chapter.value)
const choices = [{id:'table',label:'连续数值 / 表格'},{id:'time',label:'未来走势 / 时序'},{id:'discrete',label:'类别、计数或比例'}]
</script>

<template>
  <div class="book-home-content">
    <div class="book-edition"><span>数学建模 · 开放手册</span><span>第二版 / v{{ portal.version }}</span></div>
    <header class="book-intro">
      <p class="book-volume">{{ guide.review ? '卷二 · 审查与论文图表' : '卷一 · 建模方法' }}</p>
      <h1>{{ guide.review ? '让方法与证据相互对应。' : '从问题出发，找到合适的方法。' }}</h1>
      <p>{{ guide.review ? '从已有模型和结论入手，逐项核对验证、解释与图表。' : '先明确你要回答的问题，再阅读方法、比较基线，完成验证。' }}<br>这是一份可以按需翻阅的建模手册。</p>
    </header>
    <section class="method-guide" aria-labelledby="choose-title">
      <div class="chapter-heading"><span>01</span><h2 id="choose-title">{{ guide.review ? '按任务开始审查' : '你想解决什么问题？' }}</h2></div>
      <p class="section-description">选择当前任务，查看阅读起点与需要先确认的条件。</p>
      <div class="task-options" role="group" aria-label="选择任务">
        <button v-for="c in guide.chapters" :key="c.id" type="button" :aria-pressed="selected===c.id" @click="selected=c.id">{{ c.label }}</button>
      </div>
      <fieldset v-if="selected==='prediction'" class="branch-options"><legend>预测对象</legend>
        <label v-for="b in choices" :key="b.id"><input v-model="branch" type="radio" name="prediction-type" :value="b.id">{{ b.label }}</label>
      </fieldset>
      <div class="reading-path" aria-live="polite" aria-atomic="true">
        <div class="reading-path-label">阅读起点</div><h3>{{ active.title }}</h3><p>{{ active.note }}</p>
        <ol><li v-for="(link,i) in active.links" :key="link.href"><span class="reading-step">0{{ i+1 }}</span><a :href="withBase(link.href)">{{ link.label }}<span aria-hidden="true"> →</span></a></li></ol>
        <p class="reading-check"><span>先确认</span>{{ active.check }}</p>
      </div>
      <p class="guide-footnote">这里提供阅读路径。最终选模仍取决于数据结构、假设与同条件验证。</p>
    </section>
    <section class="book-contents" aria-labelledby="contents-title">
      <div class="chapter-heading"><span>02</span><h2 id="contents-title">按章节翻阅</h2></div>
      <div class="contents-list"><a v-for="(c,i) in guide.contents" :key="c.href" :href="withBase(c.href)"><span class="contents-number">{{ String(i+1).padStart(2,'0') }}</span><span><strong>{{ c.label }}</strong><small>{{ c.note }}</small></span><span aria-hidden="true">↗</span></a></div>
    </section>
    <aside class="book-colophon"><p>阅读、比较、验证，再写下结论。</p><div><a :href="withBase('/guide.html')">使用说明</a><span>·</span><a :href="withBase('/download.html')">下载 v{{ portal.version }}</a><span>·</span><a :href="guide.other">{{ guide.review ? '卷一 · 建模方法' : '卷二 · 审查与图表' }} ↗</a></div></aside>
  </div>
</template>
