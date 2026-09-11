#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""定点诊断：为什么这些单位的 damage / reload 是 0。"""
import os, json, sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
VAN = os.path.join(ROOT, 'data', 'vanilla_units.json')
PUB = os.path.join(ROOT, 'docs', 'public', 'data', 'units.json')

van = json.load(open(VAN, encoding='utf-8'))['units']
merged = {u['id']: u for u in json.load(open(PUB, encoding='utf-8'))}

TARGETS = sys.argv[1:] or [
    'horizon', 'crawler', 'anthicus', 'scepter', 'mace',
    'disrupt-missile', 'zenith', 'navanax', 'gamma', 'spike'
]


def brief(w, tag):
    if not isinstance(w, dict):
        print('    %s  不是 dict: %r' % (tag, w))
        return
    b = w.get('bullet') if isinstance(w.get('bullet'), dict) else {}
    print('    %s type=%s reload=%r name=%r' %
          (tag, w.get('__type') or w.get('type'), w.get('reload'), w.get('name')))
    print('         bullet: type=%r __type=%r damage=%r splash=%r '
          'splashRadius=%r damageInterval=%r' % (
              b.get('type'), b.get('__type'), b.get('damage'),
              b.get('splashDamage'), b.get('splashDamageRadius'),
              b.get('damageInterval')))
    if b.get('__args'):
        print('         __args=%r' % (b.get('__args'),))
    if w.get('shoot'):
        print('         shoot=%r' % (w.get('shoot'),))


for uid in TARGETS:
    print('=' * 76)
    print('【%s】' % uid)
    v = van.get(uid)
    if v:
        print('  原版 weapons=%d  keys=%s' % (
            len(v.get('weapons', [])),
            [k for k in v if k not in ('weapons', 'misc')][:12]))
        for i, w in enumerate(v.get('weapons', [])):
            brief(w, '[V%d]' % i)
    else:
        print('  原版：无')

    m = merged.get(uid)
    if m:
        print('  合并后 dps=%s' % m['dps'])
        for i, w in enumerate(m['weapons']):
            print('    [M%d] name=%r bulletType=%r role=%s mode=%s reload=%s '
                  'damage=%s dps=%s' % (
                      i, w['name'], w['bulletType'], w['role'], w['mode'],
                      w['reload'], w['damage'], w['dps']))
    else:
        print('  合并后：无此单位')
    print()

# ---------- 全局：vanilla 里 reload 缺失的 weapon 统计 ----------
print('=' * 76)
print('【全局】原版里 reload 未解析出的武器')
miss = []
for uid, v in van.items():
    for i, w in enumerate(v.get('weapons', [])):
        if not isinstance(w, dict):
            continue
        if w.get('reload') is None:
            b = w.get('bullet') if isinstance(w.get('bullet'), dict) else {}
            miss.append((uid, i, w.get('__type'), b.get('__type'),
                         b.get('damage'), b.get('splashDamage')))
print('  共 %d 个' % len(miss))
for uid, i, wt, bt, dmg, sp in miss[:40]:
    print('    %-18s [%d] %-22s bullet=%-24s dmg=%s splash=%s' %
          (uid, i, wt, bt, dmg, sp))

print()
print('=' * 76)
print('【全局】原版里 damage 与 splashDamage 都是 0/None 的武器')
zero = []
for uid, v in van.items():
    for i, w in enumerate(v.get('weapons', [])):
        if not isinstance(w, dict):
            continue
        b = w.get('bullet') if isinstance(w.get('bullet'), dict) else {}
        d = b.get('damage')
        s = b.get('splashDamage')
        if not d and not s:
            zero.append((uid, i, w.get('__type'), b.get('__type'),
                         b.get('__args'), b.get('__raw')))
print('  共 %d 个' % len(zero))
for uid, i, wt, bt, args, raw in zero[:40]:
    print('    %-18s [%d] %-22s bullet=%-26s args=%s raw=%s' %
          (uid, i, wt, bt, args, (raw or '')[:40]))