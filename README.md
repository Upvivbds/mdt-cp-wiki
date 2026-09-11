# Mindustry 数据包 Wiki

由数据包 hjson 自动解析生成的静态图鉴站点：**每个单位、每个建筑一个独立页面**，逐项与原版数值对比，并内置 DPS 计算器。

## 快速开始

```bash
npm install
npm run build      # 产物在 docs/.vitepress/dist/
npm run preview    # 本地预览
npm run dev        # 开发模式
```

只验证产物能否被静态服务器正确提供：

```bash
cd docs/.vitepress/dist && python3 -m http.server 4175
# 打开 http://127.0.0.1:4175/
```

## 站点结构

| 路径 | 内容 |
|---|---|
| `/` | 首页：数据包统计 + DPS 榜首 |
| `/units/` | 单位总览，按星球 / 作者 / 分类筛选 + 关键词搜索 |
| `/units/{id}` | 单位详情：数值对比、武器明细、DPS 计算、技能、部件 |
| `/buildings/` | 建筑总览 |
| `/buildings/{id}` | 建筑详情：稀疏补丁字段、弹药类型、炮塔射速参考 |
| `/dps` | DPS 排行（总 / 对空 / 对地三种口径） |
| `/about` | 数据来源与解析说明 |

## 架构要点

- **引擎**：VitePress 1.6（Vue 3）。选它是因为 Markdown 驱动 + 单页应用式路由，
  生成上百个详情页的成本极低，且主题可完全接管。
- **数据流**：`tools/` 下的 Python 管线解析数据包 hjson →
  `docs/public/data/*.json` → 构建时复制到 `dist/data/` → 前端运行时 `fetch`。
  `units.json` 约 400KB，因此详情页走运行时加载而非 SSR 内联，换来的是极小的 HTML。
  代价是详情页在没有 JS 时只显示加载态骨架 —— 这是有意的取舍。
- **数值对比**：每个单位都带 `vanillaStats`（原版基准），
  组件逐字段算差值并标注「有改动 / 与原版一致」。
- **DPS 口径**：常规武器 `DPS = shots × damage × 60 / reload`；持续光束另走一条公式。
  提供总 / 单武器 / 对空 / 对地四种视图。

## 数据管线

```bash
python3 tools/merge_and_dps.py    # 解析 + 合并 + 计算 DPS → docs/public/data/
python3 tools/audit_components.py # 组件静态体检（见下）
```

`audit_components.py` 检查三类**构建期不报错、只在运行时静默失效**的问题：

1. `<script setup>` 里用了未导入的符号 —— 运行时 `ReferenceError`，
   被 `try/catch` 吞掉后页面只是「永远空着」。
2. `<template>` 里引用了未声明的名字。
3. 写了 `<Foo />` 但组件没在 `theme/index.ts` 注册 —— VitePress 原样输出标签。

这类问题曾真实发生过两次（首页 DPS 榜永远为空、建筑详情页整体缺失），
所以固化成脚本。改组件后建议跑一次。

## 已知限制

- **无头浏览器验证在本机不可用**：Chrome 138 的 `--dump-dom` 连 `data:` URL 都会
  `Abort trap: 6`。因此前端的「JS 执行后到底渲染出什么」是靠
  ①数据契约静态复算 ②打包 chunk 语法体检 ③SSR 产物抽查 三者等价的，
  而不是真的开浏览器跑过。改动前端后请在真实浏览器里确认一次。
- **副单位（`-missile`）**：其 DPS 语义是「命中即炸」，
  混进榜单会把真正的作战单位全挤下去，因此已从 `topDps` 排除。
- 数据里的空值（如 `ground: 0` 的纯对空单位）按原样显示，不做推测补全。