#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""小样本探针：先看清数据包实际的语法形态，再决定解析器细节。"""
import os, re, collections

ROOT = os.path.expanduser('~/Downloads/数据包单位总览')
FILES = [
    'UT的赛普罗单位补丁包.hjson',
    'UP的埃里克尔单位补丁包.hjson',
    'UT的赛普罗建筑补丁包.hjson',
]

for f in FILES:
    p = os.path.join(ROOT, f)
    if not os.path.exists(p):
        print('!! 缺失', f)
        continue
    lines = open(p, encoding='utf-8').read().split('\n')
    print('=' * 72)
    print('【%s】共 %d 行' % (f, len(lines)))
    # 统计键名形态
    forms = collections.Counter()
    samples = collections.defaultdict(list)
    for i, l in enumerate(lines, 1):
        s = l.strip()
        if not s or s.startswith('//'):
            continue
        m = re.match(r'^([A-Za-z_"][^:]*?)\s*:\s*(.*)$', l)
        if not m:
            continue
        key = m.group(1).strip()
        val = m.group(2).strip()
        if key.startswith('"'):
            form = 'JSON键'
        elif re.match(r'^(unit|block|status)\.', key):
            n_dots = key.count('.')
            if val.startswith('{'):
                form = '点号+块(%d段)' % (n_dots + 1)
            elif val.startswith('['):
                form = '点号+数组'
            else:
                form = '点号=标量(%d段)' % (n_dots + 1)
        elif ':' in key or key in ('name',):
            form = '顶层'
        else:
            form = '其它'
        forms[form] += 1
        if len(samples[form]) < 3:
            samples[form].append((i, l.strip()[:96]))
    for form, n in forms.most_common():
        print('  %-22s %4d' % (form, n))
        for i, s in samples[form]:
            print('        L%-5d %s' % (i, s))
    print()

print('=' * 72)
print('【点号路径的段数分布】')
seg = collections.Counter()
plus = collections.Counter()
idx = collections.Counter()
for f in sorted(os.listdir(ROOT)):
    if not f.endswith('.hjson') or f.startswith('_'):
        continue
    for l in open(os.path.join(ROOT, f), encoding='utf-8'):
        m = re.match(r'^\s*(unit|block|status)\.([A-Za-z0-9_\-]+)\.([^:\s]+)\s*:', l)
        if not m:
            continue
        path = m.group(3)
        seg[len(path.split('.'))] += 1
        if '+' in path:
            plus[f] += 1
        if re.search(r'\.\d+\.', path) or re.search(r'\.\d+$', path):
            idx[f] += 1
print('  段数分布:', dict(sorted(seg.items())))
print()
print('  含 "+" 追加标记的文件:')
for f, n in plus.most_common(10):
    print('     %-44s %d' % (f, n))
print('  含数字下标的文件:')
for f, n in idx.most_common(10):
    print('     %-44s %d' % (f, n))