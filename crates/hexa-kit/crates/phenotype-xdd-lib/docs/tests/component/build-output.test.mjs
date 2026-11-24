import test from 'node:test'
import assert from 'node:assert/strict'
import { existsSync, readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('built output contains the public docs routes', () => {
  const distRoot = resolve(process.cwd(), '.vitepress/dist')
  const expectedFiles = [
    'index.html',
    'guide/index.html',
    'reference/index.html',
    'reference/architecture/index.html',
    'reference/property-testing.html',
    'reference/contract-testing.html',
    'reference/mutation-testing.html',
    'reference/specdd.html',
    'zh-CN/index.html',
    'zh-TW/index.html',
    'fa/index.html',
    'fa-Latn/index.html'
  ]

  for (const relativePath of expectedFiles) {
    assert.equal(existsSync(resolve(distRoot, relativePath)), true, `${relativePath} should exist`)
  }

  const homeHtml = readFileSync(resolve(distRoot, 'index.html'), 'utf8')
  assert.match(homeHtml, /phenotype-xdd-lib/i)
})
