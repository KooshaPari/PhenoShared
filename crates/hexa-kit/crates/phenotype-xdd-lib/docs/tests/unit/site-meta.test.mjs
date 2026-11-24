import test from 'node:test'
import assert from 'node:assert/strict'

import { getSiteMeta } from '../helpers/site-meta.mjs'

test('site metadata exposes the expected nav and locales', () => {
  const meta = getSiteMeta()

  assert.equal(meta.title, 'phenotype-xdd-lib')
  assert.ok(meta.nav.some((item) => item.text === 'Reference' && item.link === '/reference/'))
  assert.deepEqual(meta.locales.sort(), ['fa', 'fa-Latn', 'zh-CN', 'zh-TW'])
})
