---
title: 关于
---

# 关于

这个站点把 Mindustry 数据包 `整合 (15).hjson` 的内容整理成可浏览的图鉴。

## 数据来源

| 环节 | 来源 |
| --- | --- |
| 数据包改动 | `整合 (15).hjson`（9613 行），拆分为 59 单位 / 57 建筑 |
| 原版数值 | Mindustry 官方源码 `UnitTypes.java`（64 个单位） |
| 中文名称 | 官方语言包 `bundle_zh_CN.properties` |
| DPS 公式 | `Weapon.java`、`ShootPattern.java`、`PointLaserBulletType.java` |

站点数据产物：

- `docs/public/data/units.json` —— 每个单位的完整记录，含 `stats`、`vanillaStats`、`weapons`、`abilities`、`raw`
- `docs/public/data/buildings.json` —— 每个建筑的完整记录
- `docs/public/data/index.json` —— 紧凑索引：分类、作者、星级、DPS 排序

数值对比的原理是：把数据包的补丁合并到**原版单位数据**上，得到「合并后」与「原版」两套数值，二者相减即为改动量。因此属性表中的「原版」列指的是 Mindustry 原版（vanilla）对应单位的数值；数据包新增的、原版不存在的单位则没有可比的原版值，会显示为 `—`。

## DPS 怎么算的

常规武器每扣一次扳机打出 `shots` 发，随后进入 `reload` tick 的冷却：

```
DPS = shots × damage × 60 / reload
```

持续光束（`PointLaserBulletType` 等）不吃 `reload`，按 `damageInterval` 结算：

```
DPS = damage / damageInterval × 60
```

- `reload` 的单位是 **tick**，60 tick = 1 秒；`shots` 缺失时按 1 计。
- **溅射伤害（`splashDamage`）不计入单体 DPS**，单独列出。
- **对空 DPS** 只累加 `collidesAir` 为真的武器，**对地 DPS** 同理。

以下不计入 DPS，只列单发伤害：

- 死亡触发的爆炸弹头（`shootOnDeath`）
- 导弹本体等副单位（`MissileUnitType`）
- 点防御武器、维修 / 建造 / 采矿武器

单位详情页的 DPS 面板提供一个计算器，可以调整射速倍率与伤害倍率实时重算，方便做「如果改成这样会怎样」的推演。

## 作者划分

- **UT** —— 赛普罗（Serpulo）线，原版单位数值再平衡
- **UP** —— 埃里克尔（Erekir）线，系统化设计

## 免责

- 本站为玩家自发整理的**非官方**资料站，与 Mindustry 官方及其开发团队无关。
- 数值由脚本从 hjson 与 Java 源码自动解析，个别字段（尤其依赖循环变量或复杂表达式的）可能无法静态求值，此时该武器只列单发伤害、不报 DPS。以游戏内实际表现为准。
- 数值与描述版权归各自数据包作者所有；本站仅作整理与展示之用。