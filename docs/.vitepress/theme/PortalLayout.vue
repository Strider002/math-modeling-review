<script setup>
import DefaultTheme from 'vitepress/theme'
import { useData, withBase } from 'vitepress'
import { computed } from 'vue'
import portal from '../portal.json'
import FigureFinder from './FigureFinder.vue'

const { frontmatter, site } = useData()
const current = computed(() => portal.sites.find(s => s.repository === site.value.base.split('/').filter(Boolean)[0]))
const currentId = computed(() => current.value?.id)
</script>

<template>
  <DefaultTheme.Layout>
    <template #home-hero-info-before>
      <div class="edition-label">CUMCM / MCM / ICM · OPEN KNOWLEDGE</div>
    </template>
    <template #home-features-after>
      <section class="portal-section" aria-label="两个独立 Skill">
        <div class="section-kicker">ONE NAVIGATION, TWO INDEPENDENT SKILLS</div>
        <h2>从建立模型，到让结论经得起检验。</h2>
        <div class="skill-cards">
          <a v-for="(entry, index) in portal.sites" :key="entry.id" class="skill-card"
             :href="entry.id === currentId ? withBase('/') : `${portal.origin}/${entry.repository}/`">
            <span class="card-number">0{{ index + 1 }}</span>
            <div><span class="card-status">{{ entry.id === currentId ? '当前 Skill' : '独立 Skill · 切换阅读' }}</span>
              <h3>{{ entry.label }} <span aria-hidden="true">↗</span></h3>
              <p>{{ entry.description }}</p><code>{{ entry.id }}</code>
            </div>
          </a>
        </div>
        <p class="portal-note">同一套导航，独立仓库、独立下载。以真实证据为基础，不承诺奖项或模型效果。</p>
      </section>
    </template>
    <template #doc-before>
      <div class="document-context"><span class="context-dot"></span>{{ current?.label }}<span class="context-separator">/</span>公开知识与工具</div>
      <FigureFinder v-if="frontmatter.figureFinder" />
    </template>
  </DefaultTheme.Layout>
</template>
