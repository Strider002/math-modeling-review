<script setup>
import DefaultTheme from 'vitepress/theme'
import { useData } from 'vitepress'
import portal from '../portal.json'
import FigureFinder from './FigureFinder.vue'
import BookHome from './BookHome.vue'
const { frontmatter } = useData()
</script>
<template><DefaultTheme.Layout><template #doc-before>
<BookHome v-if="frontmatter.bookHome" />
<template v-else><div class="document-context"><span>数学建模手册</span><span class="context-separator">/</span><span>{{ portal.version }}</span></div><FigureFinder v-if="frontmatter.figureFinder" /></template>
</template></DefaultTheme.Layout></template>
