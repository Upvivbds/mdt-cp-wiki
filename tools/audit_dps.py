#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DPS 审计：逐单位打印武器明细，并列出可疑项。

用法：
  python3 tools/audit_dps.py                 只打印全局可疑清单 + 默认抽样
  python3 tools/audit_dps.py merui horizon   打印指定单位的完整明细
"""
import os, json, sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
PUB = os.path.join(ROOT, 'docs', 'public', 'data')


def load():
    units = json.load(open(os.path.join(PUB, 'units.json'), encoding='utf-8'))
    return {u['id']: u for u in units}


def show(u):
    print('=' * 78)
    print('【%s】%s  作者=%s  T=%s  HP=%s' %
          (u['id'], u['nameZh'], u['author'], u['tier'], u['stats']['health']))
    print('  总DPS=%.1f  对空=%.1f  对地=%.1f   (原版 %.1f / %.1f / %.1f)' % (
        u['dps']['total'], u['dps']['air'], u['dps']['ground'],
        u['vanillaDps']['total'], u['vanillaDps']['air'], u['vanillaDps']['ground']))
    for i, w in enumerate(u['weapons']):
        dp = w['dps']
        print('    [%d] %-22s %-16s role=%-12s mode=%-10s' %
              (i, str(w['name'])[:22], str(w['bulletType'])[:16],
               w['role'], w['mode']))
        print('        reload=%s%s  shots=%s  damage=%s  splash=%s  DPS=%s  单发=%s' % (
            w['reload'], '' if w['reloadExplicit'] else '(默认)',
            w['shots'], w['damage'], w['splashDamage'],
            ('%.2f' % dp) if dp is not None else '—', w['perShot']))
        print('        对空=%s 对地=%s 射程=%s  continuous=%s' %
              (w['canHitAir'], w['canHitGround'], w['bulletRange'], w['continuous']))


def main():
    by = load()
    args = sys.argv[1:]
    print('单位总数: %d' % len(by))

    print()
    print('=' * 78)
    print('【全局审计】')
    print('=' * 78)

    no_weapon = [u['id'] for u in by.values() if not u['weapons']]
    zero_dps = [u['id'] for u in by.values()
                if u['weapons'] and u['dps']['total'] == 0]
    oneshot = [(u['id'], w['name'], w['perShot'])
               for u in by.values() for w in u['weapons'] if w['mode'] == 'oneshot']
    support = [(u['id'], w['name'], w['weaponType'])
               for u in by.values() for w in u['weapons'] if w['role'] != 'damage']
    weird = [(u['id'], w['name'], w['dps'])
             for u in by.values() for w in u['weapons']
             if isinstance(w['dps'], (int, float)) and w['dps'] > 3000]
    cont = [(u['id'], w['name'], w['dps'])
            for u in by.values() for w in u['weapons'] if w['mode'] == 'continuous']

    print('无武器单位 (%d): %s' % (len(no_weapon), no_weapon))
    print()
    print('有武器但总 DPS=0 (%d): %s' % (len(zero_dps), zero_dps))
    print()
    print('一次性弹头（无 reload，只报单发）(%d):' % len(oneshot))
    for uid, nm, ps in oneshot:
        print('   %-18s %-26s 单发 %s' % (uid, nm, ps))
    print()
    print('非伤害武器（点防御/维修/建造/采矿）(%d):' % len(support))
    for uid, nm, ty in support:
        print('   %-18s %-26s %s' % (uid, nm, ty))
    print()
    print('持续光束武器 (%d):' % len(cont))
    for uid, nm, d in cont:
        print('   %-18s %-26s DPS=%.2f' % (uid, nm, d))
    print()
    print('DPS > 3000 的武器（需人工确认）(%d):' % len(weird))
    for uid, nm, d in weird:
        print('   %-18s %-26s %.1f' % (uid, nm, d))
    print()

    if not args:
        args = ['merui', 'horizon', 'crawler', 'anthicus', 'conquer',
                'collaris', 'disrupt-missile', 'mace', 'tecta', 'incite']
    print('=' * 78)
    print('【逐单位明细】')
    for uid in args:
        u = by.get(uid)
        if not u:
            print('!! 找不到 %s' % uid)
            continue
        show(u)
    return 0


if __name__ == '__main__':
    sys.exit(main())