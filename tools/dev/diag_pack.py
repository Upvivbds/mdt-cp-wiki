#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""查看指定单位在数据包里的实际覆盖路径，以及原版武器。"""
import os, sys, json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hjson_datapack import parse_file

ROOT = os.path.expanduser('~/Downloads/数据包单位总览')
VAN = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'vanilla_units.json'))

PACKS = ['UT的赛普罗单位补丁包.hjson', 'UP的埃里克尔单位补丁包.hjson',
         'UT的赛普罗单位&建筑补丁整合包.hjson']

TARGETS = sys.argv[1:] or ['scepter', 'navanax', 'gamma', 'mace', 'zenith',
                           'anthicus', 'horizon', 'crawler']

van = json.load(open(VAN, encoding='utf-8'))['units']

print('#' * 76)
print('# 原版武器（来自 UnitTypes.java 解析）')
print('#' * 76)
for uid in TARGETS:
    v = van.get(uid)
    ws = (v or {}).get('weapons', [])
    print('【%s】原版 weapons=%d' % (uid, len(ws)))
    for i, w in enumerate(ws):
        b = w.get('bullet') if isinstance(w.get('bullet'), dict) else {}
        print('   [%d] type=%s reload=%r name=%r  bullet.__type=%r dmg=%r splash=%r' % (
            i, w.get('__type'), w.get('reload'), w.get('name'),
            b.get('__type'), b.get('damage'), b.get('splashDamage')))
    if not ws:
        # 打印 body 里所有 weapons.add 的原文
        print('   （无武器；查看源码 weapons.add 片段）')
    print()

print('#' * 76)
print('# 数据包覆盖路径')
print('#' * 76)
for pk in PACKS:
    p = os.path.join(ROOT, pk)
    if not os.path.exists(p):
        continue
    dp = parse_file(p)
    hit = False
    for uid in TARGETS:
        b = dp.get('unit', uid)
        if not b:
            continue
        hit = True
        print('--- %s  /  unit.%s   (%d 条路径)' % (pk, uid, len(b)))
        for path, val in b.items():
            ps = '.'.join(path) if path else '(root)'
            vs = json.dumps(val, ensure_ascii=False)
            if len(vs) > 150:
                vs = vs[:150] + '...'
            print('      %-56s %s' % (ps, vs))
    if hit:
        print()