#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 Mindustry 原版贴图复制进站点，并产出一份清单。

为什么需要清单：并非每个条目都有贴图 —— 三个 `-missile` 副单位本身是弹体，
在 `sprites/units/` 下没有对应文件。若组件无条件渲染 `<img>`，这些页面会
请求不存在的图片（404）。所以这里把「实际复制到哪些」写进
`docs/data/sprites.json`，组件据此决定渲染与否。

贴图来源：Mindustry 官方仓库 core/assets-raw/sprites/
    units/<id>.png                    单位主体
    blocks/turrets/<id>/<id>-preview.png  复杂炮塔的拼装预览图
    blocks/turrets/<id>.png           简单炮塔
    blocks/defense/<id>.png           防御建筑
    blocks/walls/<id>[1-4].png        墙体（多帧变体取第一帧）

许可：Mindustry 采用 GPL-3.0，贴图随游戏源码分发。站点「关于」页已注明来源。
"""
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..'))
DOCS = os.path.join(ROOT, 'docs')

SRC_ROOT = os.path.expanduser(
    '~/Downloads/Mindustry-master/core/assets-raw/sprites')
UNIT_SRC = os.path.join(SRC_ROOT, 'units')
BLOCK_SRC = os.path.join(SRC_ROOT, 'blocks')

UNIT_DEST = os.path.join(DOCS, 'public', 'sprites', 'units')
BLOCK_DEST = os.path.join(DOCS, 'public', 'sprites', 'blocks')
MANIFEST = os.path.join(DOCS, 'data', 'sprites.json')


def build_block_index():
    """文件名 -> 所有路径，供兜底挑最浅的那个。"""
    idx = {}
    for root, _, files in os.walk(BLOCK_SRC):
        for f in files:
            if f.endswith('.png'):
                idx.setdefault(f, []).append(os.path.join(root, f))
    return idx


def resolve_block(bid, index):
    for c in (os.path.join(BLOCK_SRC, 'turrets', bid, bid + '-preview.png'),
              os.path.join(BLOCK_SRC, 'turrets', bid + '.png'),
              os.path.join(BLOCK_SRC, 'defense', bid + '.png'),
              os.path.join(BLOCK_SRC, 'walls', bid + '.png')):
        if os.path.exists(c):
            return c
    for i in range(1, 5):
        c = os.path.join(BLOCK_SRC, 'walls', '%s%d.png' % (bid, i))
        if os.path.exists(c):
            return c
    cands = index.get(bid + '.png') or index.get(bid + '-preview.png')
    return min(cands, key=lambda p: p.count('/')) if cands else None


def main():
    if not os.path.isdir(UNIT_SRC):
        print('!! 找不到贴图源目录：%s' % UNIT_SRC)
        return 1

    units = json.load(open(os.path.join(DOCS, 'public', 'data', 'units.json'),
                           encoding='utf-8'))
    blocks = json.load(open(os.path.join(DOCS, 'public', 'data', 'buildings.json'),
                            encoding='utf-8'))

    for d in (UNIT_DEST, BLOCK_DEST):
        os.makedirs(d, exist_ok=True)
        for f in os.listdir(d):
            os.remove(os.path.join(d, f))

    unit_have, unit_miss = [], []
    for u in units:
        src = os.path.join(UNIT_SRC, u['id'] + '.png')
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(UNIT_DEST, u['id'] + '.png'))
            unit_have.append(u['id'])
        else:
            unit_miss.append(u['id'])

    block_index = build_block_index()
    block_have, block_miss = [], []
    for b in blocks:
        src = resolve_block(b['id'], block_index)
        if src:
            shutil.copy2(src, os.path.join(BLOCK_DEST, b['id'] + '.png'))
            block_have.append(b['id'])
        else:
            block_miss.append(b['id'])

    os.makedirs(os.path.dirname(MANIFEST), exist_ok=True)
    with open(MANIFEST, 'w', encoding='utf-8') as f:
        json.dump({'units': sorted(unit_have), 'blocks': sorted(block_have)},
                  f, ensure_ascii=False, indent=1)

    size = sum(os.path.getsize(os.path.join(r, f))
               for r, _, fs in os.walk(os.path.join(DOCS, 'public', 'sprites'))
               for f in fs)
    nfile = sum(len(fs) for _, _, fs in os.walk(os.path.join(DOCS, 'public', 'sprites')))

    print('单位贴图 %d/%d' % (len(unit_have), len(units)))
    print('建筑贴图 %d/%d' % (len(block_have), len(blocks)))
    if unit_miss:
        print('  单位无贴图: %s' % unit_miss)
    if block_miss:
        print('  建筑无贴图: %s' % block_miss)
    print('合计 %d 文件 / %.0f KB' % (nfile, size / 1024))
    print('清单 -> %s' % MANIFEST)
    return 0


if __name__ == '__main__':
    sys.exit(main())
