import { spawn, type ChildProcess } from 'node:child_process'

const DEV_PORT = Number(process.env.DEV_PORT ?? 5173)
export const BASE_URL = process.env.E2E_BASE_URL ?? `http://localhost:${DEV_PORT}`

let devServer: ChildProcess | undefined
let spawnedByTests = false
let refCount = 0

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
    if (await isServerReady(BASE_URL)) {
      return
    }
    await new Promise((resolve) => setTimeout(resolve, 500))
  }
  throw new Error('VitePress dev server did not start in 60s')
}

async function startDevServer(): Promise<void> {
  if (process.env.E2E_BASE_URL || (await isServerReady(BASE_URL))) {
    return
  }

  devServer = spawn('npx', ['vitepress', 'dev', '--port', String(DEV_PORT)], {
    cwd: process.cwd(),
    env: { ...process.env, NODE_ENV: 'test' },
    stdio: ['ignore', 'pipe', 'pipe'],
  })
  spawnedByTests = true
  devServer.on('error', (err) => {
    throw err
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
    devServer.kill('SIGTERM')
    devServer = undefined
    spawnedByTests = false
  }
}
