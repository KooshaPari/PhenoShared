import { spawn, type ChildProcess } from 'node:child_process'

const DEV_PORT = Number(process.env.DEV_PORT ?? 5173)
export const BASE_URL = process.env.E2E_BASE_URL ?? `http://localhost:${DEV_PORT}`

/**
 * The dev server's stdout/stderr are piped but were never read. An OS pipe
 * buffer holds roughly 64 KiB; once the child writes that much into a pipe
 * nobody is reading, it blocks on write and the dev server wedges mid-run.
 * Draining both pipes into this ring buffer keeps the child unblocked, and
 * retains the most recent output so a timeout can report what the server
 * actually said instead of a bare "did not start in 60s".
 */
const MAX_OUTPUT_BYTES = 64 * 1024
const OUTPUT_TAIL_BYTES = 8 * 1024

class OutputRingBuffer {
  private chunks: Buffer[] = []
  private size = 0

  reset(): void {
    this.chunks = []
    this.size = 0
  }

  append(chunk: Buffer): void {
    this.chunks.push(chunk)
    this.size += chunk.length
    // Drop the oldest bytes once the cap is exceeded.
    while (this.size > MAX_OUTPUT_BYTES && this.chunks.length > 1) {
      this.size -= this.chunks.shift()!.length
    }
    if (this.size > MAX_OUTPUT_BYTES) {
      const only = this.chunks[0]!
      const kept = only.subarray(only.length - MAX_OUTPUT_BYTES)
      this.chunks[0] = kept
      this.size = kept.length
    }
  }

  tail(maxBytes: number = OUTPUT_TAIL_BYTES): string {
    if (this.chunks.length === 0) {
      return ''
    }
    const parts: Buffer[] = []
    let total = 0
    for (let i = this.chunks.length - 1; i >= 0; i -= 1) {
      const chunk = this.chunks[i]!
      parts.unshift(chunk)
      total += chunk.length
      if (total >= maxBytes) {
        break
      }
    }
    const merged = Buffer.concat(parts)
    return merged.subarray(Math.max(0, merged.length - maxBytes)).toString('utf8')
  }
}

let devServer: ChildProcess | undefined
let spawnedByTests = false
let refCount = 0
let spawnError: Error | undefined
const devServerOutput = new OutputRingBuffer()

async function isServerReady(url: string): Promise<boolean> {
  try {
    const res = await fetch(url, { signal: AbortSignal.timeout(2_000) })
    return res.ok || res.status < 500
  } catch {
    return false
  }
}

async function waitForDevServer(): Promise<void> {
  const deadline = Date.now() + 60_000
  while (Date.now() < deadline) {
    // A spawn failure is reported through the 'error' event, which fires on a
    // later tick. Surfacing it here turns "the server never came up" into the
    // real cause instead of an indistinguishable 60s hang.
    if (spawnError) {
      throw spawnError
    }
    if (await isServerReady(BASE_URL)) {
      return
    }
    await new Promise((resolve) => setTimeout(resolve, 500))
  }
  const tail = devServerOutput.tail()
  const detail = tail ? `\n--- dev server output (tail) ---\n${tail}` : ''
  throw new Error(`VitePress dev server did not start in 60s${detail}`)
}

async function startDevServer(): Promise<void> {
  if (process.env.E2E_BASE_URL || (await isServerReady(BASE_URL))) {
    return
  }

  spawnError = undefined
  devServerOutput.reset()
  devServer = spawn('npx', ['vitepress', 'dev', '--port', String(DEV_PORT)], {
    cwd: process.cwd(),
    env: {
      ...process.env,
      NODE_ENV: 'test',
      // Serve the site at base '/'. .vitepress/config.mts derives its base from
      // the Pages environment: in GitHub Actions `base` becomes
      // `/${GITHUB_REPOSITORY basename}/` (i.e. '/PhenoShared/'), while these
      // specs navigate with base-less URLs like `${BASE_URL}/guide/...`.
      // Under a non-root base every non-root request is the wrong URL: VitePress
      // returns the SPA shell and its client router then rewrites the location
      // mid-navigation, so `page.goto` is torn down
      // ('... interrupted by another navigation to .../PhenoShared/...') and the
      // assertions inspect an unhydrated shell. '/' is the only route where the
      // base-prefixed and base-stripped forms coincide, which is exactly why '/'
      // was the only route passing in CI. The a11y rules under test are
      // document-level and independent of the deployment sub-path, so pinning the
      // base to '/' here is correct rather than a workaround.
      GITHUB_ACTIONS: 'false',
      GITHUB_PAGES: 'false',
    },
    stdio: ['ignore', 'pipe', 'pipe'],
  })
  spawnedByTests = true

  // Drain BOTH pipes. Without a reader the child fills the ~64 KiB pipe
  // buffer and blocks forever, wedging the dev server part-way through a run.
  devServer.stdout?.on('data', (chunk: Buffer | string) => {
    devServerOutput.append(typeof chunk === 'string' ? Buffer.from(chunk) : chunk)
  })
  devServer.stderr?.on('data', (chunk: Buffer | string) => {
    devServerOutput.append(typeof chunk === 'string' ? Buffer.from(chunk) : chunk)
  })

  // Capture the spawn error instead of throwing inside the handler: a throw
  // here escapes to the event loop and never reaches waitForDevServer().
  devServer.on('error', (err) => {
    spawnError = err
  })

  await waitForDevServer()
}

export async function acquireDevServer(): Promise<void> {
  refCount += 1
  if (refCount === 1) {
    await startDevServer()
  }
}

export async function releaseDevServer(): Promise<void> {
  refCount -= 1
  if (refCount === 0 && spawnedByTests && devServer) {
    const dying = devServer
    devServer = undefined
    spawnedByTests = false
    // Wait for the child to actually exit before a later startDevServer() can
    // probe the port. Both spec files share one fork (singleFork, no file
    // parallelism), so keyboard.spec.ts's teardown and wcag.spec.ts's setup are
    // back to back: if the dying server is still accepting on 5173 when the next
    // probe runs, isServerReady() returns true and no replacement is spawned.
    const exited = new Promise<void>((resolve) => {
      dying.once('exit', () => resolve())
      setTimeout(resolve, 5000)
    })
    dying.kill('SIGTERM')
    await exited
  }
}
