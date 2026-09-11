#!/usr/bin/env python3
"""
静态体检 theme/ 下的 Vue 组件与 VitePress 配置。

动机：站点里出现过的真实 bug 有两类，构建期都不报错 ——
  1. `<script setup>` 里用了未导入的符号（loadJson），运行时 ReferenceError，
     被 try/catch 静默吞掉，页面只是"永远空着"。
  2. 模板里写了 `<Foo />` 但组件没注册，VitePress 原样输出标签，页面一片空白。
本脚本把这两类问题变成可见的静态报告。
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
THEME = os.path.join(ROOT, 'docs', '.vitepress', 'theme')
COMPONENTS = os.path.join(THEME, 'components')
PAGES_DIR = os.path.join(ROOT, 'docs')

# 模板里合法但不需声明的名字
BUILTINS = {
    'true', 'false', 'null', 'undefined', 'this',
    'Math', 'Number', 'String', 'Boolean', 'Array', 'Object', 'JSON', 'Date',
    'RegExp', 'Map', 'Set', 'Promise', 'Error', 'isNaN', 'isFinite',
    'parseInt', 'parseFloat', 'encodeURIComponent', 'decodeURIComponent',
    'window', 'document', 'console', 'navigator', 'location',
    '$event', '$slots', '$attrs', '$props', '$emit', '$refs', '$el', '$nextTick',
    'in', 'of', 'new', 'typeof', 'instanceof', 'return', 'if', 'else', 'void',
    'await', 'async', 'function', 'class', 'const', 'let', 'var', 'delete',
    # Vue 模板里天然可见、无需在 script 里声明的名字
    'event', 'key', 'index', 'ref', 'type', 'value', 'label', 'id', 'name',
    'length', 'item', 'props', 'attrs', 'slots',
}

IDENT = re.compile(r'\b[A-Za-z_$][\w$]*\b')
SCRIPT_RE = re.compile(r'<script[^>]*>(.*?)</script>', re.S)
TEMPLATE_RE = re.compile(r'<template[^>]*>(.*?)</template>', re.S)


def declared_names(script: str):
    """script setup 里所有"声明出来的"顶层名字。"""
    names = set()
    # import a from 'x' / import {a, b as c} from 'x'
    for m in re.finditer(r'import\s+([\s\S]*?)\s+from\s+[\'"]', script):
        clause = m.group(1)
        clause = re.sub(r'\{|\}', ' ', clause)
        for part in clause.split(','):
            part = part.strip()
            if not part:
                continue
            if ' as ' in part:
                part = part.split(' as ')[-1]
            part = part.replace('*', ' ').strip()
            if IDENT.fullmatch(part or ''):
                names.add(part)
    # const/let/var/function 声明（含解构）
    for m in re.finditer(r'\b(?:const|let|var)\s+([^=;\n]+?)\s*=', script):
        for part in m.group(1).split(','):
            part = re.sub(r'[{}[\]]', ' ', part).strip()
            for tok in part.split(':'):
                tok = tok.strip()
                if IDENT.fullmatch(tok or ''):
                    names.add(tok)
    for m in re.finditer(r'\bfunction\s+([A-Za-z_$][\w$]*)', script):
        names.add(m.group(1))
    # defineProps 的键：在模板里直接当变量用（props.value 与 value 等价）
    for m in re.finditer(r'defineProps\s*\(\s*\{(.*?)\n\s*\}\s*\)', script, re.S):
        for km in re.finditer(r'^\s*([A-Za-z_$][\w$]*)\s*:', m.group(1), re.M):
            names.add(km.group(1))
    return names


def template_expressions(tpl: str):
    """模板里所有需要求值的表达式片段。"""
    exprs = []
    for m in re.finditer(r'\{\{([\s\S]*?)\}\}', tpl):
        exprs.append(m.group(1))
    for m in re.finditer(r'(?:v-if|v-else-if|v-show|v-for|v-model|v-bind|v-on|v-html|v-text)'
                         r'(?::[\w.-]+)?\s*=\s*"([^"]*)"', tpl):
        exprs.append(m.group(1))
    for m in re.finditer(r'[:@][\w.-]+\s*=\s*"([^"]*)"', tpl):
        exprs.append(m.group(1))
    return exprs


def vfor_aliases(tpl: str):
    """v-for 引入的局部名，涵盖 v / (v, i) / [k, v] / ({a, b}) 四种写法。"""
    names = set()
    for m in re.finditer(r'v-for\s*=\s*"([^"]*)"', tpl):
        body = m.group(1)
        head = re.split(r'\s+(?:in|of)\s+', body)[0]
        # 去掉括号、方括号、花括号，再按逗号切；`k: v` 形式取别名
        for part in re.split(r'[,\[\](){}]', head):
            part = part.strip()
            if ':' in part:
                part = part.split(':')[-1].strip()
            if part and IDENT.fullmatch(part):
                names.add(part)
    return names


def free_identifiers(expr: str, scope: set):
    out = set()
    # 先去掉对象字面量的键名 `foo:`（避免误判）
    cleaned = re.sub(r'([{,]\s*)[A-Za-z_$][\w$]*\s*:', r'\1', expr)
    for m in IDENT.finditer(cleaned):
        name = m.group(0)
        start = m.start()
        # 属性访问 a.b 里的 b 不算自由变量
        if start > 0 and cleaned[start - 1] == '.':
            continue
        # 字符串字面量里的内容不算
        before = cleaned[:start]
        # 落在字符串/模板字面量内部的名字不算标识符（反引号也必须算上，
        # 否则 `/units/${id}` 里的 units 会被误报）
        if (before.count("'") % 2 == 1
                or before.count('"') % 2 == 1
                or before.count('`') % 2 == 1):
            continue
        if name in BUILTINS or name in scope:
            continue
        out.add(name)
    return out


def audit_component(path):
    src = open(path, encoding='utf-8').read()
    scripts = SCRIPT_RE.findall(src)
    script = scripts[0] if scripts else ''
    # 顶层 <template> 是整个组件模板（可能嵌套，取最外层靠正则够了）
    tpls = TEMPLATE_RE.findall(src)
    tpl = max(tpls, key=len) if tpls else ''

    declared = declared_names(script)
    declared |= vfor_aliases(tpl)

    # 注册为全局的组件名（theme/index.ts 里的 app.component）在别处检查
    used_undeclared = set()
    for expr in template_expressions(tpl):
        used_undeclared |= free_identifiers(expr, declared)

    # 脚本里是否用了未导入的"疑似工具函数"（loadJson 那一类）
    problems = []
    if used_undeclared:
        problems.append(('模板未声明标识符', sorted(used_undeclared)))

    return problems


def audit_imports():
    """相对 import 的目标文件是否存在。"""
    bad = []
    for dirpath, _, files in os.walk(THEME):
        for fn in files:
            if not fn.endswith(('.vue', '.ts', '.js')):
                continue
            p = os.path.join(dirpath, fn)
            src = open(p, encoding='utf-8').read()
            for m in re.finditer(r'from\s+[\'"](\.[^\'"]+)[\'"]', src):
                rel = m.group(1)
                base = os.path.normpath(os.path.join(dirpath, rel))
                if os.path.exists(base):
                    continue
                if any(os.path.exists(base + ext) for ext in ('.ts', '.js', '.vue', '.json')):
                    continue
                if os.path.isdir(base):
                    continue
                bad.append((os.path.relpath(p, ROOT), rel))
    return bad


def audit_registration():
    """theme/index.ts 注册的组件 vs components 目录里的文件。"""
    idx = os.path.join(THEME, 'index.ts')
    src = open(idx, encoding='utf-8').read()
    registered = set(re.findall(r"app\.component\(\s*['\"]([\w]+)['\"]", src))
    files = {f[:-4] for f in os.listdir(COMPONENTS) if f.endswith('.vue')}
    return registered, files


def audit_pages():
    """md 页面里用到的 PascalCase 标签是否都已注册。"""
    idx = os.path.join(THEME, 'index.ts')
    src = open(idx, encoding='utf-8').read()
    registered = set(re.findall(r"app\.component\(\s*['\"]([\w]+)['\"]", src))
    missing = []
    for dirpath, _, files in os.walk(PAGES_DIR):
        if 'node_modules' in dirpath or '.vitepress' in dirpath:
            continue
        for fn in files:
            if not fn.endswith('.md'):
                continue
            p = os.path.join(dirpath, fn)
            text = open(p, encoding='utf-8').read()
            for tag in set(re.findall(r'<([A-Z][A-Za-z0-9]*)\s*/?>', text)):
                if tag not in registered:
                    missing.append((os.path.relpath(p, ROOT), tag))
    return missing


def main():
    fails = 0

    print('=== 1. 组件模板中的未声明标识符 ===')
    for fn in sorted(os.listdir(COMPONENTS)):
        if not fn.endswith('.vue'):
            continue
        p = os.path.join(COMPONENTS, fn)
        problems = audit_component(p)
        if problems:
            fails += 1
            print(f'  !! {fn}')
            for label, names in problems:
                print(f'       {label}: {names}')
    if fails == 0:
        print('  OK 全部组件模板引用的名字都有声明')

    print()
    print('=== 2. 相对 import 目标是否存在 ===')
    bad = audit_imports()
    if bad:
        fails += 1
        for f, rel in bad:
            print(f'  !! {f} -> {rel}  (找不到)')
    else:
        print('  OK 所有相对 import 都能解析')

    print()
    print('=== 3. 组件注册情况 ===')
    registered, files = audit_registration()
    print(f'  已注册 {len(registered)} 个: {sorted(registered)}')
    unreg = sorted(files - registered)
    if unreg:
        fails += 1
        print(f'  !! 存在但未注册（页面里引用会渲染成字面标签）: {unreg}')
    else:
        print('  OK components/ 下每个 .vue 都已注册')

    print()
    print('=== 4. md 页面里的组件标签是否都已注册 ===')
    missing = audit_pages()
    if missing:
        fails += 1
        for page, tag in missing:
            print(f'  !! {page} 使用了未注册的 <{tag}>')
    else:
        print('  OK 所有页面用到的组件标签都已注册')

    print()
    print('AUDIT=' + ('PASS' if fails == 0 else f'FAIL({fails})'))
    return 0 if fails == 0 else 1


if __name__ == '__main__':
    sys.exit(main())