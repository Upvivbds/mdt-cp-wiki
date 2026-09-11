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


def main():
    units = load('units.json')
    blocks = load('buildings.json')

    nu = write_unit_pages(units)
    nb = write_block_pages(blocks)
    write_index_pages(units, blocks)

    print(f'单位页 {nu} 个 + 索引 -> {UNIT_PAGE_DIR}')
    print(f'建筑页 {nb} 个 + 索引 -> {BLOCK_PAGE_DIR}')
    print(f'数据 -> {UNIT_DATA_DIR} / {BLOCK_DATA_DIR}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
