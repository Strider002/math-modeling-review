import test from 'node:test'
import assert from 'node:assert/strict'
import { adaptMarkdown, figureRows, pageId, pageLink, tokenize } from './text.mjs'
import { approvedFiles, safeFile } from './files.mjs'

test('Chinese phrases and English model names are searchable', () => {
  const tokens = tokenize('敏感性分析 回归模型 SHAP MILP PCA')
  for (const token of ['敏感', '感性', '回归', 'shap', 'milp', 'pca']) assert(tokens.includes(token), token)
})
test('stable URLs are distinct and safe', () => {
  assert.match(pageId('references/回归.md'), /^p-[a-f0-9]{16}$/)
  assert.notEqual(pageId('references/回归.md'), pageId('references/回归2.md'))
})
test('formula adaptation preserves inline and fenced code', () => {
  const source = '# Test\n\\[\nx=1\n\\]\n`\\(x\\)`\n```text\n\\(code\\)\n```\n\\(x\\)'
  const result = adaptMarkdown(source, 'a.md', new Set())
  assert(result.includes('$$\nx=1\n$$'))
  assert(result.includes('`\\(x\\)`'))
  assert(result.includes('\\(code\\)'))
  assert(result.endsWith('$x$'))
})
test('approved relative links become stable page links', () => {
  const output = adaptMarkdown('[方法](../b.md#旧锚点)', 'a/c.md', new Set(['b.md']))
  assert.equal(output, `[方法](${pageLink('b.md')})`)
})
test('unapproved links fail closed', () => {
  assert.throws(() => adaptMarkdown('[secret](../../private.md)', 'a/c.md', new Set()))
})
test('source templates cannot become Vue expressions', () => {
  assert.equal(adaptMarkdown('{{secret}}', 'a.md', new Set()), '&#123;&#123;secret&#125;&#125;')
})
test('nested TeX braces are preserved', () => {
  assert.equal(adaptMarkdown('\\(\\frac{\\mathrm{SSE}}{\\mathrm{SST}}\\)', 'a.md', new Set()), '$\\frac{\\mathrm{SSE}}{\\mathrm{SST}}$')
})
test('public source hashes match the approved manifest', () => {
  assert(approvedFiles().length > 40)
})
test('paths cannot escape the repository', () => {
  for (const value of ['../private.txt', '/private.txt', 'C:/private.txt', 'a/../private.txt', 'a\\b']) assert.throws(() => safeFile(value))
})
test('figure rows are derived from the approved master table', () => {
  const source = '| 模型 | 图 | 表 | 条件 |\n|---|---|---|---|\n| OLS | 残差 | 参数 | [回归](a.md)：先验证 |'
  const rows = figureRows(source, 'guides', new Set(['guides/a.md']))
  assert.equal(rows.length, 1)
  assert.equal(rows[0].model, 'OLS')
  assert.equal(rows[0].link, pageLink('guides/a.md'))
  assert.throws(() => figureRows(source, 'guides', new Set()))
})
