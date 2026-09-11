/**
 * 通过 CDP 让 Chrome 渲染页面并把截图取回来。
 *
 * 为什么不用 `chrome --headless --screenshot`：
 * 在这台机器（macOS 11.7.11 + Chrome 138）上，任何带 --headless 的 CLI
 * 截图/dump-dom 调用都会在浏览器进程启动阶段 Abort trap: 6，连 data: URL
 * 都撑不住。但一个**已经在跑的** headless 实例配上 --remote-debugging-port
 * 是正常的，于是改走 CDP：让 Chrome 自己渲染、自己截图，再把 PNG 通过
 * WebSocket 送回来。这条路不需要屏幕录制权限。
 *
 * 用法：
 *   node tools/shoot.mjs <url> <out.png> [--width 1440] [--height 900] [--wait 2500] [--full]
 */
import { writeFileSync } from 'node:fs'
import { setTimeout as sleep } from 'node:timers/promises'

const CDP = process.env.CDP || 'http://127.0.0.1:9222'

const args = process.argv.slice(2)
const url = args[0]
const out = args[1]
if (!url || !out) {
  console.error('用法: node tools/shoot.mjs <url> <out.png> [--width N] [--height N] [--wait ms] [--full]')
  process.exit(2)
}

function opt(name, def) {
  const i = args.indexOf('--' + name)
  return i >= 0 && args[i + 1] ? Number(args[i + 1]) : def
}
const WIDTH = opt('width', 1440)
const HEIGHT = opt('height', 900)
const WAIT = opt('wait', 2500)
const FULL = args.includes('--full')

class Cdp {
  constructor(ws) {
    this.ws = ws
    this.id = 0
    this.pending = new Map()
    ws.addEventListener('message', (ev) => {
      let msg
      try { msg = JSON.parse(ev.data) } catch { return }
      if (msg.id && this.pending.has(msg.id)) {
        const { resolve, reject } = this.pending.get(msg.id)
        this.pending.delete(msg.id)
        msg.error ? reject(new Error(JSON.stringify(msg.error))) : resolve(msg.result)
      }
    })
  }

  send(method, params = {}, sessionId) {
    const id = ++this.id
    const payload = { id, method, params }
    if (sessionId) payload.sessionId = sessionId
    this.ws.send(JSON.stringify(payload))
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject })
      setTimeout(() => {
        if (this.pending.has(id)) {
          this.pending.delete(id)
          reject(new Error(`CDP 超时: ${method}`))
        }
      }, 30000)
    })
  }
}

async function main() {
  // 找到浏览器级 WebSocket 端点
  const ver = await fetch(`${CDP}/json/version`).then((r) => r.json())
  const wsUrl = ver.webSocketDebuggerUrl
  if (!wsUrl) throw new Error('拿不到 webSocketDebuggerUrl')

  const ws = new WebSocket(wsUrl)
  await new Promise((res, rej) => {
    ws.addEventListener('open', res, { once: true })
    ws.addEventListener('error', () => rej(new Error('WebSocket 连接失败')), { once: true })
  })

  const cdp = new Cdp(ws)

  // 新建一个标签
  const { targetId } = await cdp.send('Target.createTarget', { url: 'about:blank' })
  const { sessionId } = await cdp.send('Target.attachToTarget', { targetId, flatten: true })

  await cdp.send('Page.enable', {}, sessionId)
  await cdp.send('Runtime.enable', {}, sessionId)
  await cdp.send('Emulation.setDeviceMetricsOverride',
    { width: WIDTH, height: HEIGHT, deviceScaleFactor: 1, mobile: false }, sessionId)

  await cdp.send('Page.navigate', { url }, sessionId)
  await sleep(WAIT)

  // 顺便把可见文本和控制台错误取回来，作为"是否真的渲染成功"的证据
  const textRes = await cdp.send('Runtime.evaluate', {
    expression: 'document.body ? document.body.innerText.slice(0, 4000) : ""',
    returnByValue: true
  }, sessionId)
  const titleRes = await cdp.send('Runtime.evaluate', {
    expression: 'document.title', returnByValue: true
  }, sessionId)

  const shot = await cdp.send('Page.captureScreenshot',
    { format: 'png', captureBeyondViewport: FULL }, sessionId)

  writeFileSync(out, Buffer.from(shot.data, 'base64'))
  console.log(JSON.stringify({
    ok: true,
    url,
    title: titleRes.result && titleRes.result.value,
    out,
    bytes: Buffer.from(shot.data, 'base64').length,
    textPreview: (textRes.result && textRes.result.value || '').slice(0, 600)
  }, null, 1))

  await cdp.send('Target.closeTarget', { targetId })
  ws.close()
}

main().catch((e) => {
  console.error('SHOOT_FAIL:', e.message)
  process.exit(1)
})
