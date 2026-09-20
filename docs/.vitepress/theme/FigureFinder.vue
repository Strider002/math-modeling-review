<script setup>
import { computed, ref } from 'vue'
import { withBase } from 'vitepress'
import figures from './figures.json'

const query = ref('')
const selected = ref('全部')
const groups = ['全部', ...new Set(figures.map(row => row.group))]
const filtered = computed(() => figures.filter(row =>
  (selected.value === '全部' || row.group === selected.value) &&
  `${row.model} ${row.figure} ${row.table} ${row.condition}`.toLowerCase().includes(query.value.trim().toLowerCase())
))
</script>

<template>
  <section class="figure-finder" aria-label="模型与论文图表筛选">
    <p class="section-kicker">MODEL → EVIDENCE → FIGURE / TABLE</p>
    <h1>模型与论文图表速查</h1>
    <p class="finder-intro">先明确需要支持的主张，再决定使用哪一张图、哪一张表。以下是候选，不是固定交付清单。</p>
    <label for="figure-query" class="field-label">搜索模型、图形或指标</label>
    <input id="figure-query" v-model="query" type="search" placeholder="例如：回归、PCA、混淆矩阵、优化…" autocomplete="off" />
    <div class="filter-tabs" role="group" aria-label="按任务筛选">
      <button v-for="group in groups" :key="group" :aria-pressed="selected === group" @click="selected = group">{{ group }}</button>
    </div>
    <p class="result-count" aria-live="polite">{{ filtered.length }} 项匹配 · 详细字段与适用条件见对应指南</p>
    <div class="figure-results">
      <article v-for="row in filtered" :key="row.model" class="figure-card">
        <span class="group-tag">{{ row.group }}</span><h2>{{ row.model }}</h2>
        <dl><dt>候选图</dt><dd>{{ row.figure }}</dd><dt>配套表</dt><dd>{{ row.table }}</dd><dt>适用条件</dt><dd>{{ row.condition }}</dd></dl>
        <a :href="withBase(row.link)">查看轴、字段与审查点 <span aria-hidden="true">→</span></a>
      </article>
    </div>
    <p v-if="filtered.length === 0" class="empty-state">没有匹配项。可以换一个模型名称，或选择“全部”。</p>
  </section>
</template>
