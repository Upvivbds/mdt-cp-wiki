#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""解析 Mindustry 数据包（hjson 点号路径语法）。

数据包有两种形态，统一成同一个中间表示：

  A. 点号语法（行���）
       unit.eclipse.weapons.2.reload: 14.5
       unit.zenith.weapons.+: { x: 0, y: -5, bullet: {...} }
       unit.eclipse.parts: [ {...}, {...} ]

  B. JSON 嵌套块
       "unit": {
         "collaris": {
           "range": 512,
           "weapons.0.bullet.lifetime": 79,
           "weapons.+": [ {...} ]
         }
       }
     —— 注意 JSON 块内部的键**仍然是点号路径**，值是嵌套的 JSON。

统一表示：
  { (kind, id): { path_tuple: value } }
其中 path_tuple 是点号切分后的元组，例如 ('weapons','0','bullet','lifetime')。

v2 修复（2026-09-11）
--------------------
v1 有两处硬伤：
  1. JSON 顶层块 `"unit": {` 的键带引号，元信息分支没剥引号，
     导致整块被当成字符串塞进 meta，JSON 形态的单位（天帝/悲切等）全部丢失。
  2. JSON 行尾逗号（`"range": 512,`）没剥，数值被解析成字符串 '512,'。
v2 改为：先用花括号配平把 `"unit"/"block"/"status"` 块整段切出来，
交给 json.loads 处理（严格 JSON，可靠得多）；剩余部分走行式解析。
"""
import os, re, json, sys, collections


# ============================================================
# 一、词法工具
# ============================================================
def _skip_string(s, i):
    """s[i] 是引号，返回字符串结束后的下标。"""
    i += 1
    while i < len(s):
        if s[i] == '\\':
            i += 2
            continue
        if s[i] == '"':
            return i + 1
        i += 1
    return i


def _skip_comment(s, i):
    if s.startswith('//', i):
        j = s.find('\n', i)
        return len(s) if j < 0 else j
    if s.startswith('/*', i):
        j = s.find('*/', i + 2)
        return len(s) if j < 0 else j + 2
    return i


def _match(s, i, op, cl):
    """s[i] == op，返回配对 cl 的下标（跳过字符串与注释）。"""
    d = 0
    while i < len(s):
        c = s[i]
        if c == '"':
            i = _skip_string(s, i)
            continue
        if c == '/' and i + 1 < len(s) and s[i + 1] in '/*':
            i = _skip_comment(s, i)
            continue
        if c == op:
            d += 1
        elif c == cl:
            d -= 1
            if d == 0:
                return i
        i += 1
    return -1


def strip_comments(text):
    """去掉 // 与 /* */ 注释，保留字符串内容。"""
    out, i, n = [], 0, len(text)
    while i < n:
        c = text[i]
        if c == '"':
            j = _skip_string(text, i)
            out.append(text[i:j])
            i = j
            continue
        if c == '/' and i + 1 < n and text[i + 1] in '/*':
            i = _skip_comment(text, i)
            continue
        out.append(c)
        i += 1
    return ''.join(out)


# ============================================================
# 二、JSON 顶层块提取
# ============================================================
# 匹配行首的 "unit" / "block" / "status" 后跟冒号与左花括号
JSON_BLOCK_RE = re.compile(
    r'^[ \t]*"(unit|block|status)"[ \t]*:[ \t]*\{', re.M)


def extract_json_blocks(text):
    """把 `"unit": { ... }` 这类块整段切出来。

    返回 (cleaned_text, blocks)，blocks 是 [(kind, dict), ...]。
    cleaned_text 里这些块被替换成等量空白（保持行号不变）。
    """
    blocks = []
    out = list(text)
    pos = 0
    while True:
        m = JSON_BLOCK_RE.search(text, pos)
        if not m:
            break
        kind = m.group(1)
        brace = text.index('{', m.start())
        end = _match(text, brace, '{', '}')
        if end < 0:
            pos = m.end()
            continue
        raw = text[brace:end + 1]
        # 清掉可能的行尾逗号
        raw = re.sub(r',(\s*[}\]])', r'\1', raw)
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError as e:
            print('WARN JSON 块解析失败 (%s): %s' % (kind, e), file=sys.stderr)
            obj = None
        if isinstance(obj, dict):
            blocks.append((kind, obj))
        # 用空白覆盖，保持后续行号/偏移不变
        for k in range(m.start(), end + 1):
            if out[k] not in '\r\n':
                out[k] = ' '
        pos = end + 1
    return ''.join(out), blocks


# ============================================================
# 三、标量与值解析
# ============================================================
_NUM = re.compile(r'^[-+]?(?:[0-9]+\.?[0-9]*|\.[0-9]+)(?:[eE][-+]?[0-9]+)?$')


