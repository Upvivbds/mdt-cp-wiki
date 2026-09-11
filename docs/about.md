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

单发伤害不只有主弹，还包含这些派生伤害（递归累加，深度上限 3 层）：

| 来源 | 规则 | 归入 |
| --- | --- | --- |
| 分裂子母弹 `fragBullet` | `fragBullets` × 子弹出伤 | 按子弹出伤性质 |
| 电弧 `lightning` | `lightning` × `lightningDamage`；该字段为负时取主弹伤害 | 范围 |
| 间隔弹 `intervalBullet` | `intervalBullets` × ⌊(`lifetime` − `intervalDelay`) / `bulletInterval`⌋ × 间隔弹出伤 | 按间隔弹出伤性质 |

- **电弧会同时命中多个目标**，所以计入范围而非单体。它按原版的
  `BulletType.hit()` 逻辑在命中点派生，条数即 `lightning`。
- **间隔弹按「寿命内全部生成且全部命中」计**，是理论上限；实战中子弹可能
  在生成出全部间隔弹之前就打空了。`bulletInterval` 缺省 20 tick。
- **穿透（`pierce` / `pierceCap`）不计入 DPS** —— 它让同一发子弹命中更多
  目标，不增加对单个目标的伤害。页面只展示穿透参数，不做折算：
  `pierce` 是布尔值，`pierceCap` 是穿透上限，而 `pierceDamageFactor` 的语义是
  「每穿透一点生命值降低的伤害倍率」（默认 0），并非逐目标衰减系数。

以下不计入 DPS，只列单发伤害：

- 死亡触发的爆炸弹头（`shootOnDeath`），即「殉爆」类单位（爬虫等）
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
## 素材来源与许可

单位与建筑的图标取自 Mindustry 官方仓库：

- 单位：`core/assets-raw/sprites/units/<id>.png`
- 建筑：`core/assets-raw/sprites/blocks/`（炮塔的拼装预览图、墙体等）

Mindustry 以 **GPL-3.0** 许可发布，贴图随源码一同分发。本站是数据包的非官方
资料站，贴图仅用于标识对应游戏内容，版权归 Mindustry 开发者所有。

并非每个条目都有贴图：三个 `-missile` 副单位本身是弹体，游戏中没有独立图标，
对应页面因此不显示图片。贴图清单由 `tools/fetch_sprites.py` 生成，
存在 `docs/data/sprites.json`，组件据此决定是否渲染 `<img>`。

## 重新生成站点

```bash
python3 tools/merge_and_dps.py        # 解析数据包 + 原版源码 → 数据
python3 tools/parse_status_effects.py # 采集 status.* 状态效果 → 数据
python3 tools/fetch_sprites.py        # 复制贴图 + 生成清单
python3 tools/gen_pages.py            # 生成 59 单位页 + 57 建筑页 + 状态效果页
npm run build                         # 构建到 docs/.vitepress/dist
```

校验工具：

```bash
python3 tools/audit_components.py   # 组件静态体检：未声明标识符、断掉的 import、未注册组件
python3 tools/check_links.py        # 全站链接完整性（起临时服务器逐个请求）
python3 tools/check_links.py --base /<仓库名>/   # 同上，但按 Pages 的 /<repo>/ 前缀验
python3 tools/audit_dps.py          # DPS 审计：逐武器明细与可疑项
python3 tools/audit_dps.py 天蝎 龙王  # 只看指定单位
```

开发期用来「看一眼数据长什么样」的一次性脚本在 `tools/dev/`，不参与构建，
详见该目录的 README。

> **改了组件里的链接或贴图路径，务必用 `--base` 再验一次。**
> GitHub Pages 挂在 `/<仓库名>/` 下，而本地默认构建的 base 是 `/` ——
> 少一段前缀的链接在本地完全正常，上线就是 404。`--base` 模式会强制要求
> 前缀存在（和 Pages 行为一致），缺前缀的链接会被判为 404。
