#!/usr/bin/env node
// Generates PWA icons (PNG) with no external dependencies.
// Usage: node scripts/generate-icons.mjs

import { mkdirSync, writeFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { deflateSync } from 'node:zlib'

const OUT_DIR = join(dirname(fileURLToPath(import.meta.url)), '..', 'public')

const GRADIENT_A = [91, 91, 214] // #5b5bd6
const GRADIENT_B = [124, 108, 240] // #7c6cf0

// ECG/heartbeat polyline in unit space (-1..1, y down)
const GLYPH = [
  [-1.0, 0],
  [-0.55, 0],
  [-0.32, -0.5],
  [-0.05, 0.75],
  [0.22, -0.62],
  [0.45, 0],
  [1.0, 0],
]

function lerp(a, b, t) {
  return a + (b - a) * t
}

function distToSegment(px, py, x1, y1, x2, y2) {
  const dx = x2 - x1
  const dy = y2 - y1
  const len2 = dx * dx + dy * dy
  let t = len2 > 0 ? ((px - x1) * dx + (py - y1) * dy) / len2 : 0
  t = Math.max(0, Math.min(1, t))
  return Math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))
}

// Signed distance to a rounded rectangle (negative inside)
function sdRoundRect(x, y, w, h, r) {
  const qx = Math.abs(x - w / 2) - (w / 2 - r)
  const qy = Math.abs(y - h / 2) - (h / 2 - r)
  const ox = Math.max(qx, 0)
  const oy = Math.max(qy, 0)
  return Math.hypot(ox, oy) + Math.min(Math.max(qx, qy), 0) - r
}

function render(size, maskable) {
  const rgba = Buffer.alloc(size * size * 4)
  const radius = size * 0.22
  const span = (maskable ? 0.3 : 0.375) * size // glyph half-width
  const stroke = (maskable ? 0.044 : 0.05) * size
  const cx = size / 2
  const cy = size / 2
  const segments = GLYPH.slice(0, -1).map((p, i) => [
    cx + p[0] * span,
    cy + p[1] * span,
    cx + GLYPH[i + 1][0] * span,
    cy + GLYPH[i + 1][1] * span,
  ])

  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      const px = x + 0.5
      const py = y + 0.5

      // Background coverage (1 = inside shape, 0 = transparent)
      let bgCoverage = 1
      if (!maskable) {
        const d = sdRoundRect(px, py, size, size, radius)
        bgCoverage = Math.max(0, Math.min(1, 0.5 - d))
      }
      if (bgCoverage <= 0) {
        rgba[(y * size + x) * 4 + 3] = 0
        continue
      }

      // Diagonal gradient fill
      const t = (x + y) / (2 * (size - 1))
      let r = lerp(GRADIENT_A[0], GRADIENT_B[0], t)
      let g = lerp(GRADIENT_A[1], GRADIENT_B[1], t)
      let b = lerp(GRADIENT_A[2], GRADIENT_B[2], t)

      // Heartbeat glyph (anti-aliased white stroke)
      let dGlyph = Infinity
      for (const [x1, y1, x2, y2] of segments) {
        const d = distToSegment(px, py, x1, y1, x2, y2) - stroke
        if (d < dGlyph) dGlyph = d
      }
      const cov = Math.max(0, Math.min(1, 0.5 - dGlyph))
      if (cov > 0) {
        r = lerp(r, 255, cov)
        g = lerp(g, 255, cov)
        b = lerp(b, 255, cov)
      }

      const i = (y * size + x) * 4
      rgba[i] = Math.round(r)
      rgba[i + 1] = Math.round(g)
      rgba[i + 2] = Math.round(b)
      rgba[i + 3] = Math.round(bgCoverage * 255)
    }
  }
  return rgba
}

// --- Minimal PNG encoder (8-bit RGBA) ---

const CRC_TABLE = (() => {
  const table = new Uint32Array(256)
  for (let n = 0; n < 256; n++) {
    let c = n
    for (let k = 0; k < 8; k++) {
      c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1
    }
    table[n] = c >>> 0
  }
  return table
})()

function crc32(buf) {
  let c = 0xffffffff
  for (let i = 0; i < buf.length; i++) {
    c = CRC_TABLE[(c ^ buf[i]) & 0xff] ^ (c >>> 8)
  }
  return (c ^ 0xffffffff) >>> 0
}

function chunk(type, data) {
  const len = Buffer.alloc(4)
  len.writeUInt32BE(data.length)
  const typeBuf = Buffer.from(type, 'ascii')
  const crc = Buffer.alloc(4)
  crc.writeUInt32BE(crc32(Buffer.concat([typeBuf, data])))
  return Buffer.concat([len, typeBuf, data, crc])
}

function encodePNG(size, rgba) {
  const stride = size * 4 + 1
  const raw = Buffer.alloc(stride * size)
  for (let y = 0; y < size; y++) {
    raw[y * stride] = 0 // filter: none
    rgba.copy(raw, y * stride + 1, y * size * 4, (y + 1) * size * 4)
  }
  const ihdr = Buffer.alloc(13)
  ihdr.writeUInt32BE(size, 0)
  ihdr.writeUInt32BE(size, 4)
  ihdr[8] = 8 // bit depth
  ihdr[9] = 6 // color type RGBA
  return Buffer.concat([
    Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]),
    chunk('IHDR', ihdr),
    chunk('IDAT', deflateSync(raw, { level: 9 })),
    chunk('IEND', Buffer.alloc(0)),
  ])
}

mkdirSync(OUT_DIR, { recursive: true })

const targets = [
  { file: 'icon-192.png', size: 192, maskable: false },
  { file: 'icon-512.png', size: 512, maskable: false },
  { file: 'icon-maskable-512.png', size: 512, maskable: true },
]

for (const { file, size, maskable } of targets) {
  const png = encodePNG(size, render(size, maskable))
  writeFileSync(join(OUT_DIR, file), png)
  console.log(`wrote public/${file} (${size}x${size}, ${png.length} bytes)`)
}