def parse_scalar(raw):
    v = raw.strip()
    if v.endswith(','):
        v = v[:-1].rstrip()
    if not v:
        return ''
    while len(v) > 1 and v[-1] in 'fFdD' and (v[-2].isdigit() or v[-2] in '.'):
        v = v[:-1]
    if v in ('true', 'True'):
        return True
    if v in ('false', 'False'):
        return False
    if v in ('null', 'nil', 'none'):
        return None
    if len(v) >= 2 and v[0] == v[-1] and v[0] in '"\'':
        return v[1:-1]
    if _NUM.match(v):
        try:
            f = float(v)
            if f.is_integer() and '.' not in v and 'e' not in v.lower():
                return int(f)
            return f
        except ValueError:
            pass
    return v


def split_top(s, sep=','):
    """按顶层分隔符切分（忽略括号/字符串/注释内部）。"""
    out, buf = [], []
    d = {'(': 0, '[': 0, '{': 0}
    close = {')': '(', ']': '[', '}': '{'}
    i = 0
    while i < len(s):
        c = s[i]
        if c == '"':
            j = _skip_string(s, i)
            buf.append(s[i:j])
            i = j
            continue
        if c == '/' and i + 1 < len(s) and s[i + 1] in '/*':
            i = _skip_comment(s, i)
            continue
        if c in d:
            d[c] += 1
        elif c in close:
            d[close[c]] -= 1
        if c == sep and all(v == 0 for v in d.values()):
            out.append(''.join(buf))
            buf = []
            i += 1
            continue
        buf.append(c)
        i += 1
    tail = ''.join(buf)
    if tail.strip():
        out.append(tail)
    return out


def _split_newlines_top(s):
    """按顶层换行切分（忽略括号内换行）。"""
    parts, buf = [], []
    d = {'(': 0, '[': 0, '{': 0}
    close = {')': '(', ']': '[', '}': '{'}
    i = 0
    while i < len(s):
        c = s[i]
        if c == '"':
            j = _skip_string(s, i)
            buf.append(s[i:j])
            i = j
            continue
        if c in d:
            d[c] += 1
        elif c in close:
            d[close[c]] -= 1
        if c == '\n' and all(v == 0 for v in d.values()):
            parts.append(''.join(buf))
            buf = []
            i += 1
            continue
        buf.append(c)
        i += 1
    parts.append(''.join(buf))
    return parts


_KEYVAL_RE = re.compile(r'^\s*("[^"]*"|[^:\s][^:]*?)\s*:\s*(.*)$', re.S)


def parse_inline_object(body):
    """解析 `{ ... }` 内部为 dict（逗号或换行分隔）。"""
    out = collections.OrderedDict()
    for chunk in split_top(body, ','):
        for piece in _split_newlines_top(chunk):
            piece = piece.strip()
            if not piece:
                continue
            m = _KEYVAL_RE.match(piece)
            if m:
                k = m.group(1).strip()
                if len(k) >= 2 and k[0] == k[-1] and k[0] == '"':
                    k = k[1:-1]
                out[k] = parse_value(m.group(2))
            else:
                out.setdefault('__positional__', []).append(piece)
    return out


def parse_value(raw):
    raw = raw.strip()
    if raw.endswith(','):
        raw = raw[:-1].rstrip()
    if not raw:
        return ''
    if raw[0] == '{':
        end = _match(raw, 0, '{', '}')
        if end > 0:
            return parse_inline_object(raw[1:end])
    if raw[0] == '[':
        end = _match(raw, 0, '[', ']')
        if end > 0:
            return [parse_value(x) for x in split_top(raw[1:end], ',') if x.strip()]
    return parse_scalar(raw)


# ============================================================
# 四、路径展开
# ============================================================
def split_path(key):
    return [p for p in key.split('.') if p != '']


def flatten(path, value, into):
    """嵌套 dict 展开成多条 (path_tuple, 标量)；list 整体保留。"""
    if isinstance(value, dict):
        real = {k: v for k, v in value.items() if k != '__positional__'}
        if not real:
            into[tuple(path)] = {}
            return
        for k, v in real.items():
            flatten(path + split_path(k), v, into)
        return
    into[tuple(path)] = value


