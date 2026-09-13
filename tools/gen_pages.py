#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""为每个单位 / 建筑生成页面，并把数据在**构建期**注入页面。

为什么不用运行时 fetch
----------------------
早期版本让每个详情页在 onMounted 里 fetch('/data/units.json')。这带来三个问题：

1. 首屏 HTML 里没有任何内容 —— 没有 JS 时只看到「正在加载…」，
   搜索引擎抓到的也是空页；
2. 走 file:// 打开时 fetch 会被浏览器的同源策略拦死，页面永远停在加载态；
3. 一旦 JS 报错（曾经真的发生过：loadFile 少导入一个符号被 try/catch 吞掉），
   页面只是"静默空着"，构建期毫无提示。

改成构建期注入后，上述三条一次性消失：数据变成页面的一部分，
首次渲染就是完整内容。

产物
----
    docs/data/units/<id>.json       单个单位的完整记录
    docs/data/buildings/<id>.json   单个建筑的完整记录
    docs/units/<id>.md              引用上面对应 JSON 的页面
    docs/buildings/<id>.md

每个页面只 import 自己那一份，避免把 400KB 的 units.json 灌进每一页。
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..'))
DOCS = os.path.join(ROOT, 'docs')

PUB = os.path.join(DOCS, 'public', 'data')
DATA = os.path.join(DOCS, 'data')

UNIT_PAGE_DIR = os.path.join(DOCS, 'units')
BLOCK_PAGE_DIR = os.path.join(DOCS, 'buildings')
UNIT_DATA_DIR = os.path.join(DATA, 'units')
EFFECT_PAGE_DIR = os.path.join(DOCS, 'effects')
EFFECT_DATA_DIR = os.path.join(DATA, 'effects')
BLOCK_DATA_DIR = os.path.join(DATA, 'buildings')

STAR_LABEL = {'S': '赛普罗', 'E': '埃里克尔'}


def load(name):
    p = os.path.join(PUB, name)
    if not os.path.exists(p):
        p = os.path.join(DATA, name)
    with open(p, encoding='utf-8') as f:
        return json.load(f)


def clean_dir(path, keep=()):
    """只删本脚本生成的文件，保留手写文件。

    曾经这里是无差别清空整个目录，把 `docs/units/index.md`、`docs/buildings/index.md`
    这两个**手写的索引页**一起删了，于是侧边栏指向 /units/ 的链接变成死链，
    构建直接失败（VitePress 的 dead link 检查会拦下来）。
    keep 里的文件名永不删除。
    """
    os.makedirs(path, exist_ok=True)
    keep = set(keep)
    for f in os.listdir(path):
        if f in keep:
            continue
        if f.endswith(('.json', '.md')):
            os.remove(os.path.join(path, f))


def write_unit_pages(units):
    clean_dir(UNIT_PAGE_DIR, keep={'index.md'})
    clean_dir(UNIT_DATA_DIR)

    for u in units:
        uid = u.get('id')
        if not uid:
            continue

        with open(os.path.join(UNIT_DATA_DIR, uid + '.json'), 'w', encoding='utf-8') as f:
            json.dump(u, f, ensure_ascii=False, separators=(',', ':'))

        name = u.get('nameZh') or uid
        sub = ' · '.join(x for x in (
            STAR_LABEL.get(u.get('star'), ''), u.get('categoryLabel'), u.get('author')
        ) if x)

        page = f"""---
title: {name}
---

<script setup>
import unit from '../data/units/{uid}.json'
</script>

<UnitPage :unit="unit" />
"""
        with open(os.path.join(UNIT_PAGE_DIR, uid + '.md'), 'w', encoding='utf-8') as f:
            f.write(page)

    return len(units)


def write_block_pages(blocks):
    clean_dir(BLOCK_PAGE_DIR, keep={'index.md'})
    clean_dir(BLOCK_DATA_DIR)

    for b in blocks:
        bid = b.get('id')
        if not bid:
            continue

        with open(os.path.join(BLOCK_DATA_DIR, bid + '.json'), 'w', encoding='utf-8') as f:
            json.dump(b, f, ensure_ascii=False, separators=(',', ':'))

        name = b.get('nameZh') or bid

        page = f"""---
title: {name}
---

<script setup>
import building from '../data/buildings/{bid}.json'
</script>

<BuildingPage :building="building" />
"""
        with open(os.path.join(BLOCK_PAGE_DIR, bid + '.md'), 'w', encoding='utf-8') as f:
            f.write(page)

    return len(blocks)


