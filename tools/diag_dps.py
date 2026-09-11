#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""诊断 DPS 异常：逐单位打印原版与合并后的 weapons 原始数据。"""
import os, json, sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
DATA = os.path.join(ROOT, 'data')
PUB  = os.path.join(ROOT, 'docs', 'public', 'data')

van = json.load(open(os.path.join(DATA, 'vanilla_units.json'), encoding='utf-8'))['units']
units = json.load(open(os.path.join(PUB, 'units.json'), encoding='utf-8'))
by_id = {u['id']: u for u in units}

SUSPECTS = ['conquer', 'mace', 'nova', 'antumbra', 'horizon', 'mega',
            'reign', 'corvus', 'tecta', 'cleroi', 'anthicus-missile',
            'collaris', 'oct', 'retusa', 'arkyid', 'crawler']

def short(v, n=70):
    s = repr(v)
    return s if len(s) <= n else s[:n] + '...'

for uid in SUSPECTS:
    print('=' * 78)
    print('【%s】' % uid)
    v = van.get(uid)
    if v:
        ws = v.get('weapons', [])
        print('  原版 weapons=%d' % len(ws))
        for i, w in enumerate(ws):
            b = w.get('bullet', {})
            print('    [%d] name=%s __type=%s reload=%s' %
                  (i, w.get('name'), w.get('__type'), w.get('reload')))
            print('        bullet.__type=%s' % b.get('__type'))
            print('        bullet.__args=%s' % short(b.get('__args')))
            nums = {k: b[k] for k in b if not k.startswith('__')}
            print('        bullet nums=%s' % short(nums, 160))
            if 'shoot' in w:
                print('        shoot=%s' % short(w['shoot'], 100))
    else:
        print('  原版：无此单位')

    u = by_id.get(uid)
    if u:
        print('  合并后 dps: total=%s air=%s ground=%s' %
              (u['dps']['total'], u['dps']['air'], u['dps']['ground']))
        for i, w in enumerate(u['weapons']):
            print('    [%d] %s mode=%s reload=%s shots=%s damage=%s dps=%s' %
                  (i, w['name'], w['mode'], w['reload'], w['shots'],
                   w['damage'], w['dps']))
        print('  原始 weapons 键数（合并后 raw）: %d' %
              len(u['raw'].get('weapons', [])))
    print()

print('=' * 78)
print('【抽查：vanilla 里 bullet.__args 含算术表达式的情况】')
cnt = 0
for uid, v in van.items():
    for w in v.get('weapons', []):
        b = w.get('bullet', {})
        args = b.get('__args') or []
        if any(isinstance(a, str) and not a.replace('.', '').replace('-', '').isdigit()
               for a in args):
            # 只有当 damage 缺失时才算问题
            if b.get('damage') is None:
                cnt += 1
                if cnt <= 25:
                    print('  %-18s args=%s  -> damage=%s' %
                          (uid, short(args, 40), b.get('damage')))
print('  合计 %d 处 bullet 构造器参数未能求值且 damage 缺失' % cnt)