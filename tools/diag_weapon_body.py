#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""诊断 conquer / collaris / incite 的 weapon body 为何切不出 bullet 语句。"""
import sys, os, re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import parse_java_units as P

src = P.strip_comments(open(P.SRC, encoding='utf-8').read())


def unit_body(name):
    for m in P.UNIT_RE.finditer(src):
        if m.group(3) != name:
            continue
        j = src.find('{', m.end())
        if j > 0 and src[j + 1] == '{':
            j += 1
        end = P.match_brace(src, j)
        if end < 0:
            return None
        return src[j + 1:end]
    return None


for name in ['conquer', 'collaris', 'incite', 'mace']:
    body = unit_body(name)
    print('=' * 74)
    print('【%s】unit body %s chars' % (name, len(body) if body else 'N/A'))
    if not body:
        continue
    for a in re.finditer(r'weapons\.add', body):
        op = body.index('(', a.start())
        cp = P.match_bracket(body, op, '(', ')')
        if cp < 0:
            print('  weapons.add 括号未配平!')
            continue
        inner = body[op + 1:cp]
        args = P.split_top(inner, ',')
        print('  weapons.add 参数个数: %d' % len(args))
        for i, arg in enumerate(args):
            r = P.parse_new_expr(arg, 0)
            if not r:
                print('    [%d] parse_new_expr 失败  arg[:90]=%r'
                      % (i, arg.strip()[:90]))
                continue
            ty, aargs, wbody = r
            print('    [%d] type=%s args=%s wbody=%s chars'
                  % (i, ty, aargs, len(wbody) if wbody is not None else None))
            if wbody is None:
                continue
            sts = P.parse_statements(wbody)
            print('        顶层语句数: %d' % len(sts))
            has_bullet_stmt = False
            for s in sts:
                t = s.strip()
                if t.startswith('bullet'):
                    has_bullet_stmt = True
                    print('        >> 找到 bullet 语句: %s' % t[:80])
                elif t.startswith(('parts.add', 'for', 'if', 'int ')):
                    print('        .. 其它语句: %s' % t[:80].replace('\n', ' '))
            if not has_bullet_stmt:
                pos = wbody.find('bullet =')
                print('        !! 没有 bullet 语句。 wbody 里 "bullet =" 位置=%s'
                      % pos)
                if pos >= 0:
                    # 找出这条语句实际被切成了什么
                    for k, s in enumerate(sts):
                        if 'bullet' in s:
                            print('           第 %d 条语句含 bullet: %s'
                                  % (k, s.strip()[:120].replace('\n', ' ')))
                            break
        break
    print()
PYEOF_MARKER_NOT_USED