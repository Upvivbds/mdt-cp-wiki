---
layout: home

hero:
  name: Mindustry 数据包 Wiki
  text: 单位与建筑图鉴 · 原版数值对比 · DPS 计算
  tagline: 由数据包 hjson 自动解析生成 —— 每个单位的每一处改动、每一门武器的 DPS，都能查到。
  actions:
    - theme: brand
      text: 浏览单位
      link: /units/
    - theme: alt
      text: 查看 DPS 排行
      link: /dps
    - theme: alt
      text: 建筑总览
      link: /buildings/

features:
  - title: 数值逐项对比
    details: 血量、护甲、速度、射程等属性同时列出数据包与原版数值，有改动的高亮并给出增减百分比。
  - title: DPS 明细与计算器
    details: 总 DPS / 对空 / 对地三个口径，逐武器列出装填、发数、单发伤害；还能实时调整倍率重算。
  - title: 能力与原始数据
    details: 力场、状态场、弧形护盾等能力卡片化展示，并保留可折叠的 raw JSON 供深度排查。
---

<StatsCards />

## DPS 排行 Top 10

<TopDps :limit="10" />

## 站点导航

- [单位总览](/units/) —— 按星球、作者、分类筛选，支持搜索与排序
- [建筑总览](/buildings/) —— 数据包改动的建筑条目，含所属补丁包
- [DPS 排行](/dps) —— 全单位 DPS 榜单，可切换对空口径
- [关于本站](/about) —— 数据来源与 DPS 公式出处