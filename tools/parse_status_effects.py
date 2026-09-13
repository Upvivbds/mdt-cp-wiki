#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""采集数据包新增的「状态效果」(status.*)。

数据包里这一类内容目前只有一条（status.dynamic 「余劫」），但它不是单位也不是
建筑，所以既有的两条解析管线都覆盖不到它。这里单独做一条极小的管线，并且写成
通用的 status 扫描器 —— 将来数据包再加状态效果会自动进来，不用改代码。

产出：
  data/status_effects.json      —— 结构化数据（含被哪些单位/建筑施加）
  docs/public/data/effects.json —— 前端可读的同一份数据

用法：
  python3 tools/parse_status_effects.py
"""

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..'))
SRC_DIR = os.path.expanduser('~/Downloads/数据包单位总览')
SRC_MAIN = os.path.expanduser('~/Downloads/整合 (16).hjson')
PUB = os.path.join(ROOT, 'docs', 'public', 'data')
DATA = os.path.join(ROOT, 'data')

# ---- 数值字段：乘算型的转成人类可读的百分比 ----
MULT_FIELDS = [
    ('healthMultiplier', '生命值'),
    ('speedMultiplier', '移动速度'),
    ('reloadMultiplier', '射速'),
    ('damageMultiplier', '伤害'),
    ('buildSpeedMultiplier', '建造速度'),
    ('dragMultiplier', '阻力'),
]

# ---- 布尔型的开关 ----
# 注意 show 不在这里：它是「游戏内是否显示图标」，默认就是 true，
# 当成特性徽章列出来只会是噪音，改由页面按「不显示时才提示」处理。
BOOL_FIELDS = [
    ('damage', '持续伤害'),
    ('disarm', '缴械'),
    ('permanent', '永久'),
    ('reactive', '反应式'),
]


def strip_block(text, start):
    """从 start 处的 '{' 开始做花括号配对，返回块内文本。"""
    depth = 0
    i = start
    while i < len(text):
        c = text[i]
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                return text[start + 1:i], i + 1
        i += 1
    return text[start + 1:], len(text)


def parse_value(raw):
    """把 hjson 的一行值转成 Python 值。"""
    raw = raw.strip()
    if raw.startswith('[') and raw.endswith(']'):
        inner = raw[1:-1].strip()
        if not inner:
            return []
        return [p.strip().strip('"\'') for p in inner.split(',')]
    if raw in ('true', 'false'):
        return raw == 'true'
    if raw in ('none', 'null'):
        return None
    try:
        if re.fullmatch(r'-?\d+', raw):
            return int(raw)
        if re.fullmatch(r'-?\d*\.\d+', raw):
            return float(raw)
    except ValueError:
        pass
    return raw.strip('"').strip("'")


def collect_status(src):
    """从源文件里抽出所有顶层 status.<id>: { ... } 块。"""
    out = []
    for m in re.finditer(r'^status\.([A-Za-z0-9_]+)\s*:\s*\{', src, re.M):
        sid = m.group(1)
        body, _ = strip_block(src, m.end() - 1)
        fields = {}
        for line in body.splitlines():
            line = line.split('//')[0].rstrip()
            if not line.strip() or ':' not in line:
                continue
            k, _, v = line.partition(':')
            k = k.strip()
            v = v.strip()
            if not k or v == '{':
                continue
            fields[k] = parse_value(v)
        out.append((sid, fields))
    return out


# ---- 反向索引：谁施加了这个状态 ----
OWNER_RE = re.compile(r'^(block|unit)\.([A-Za-z0-9_]+)')


def scan_appliers(want_ids, names):
    """扫所有数据包文件，找出哪些块/单位会给目标状态挂 buff。

    用「认出路径而不是缩进」的老规矩：记住最近一次出现的顶层 block./unit. 前缀，
    之后遇到的 status:/shootStatus: 就归属给它。
    """
    hits = {sid: [] for sid in want_ids}
    for dirpath, _dirnames, filenames in os.walk(SRC_DIR):
        for fn in filenames:
            if not fn.endswith('.hjson'):
                continue
            path = os.path.join(dirpath, fn)
            try:
                with open(path, encoding='utf-8') as f:
                    lines = f.read().splitlines()
            except OSError:
                continue

            owner = None
            for line in lines:
                code = line.split('//')[0]
                # 认路径不认缩进：block./unit. 前缀可能和 status 同行，
                # 所以剥掉前缀后继续往下扫，不能直接 continue。
                om = OWNER_RE.match(code)
                if om:
                    owner = (om.group(1), om.group(2))
                    code = code[om.end():]
                sm = re.search(r'\b(status|shootStatus)\s*:\s*([A-Za-z0-9_]+)', code)
                if not sm:
                    continue
                sid = sm.group(2)
                if sid not in hits:
                    continue
                if owner is None:
                    continue
                entry = names.get((owner[0], owner[1]))
                rec = {
                    'kind': owner[0],
                    'id': owner[1],
                    'nameZh': (entry or {}).get('nameZh') or owner[1],
                    'field': sm.group(1),
                    'file': os.path.relpath(path, SRC_DIR),
                    'depth': path.count(os.sep),
                }
                if rec not in hits[sid]:
                    hits[sid].append(rec)

    # 同一个块往往同时出现在「单文件」和 2~3 个合集包里，按 (kind,id,字段) 去重，
    # 保留路径最深的那份（即最具体的那份文件），避免同一个施加者重复出现。
    for sid, recs in hits.items():
        best = {}
        for r in recs:
            key = (r['kind'], r['id'], r['field'])
            if key not in best or r['depth'] > best[key]['depth']:
                best[key] = r
        dedup = sorted(best.values(), key=lambda r: (r['kind'], r['id']))
        for r in dedup:
            r.pop('depth', None)
        hits[sid] = dedup
    return hits


def load_index():
    """把已生成的单位/建筑数据读进来，用于 id -> 中文名 映射。"""
    names = {}
    for kind, fname in (('unit', 'units.json'), ('block', 'buildings.json')):
        p = os.path.join(PUB, fname)
        if not os.path.exists(p):
            continue
        with open(p, encoding='utf-8') as f:
            for item in json.load(f):
                names[(kind, item.get('id'))] = item
    return names


def humanize(fields):
    """把乘算字段整理成给人看的 修正 列表。"""
    mods = []
    for key, label in MULT_FIELDS:
        v = fields.get(key)
        if isinstance(v, (int, float)) and v != 1:
            mods.append({
                'key': key,
                'label': label,
                'value': v,
                'percent': round((v - 1) * 100, 2),
            })
    flags = []
    for key, label in BOOL_FIELDS:
        v = fields.get(key)
        if isinstance(v, bool) and v:
            flags.append({'key': key, 'label': label})
    return mods, flags


def main():
    if not os.path.exists(SRC_MAIN):
        print(f'找不到源文件: {SRC_MAIN}', file=sys.stderr)
        return 1

    with open(SRC_MAIN, encoding='utf-8') as f:
        src = f.read()

    raw = collect_status(src)
    if not raw:
        print('没有解析到任何 status.* 块', file=sys.stderr)
        return 1

    names = load_index()
    appliers = scan_appliers({sid for sid, _ in raw}, names)

    effects = []
    for sid, fields in raw:
        mods, flags = humanize(fields)
        effects.append({
            'id': sid,
            'nameZh': fields.get('localizedName') or sid,
            'color': fields.get('color'),
            'show': bool(fields.get('show', True)),
            'opposites': fields.get('opposites') or [],
            'applyEffect': fields.get('applyEffect'),
            'effect': fields.get('effect'),
            'uiIcon': fields.get('uiIcon'),
            'mods': mods,
            'flags': flags,
            'appliers': appliers.get(sid, []),
            'raw': fields,
        })

    os.makedirs(PUB, exist_ok=True)
    os.makedirs(DATA, exist_ok=True)
    for path in (os.path.join(DATA, 'status_effects.json'),
                 os.path.join(PUB, 'effects.json')):
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(effects, f, ensure_ascii=False, indent=1)

    for e in effects:
        print(f"状态效果 {e['id']:10s} {e['nameZh']}  "
              f"修正 {len(e['mods'])} 项  施加者 {len(e['appliers'])} 处")
    print(f'-> {PUB}/effects.json')
    return 0


if __name__ == '__main__':
    sys.exit(main())
