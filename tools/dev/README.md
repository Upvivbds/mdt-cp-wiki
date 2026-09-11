# tools/dev —— 开发期一次性脚本（非管线）

这里放的是解析器开发过程中用来「看一眼数据长什么样」的临时工具，正常维护
站点不需要跑它们。留在这里是为了以后数据包大改、需要重新排查时能直接捡起来，
而不是当场重写。

| 脚本 | 用途 |
| --- | --- |
| `probe_datapack.py` | 粗看某个 hjson 里有什么块、字段长什么样 |
| `diag_pack.py` | 检查数据包文件是否被完整切分（早期分片丢行时用过） |
| `diag_dps.py` | 打印某单位的武器与 bullet 展开，排查 DPS 口径 |
| `diag_weapon_body.py` | 打印 `weapons.add(...)` 的原始 body 文本 |
| `diag_weapons2.py` | 多参数 `weapons.add` 与 `bullet = <var>` 的排查 |
| `shoot.mjs` | CDP 截图工具。**在 up 这台 Big Sur 上跑不了** —— Chrome 138 无头模式直接 `Abort trap: 6`，`screencapture` 也没有录屏权限。换机器后可用 |

正式管线与校验脚本都在上一级 `tools/` 目录，见 `docs/about.md` 的「重新生成站点」。