# ============================================================
# 五、主解析器
# ============================================================
class Datapack:
    def __init__(self):
        self.data = collections.OrderedDict()   # (kind, uid) -> {path: value}
        self.meta = collections.OrderedDict()

    def _bucket(self, kind, uid):
        return self.data.setdefault((kind, uid), collections.OrderedDict())

    def _put(self, kind, uid, rest, val):
        bucket = self._bucket(kind, uid)
        if not rest:
            if isinstance(val, dict):
                flatten([], val, bucket)
            else:
                bucket[()] = val
            return
        if isinstance(val, dict):
            tmp = collections.OrderedDict()
            flatten(rest, val, tmp)
            for k, v in tmp.items():
                bucket[k] = v
        else:
            bucket[tuple(rest)] = val

    def feed(self, text):
        text = strip_comments(text)
        text, blocks = extract_json_blocks(text)

        # ---------- JSON 块 ----------
        for kind, obj in blocks:
            for uid, sub in obj.items():
                if not isinstance(sub, dict):
                    self.meta['%s.%s' % (kind, uid)] = sub
                    continue
                tmp = collections.OrderedDict()
                flatten([], sub, tmp)
                bucket = self._bucket(kind, uid)
                for k, v in tmp.items():
                    bucket[k] = v

        # ---------- 行式点号语法 ----------
        i, n = 0, len(text)
        while i < n:
            while i < n and text[i] in ' \t\r\n':
                i += 1
            if i >= n:
                break

            # 读键
            j = i
            key_end = -1
            while j < n:
                c = text[j]
                if c == '"':
                    j = _skip_string(text, j)
                    continue
                if c == '{' or c == '\n':
                    key_end = j
                    break
                if c == ':':
                    key_end = j
                    break
                j += 1
            if key_end < 0:
                break
            key_raw = text[i:key_end].strip()
            i = key_end

            if i >= n or text[i] != ':':
                while i < n and text[i] != '\n':
                    i += 1
                continue
            i += 1
            while i < n and text[i] in ' \t':
                i += 1

            # 读值
            if i < n and text[i] == '{':
                end = _match(text, i, '{', '}')
                if end < 0:
                    break
                raw_val = text[i:end + 1]
                i = end + 1
            elif i < n and text[i] == '[':
                end = _match(text, i, '[', ']')
                if end < 0:
                    break
                raw_val = text[i:end + 1]
                i = end + 1
            else:
                vs = i
                while i < n and text[i] != '\n':
                    i += 1
                raw_val = text[vs:i]

            val = parse_value(raw_val)

            key = key_raw
            if len(key) >= 2 and key[0] == key[-1] == '"':
                key = key[1:-1]

            parts = split_path(key)
            if len(parts) >= 2 and parts[0] in ('unit', 'block', 'status'):
                self._put(parts[0], parts[1], parts[2:], val)
            elif key in ('unit', 'block', 'status') and isinstance(val, dict):
                for uid, sub in val.items():
                    if isinstance(sub, dict):
                        self._put(key, uid, [], sub)
                    else:
                        self.meta['%s.%s' % (key, uid)] = sub
            else:
                self.meta[key] = val

        return self

    # ---------- 查询 ----------
    def units(self):
        return sorted(u for (k, u) in self.data if k == 'unit')

    def blocks(self):
        return sorted(b for (k, b) in self.data if k == 'block')

    def statuses(self):
        return sorted(s for (k, s) in self.data if k == 'status')

    def get(self, kind, uid):
        return self.data.get((kind, uid), {})

    def to_jsonable(self):
        ent = {}
        for (kind, uid), bucket in self.data.items():
            d = {}
            for path, val in bucket.items():
                d['.'.join(path) if path else '__root__'] = val
            ent['%s.%s' % (kind, uid)] = d
        return {'meta': self.meta, 'entities': ent}


def parse_file(path):
    return Datapack().feed(open(path, encoding='utf-8').read())


# ============================================================
# 六、CLI
# ============================================================
def main():
    root = os.path.expanduser('~/Downloads/数据包单位总览')
    packs = sorted(f for f in os.listdir(root)
                   if f.endswith('.hjson') and not f.startswith('_'))
    print('找到 %d 个补丁包' % len(packs))
    print()
    total_u, total_b, total_s = set(), set(), set()
    result = {}
    for f in packs:
        dp = parse_file(os.path.join(root, f))
        us, bs, ss = dp.units(), dp.blocks(), dp.statuses()
        total_u |= set(us)
        total_b |= set(bs)
        total_s |= set(ss)
        n_paths = sum(len(v) for v in dp.data.values())
        print('  %-44s unit=%2d block=%2d status=%d paths=%d'
              % (f, len(us), len(bs), len(ss), n_paths))
        result[f] = dp.to_jsonable()

    print()
    print('合计: unit=%d block=%d status=%d'
          % (len(total_u), len(total_b), len(total_s)))
    print()
    print('units  (%d):' % len(total_u))
    print('  ' + ' '.join(sorted(total_u)))
    print()
    print('blocks (%d):' % len(total_b))
    print('  ' + ' '.join(sorted(total_b)))
    print()
    print('status (%d): %s' % (len(total_s), sorted(total_s)))

    dest = os.path.normpath(os.path.join(
        os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'datapack.json'))
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, 'w', encoding='utf-8') as fh:
        json.dump(result, fh, ensure_ascii=False, indent=1)
    print()
    print('已写出 -> %s' % dest)
    return 0


if __name__ == '__main__':
    sys.exit(main())