def write_effect_pages(effects):
    """状态效果页：一类既不是单位也不是建筑的数据包改动。"""
    clean_dir(EFFECT_PAGE_DIR, keep={'index.md'})
    clean_dir(EFFECT_DATA_DIR)

    for e in effects:
        eid = e.get('id')
        if not eid:
            continue

        with open(os.path.join(EFFECT_DATA_DIR, eid + '.json'), 'w', encoding='utf-8') as f:
            json.dump(e, f, ensure_ascii=False, separators=(',', ':'))

        name = e.get('nameZh') or eid

        page = f"""---
title: {name}
---

<script setup>
import effect from '../data/effects/{eid}.json'
import effects from '../data/effects.json'
</script>

<EffectPage :effect="effect" :effects="effects" />
"""
        with open(os.path.join(EFFECT_PAGE_DIR, eid + '.md'), 'w', encoding='utf-8') as f:
            f.write(page)

    return len(effects)


def write_effect_index(effects):
    """状态效果总览页。条目少的时候就是一份列表，不必上组件。"""
    rows = '\n'.join(
        f"- [{e.get('nameZh') or e['id']}](/effects/{e['id']}) —— `status.{e['id']}`"
        + (
            '，修正 ' + '、'.join(
                f"{m['label']} {m['percent']:+.0f}%" for m in (e.get('mods') or [])
            )
            if e.get('mods')
            else ''
        )
        for e in effects
    )

    body = f"""---
title: 状态效果总览
---

# 状态效果总览

共 **{len(effects)}** 条。数据包在 `status.*` 下新增或改写的状态效果。

{rows or '_暂无。_'}

> 原版状态（burning、freezing、wet 等）源自 `ContentStatuses`，本 wiki 只收录
> 数据包动过的部分 —— 但作为「对立状态」出现在页面上时仍会标注出来。
"""

    with open(os.path.join(EFFECT_PAGE_DIR, 'index.md'), 'w', encoding='utf-8') as f:
        f.write(body)


def write_index_pages(units, blocks):
    """重写两个总览索引页。

    这两页由脚本生成而不是手写，理由是：它们是 UnitBrowser / BuildingBrowser
    的挂载点，内容完全由数据驱动，脚本生成可保证永远与数据同步，也不会再被
    clean_dir 误删。
    """
    with open(os.path.join(UNIT_PAGE_DIR, 'index.md'), 'w', encoding='utf-8') as f:
        f.write(f"""---
title: 单位总览
---

# 单位总览

共 **{len(units)}** 个单位。按星球、作者、分类筛选，或直接搜索中文名 / 英文 id。

<UnitBrowser />
""")

    with open(os.path.join(BLOCK_PAGE_DIR, 'index.md'), 'w', encoding='utf-8') as f:
        f.write(f"""---
title: 建筑总览
---

# 建筑总览

共 **{len(blocks)}** 个建筑。数据包对炮塔弹药、墙体等的改动一览。

<BuildingBrowser />
""")


def sync_shared():
    """把共享 JSON 从 public/data 同步到 docs/data。

    VitePress 的 public/ 是原样搬运、不经 Vite 处理的，组件没法在构建期
    import 它；所以共享数据必须在 docs/data/ 下留一份。这份副本以前没人维护，
    一直是上次运行留下的旧值 —— 排行榜、首页目录、单位卡片读的都是它。
    """
    synced = []
    for name in ('index.json', 'sprites.json', 'effects.json', 'items.json'):
        src = os.path.join(PUB, name)
        if not os.path.exists(src):
            continue
        with open(src, encoding='utf-8') as f:
            data = f.read()
        with open(os.path.join(DATA, name), 'w', encoding='utf-8') as f:
            f.write(data)
        synced.append(name)
    return synced


def main():
    units = load('units.json')
    blocks = load('buildings.json')

    effects = load('effects.json')

    nu = write_unit_pages(units)
    nb = write_block_pages(blocks)
    ne = write_effect_pages(effects)
    write_index_pages(units, blocks)
    write_effect_index(effects)

    # 状态效果的对立状态要能互相跳转，所以把整份名单也放到 docs/data 下。
    with open(os.path.join(DATA, 'effects.json'), 'w', encoding='utf-8') as f:
        json.dump(effects, f, ensure_ascii=False, separators=(',', ':'))

    print(f'单位页 {nu} 个 + 索引 -> {UNIT_PAGE_DIR}')
    print(f'建筑页 {nb} 个 + 索引 -> {BLOCK_PAGE_DIR}')
    print(f'状态效果页 {ne} 个 + 索引 -> {EFFECT_PAGE_DIR}')
    shared = sync_shared()
    print(f'共享数据同步 {len(shared)} 份 -> {DATA}: {", ".join(shared)}')
    print(f'数据 -> {UNIT_DATA_DIR} / {BLOCK_DATA_DIR} / {EFFECT_DATA_DIR}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
