#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 Mindustry 源码 Blocks.java 提取原版炮塔的装填与弹药数据。

为什么需要它：数据包对建筑的改动是**稀疏补丁**，多数建筑只覆盖了
`ammoTypes.<弹药>.damage` 这类字段，本身不含 `reload`。没有原版装填时间
就算不出 DPS。所以要把原版炮塔定义也解析出来做基准。

结构（与 UnitTypes.java 同构，复用同一套词法工具）：

    scatter = new ItemTurret("scatter"){{
        requirements(Category.turret, ...);
        ammo(
            Items.scrap, new FlakBulletType(4f, 3){{ ... }},
            Items.lead,  new FlakBulletType(4.2f, 3){{ ... }}
        );
        reload = 18f;
    }};

输出 data/vanilla_blocks.json
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import parse_java_units as P  # 复用词法 / new 表达式 / 构造器语义

SRC = os.path.expanduser(
    '~/Downloads/Mindustry-master/core/src/mindustry/content/Blocks.java')

TURRET_RE = re.compile(
    r'^[ \t]*([A-Za-z_]\w*)\s*=\s*new\s+(\w*Turret)\s*\(\s*"([^"]+)"\s*\)', re.M)

# 非弹药的炮塔用 shootType 直接给弹种（激光/电力炮台）
NON_AMMO_TURRETS = {
    'LaserTurret', 'PowerTurret', 'PointDefenseTurret', 'TractorBeamTurret',
    'CooledTurret', 'ContinuousTurret', 'ContinuousLiquidTurret', 'RepairTurret',
}

# 真正会对外输出的炮塔。DrawTurret 是墙体 buildType 里的贴图模板
# （new DrawTurret("reinforced-")），BuildTurret/RepairTurret 不造成伤害，
# 都会被正则一起匹配到，必须按类名过滤掉。
DAMAGE_TURRETS = {
    'ItemTurret', 'LiquidTurret', 'PowerTurret', 'LaserTurret',
    'ContinuousTurret', 'ContinuousLiquidTurret', 'CooledTurret', 'Turret',
}


def parse_ammo_pairs(body):
    """解析 ammo(物品, 子弹, 物品, 子弹, ...) —— 成对读取。"""
    out = []
    for m in re.finditer(r'(?<![\w.])ammo\s*\(', body):
        op = body.index('(', m.start())
        cp = P.match_bracket(body, op, '(', ')')
        if cp < 0:
            continue
        args = [a.strip() for a in P.split_top(body[op + 1:cp], ',') if a.strip()]
        i = 0
        while i + 1 < len(args):
            item, raw = args[i], args[i + 1]
            i += 2
            if raw.startswith('new'):
                b = P.parse_new_obj(raw)
                out.append((item, b))
    return out


def parse_ammo_puts(body, resolve):
    """解析 ammoTypes.put(物品, 子弹) 形式。"""
    out = []
    for m in re.finditer(r'ammoTypes\.put\s*\(', body):
        op = body.index('(', m.start())
        cp = P.match_bracket(body, op, '(', ')')
        if cp < 0:
            continue
        args = [a.strip() for a in P.split_top(body[op + 1:cp], ',')]
        if len(args) >= 2:
            raw = args[1]
            b = P.parse_new_obj(raw) if raw.startswith('new') else (
                resolve(raw) if re.fullmatch(r'[A-Za-z_]\w*', raw) else None)
            if b:
                out.append((args[0], b))
    return out


def parse_turret_body(body):
    stmts = P.parse_statements(body)
    resolve = P.make_resolver(stmts)

    t = {'ammo': [], 'misc': []}

    ammo = parse_ammo_pairs(body)
    if not ammo:
        ammo = parse_ammo_puts(body, resolve)
    t['ammo'] = ammo

    for st in stmts:
        s = st.strip()
        if not s or s.startswith(('ammo(', 'ammoTypes', 'requirements(', 'consume(',
                                  'buildType', 'researchCost', 'alwaysUnlocked')):
            continue
        m = re.match(r'^([A-Za-z_][\w.]*)\s*=\s*(.+)$', s, re.S)
        if m:
            k, v = m.group(1), m.group(2)
            if re.match(r'^[A-Za-z_]\w*\s*=', v):
                continue
            # 凡是以 `new X(...)` 开头的字段都是对象（shoot / shootType /
            # ammoTypes 等）。早先只白名单了 shootType/bullet，于是 shoot 被
            # 存成字符串，后面取 shots 时直接抛 AttributeError。
            if re.match(r'new\s+[A-Za-z_][\w.]*\s*\(', v.strip()):
                t[k] = P.parse_new_obj(v)
            else:
                t[k] = P.to_py(v)
        else:
            t['misc'].append(s[:160])

    return t


def main():
    text = P.strip_comments(open(SRC, encoding='utf-8').read())
    blocks, order = {}, []

    for m in TURRET_RE.finditer(text):
        ident, cls, bid = m.group(1), m.group(2), m.group(3)
        j = text.find('{', m.end())
        if j < 0:
            continue
        if j + 1 < len(text) and text[j + 1] == '{':
            j += 1
        end = P.match_brace(text, j)
        if end < 0:
            continue
        if cls not in DAMAGE_TURRETS:
            continue
        t = parse_turret_body(text[j + 1:end])
        t['__ident'] = ident
        t['__class'] = cls
        t['id'] = bid
        blocks[bid] = t
        order.append(bid)

    dest = os.path.normpath(os.path.join(HERE, '..', 'data', 'vanilla_blocks.json'))
    with open(dest, 'w', encoding='utf-8') as f:
        json.dump({'source': SRC, 'count': len(blocks), 'order': order,
                   'blocks': blocks}, f, ensure_ascii=False, indent=1)

    print(f'解析出 {len(blocks)} 个炮塔 -> {dest}')
    print()
    print(f'{"id":22s} {"class":20s} {"reload":>8s} {"ammo":>5s}')
    print('-' * 60)
    for bid in order:
        t = blocks[bid]
        print(f'  {bid:20s} {t["__class"]:20s} {str(t.get("reload") or "-"):>8s} '
              f'{len(t["ammo"]):>5d}')

    no_ammo = [b for b in order if not blocks[b]['ammo'] and 'shootType' not in blocks[b]]
    if no_ammo:
        print()
        print(f'!! 无弹药也无 shootType 的炮塔 {len(no_ammo)} 个: {no_ammo}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
