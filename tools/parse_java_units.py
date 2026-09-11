#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 Mindustry 源码 UnitTypes.java 提取原版单位数值 —— v3

v1/v2 漏解析了 11 个单位，两种原因
----------------------------------
1. 多参 weapons.add（8 处）
       weapons.add(
           new Weapon("a"){{ ... }},
           new Weapon("b"){{ ... }});
   v2 只取第一个 new Weapon，后面的全丢。

2. bullet 引用单位体内的局部变量（9 处）
       BulletType missiles = new MissileBulletType(4f, 30){{ ... }};
       ...
       weapons.add(new Weapon("x"){{ bullet = missiles; }});
   v2 只认 `bullet = new ...`，遇到变量名就当成没有弹种。

v3 做法
-------
- 把单位体按顶层 `;` 切成语句
- 第一遍：收集所有 `<Type> <name> = <expr>` 形式的局部变量（含 `var`）
- 第二遍：处理 weapons.add(...)，参数按顶层逗号拆开，每个参数
  要么是 new 表达式，要么是变量名 → 查变量表（支持链式引用）
- weapon 体内的 `bullet = X` / `shoot = X` 同样支持 new 表达式与变量名

输出（与 v2 兼容）：data/vanilla_units.json
"""
import os, re, json, sys

SRC = os.path.expanduser(
    '~/Downloads/Mindustry-master/core/src/mindustry/content/UnitTypes.java')


# ============================================================
# 一、词法
# ============================================================
def skip_string(s, i):
    i += 1
    while i < len(s):
        if s[i] == '\\':
            i += 2
            continue
        if s[i] == '"':
            return i + 1
        i += 1
    return i


def skip_comment(s, i):
    if s.startswith('//', i):
        j = s.find('\n', i)
        return len(s) if j < 0 else j
    if s.startswith('/*', i):
        j = s.find('*/', i + 2)
        return len(s) if j < 0 else j + 2
    return i


def match_bracket(s, i, op='(', cl=')'):
    """s[i] == op，返回配对 cl 的下标（跳过字符串与注释）。"""
    d = 0
    while i < len(s):
        c = s[i]
        if c == '"':
            i = skip_string(s, i)
            continue
        if c == '/' and i + 1 < len(s) and s[i + 1] in '/*':
            i = skip_comment(s, i)
            continue
        if c == op:
            d += 1
        elif c == cl:
            d -= 1
            if d == 0:
                return i
        i += 1
    return -1


def match_brace(s, i):
    return match_bracket(s, i, '{', '}')


def strip_comments(s):
    out, i, n = [], 0, len(s)
    while i < n:
        c = s[i]
        if c == '"':
            j = skip_string(s, i)
            out.append(s[i:j])
            i = j
            continue
        if c == '/' and i + 1 < n and s[i + 1] in '/*':
            i = skip_comment(s, i)
            continue
        out.append(c)
        i += 1
    return ''.join(out)


def split_top(s, sep=';'):
    """按顶层分隔符切分（忽略括号/花括号/方括号/字符串内部）。"""
    out, buf = [], []
    d = {'(': 0, '[': 0, '{': 0}
    close = {')': '(', ']': '[', '}': '{'}
    i = 0
    while i < len(s):
        c = s[i]
        if c == '"':
            j = skip_string(s, i)
            buf.append(s[i:j])
            i = j
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


# ============================================================
# 二、值
# ============================================================
_NUM = re.compile(r'^[-+]?(?:[0-9]+\.?[0-9]*|\.[0-9]+)(?:[eE][-+]?[0-9]+)?$')


def strip_f(v):
    """去掉数值字面量的 Java 后缀。

    不能只剥最后一个：`37f*2f`、`60f * 5` 这类表达式里每个数字都带后缀，
    只剥末尾会让整串无法求值。mace 的 damage = 37f*2f 就是这样丢成 0 的。
    """
    v = v.strip()
    v = re.sub(r'(\d(?:\.\d+)?)[fFdD](?![0-9A-Za-z_])', r'\1', v)
    while len(v) > 1 and v[-1] in 'fFdD' and (v[-2].isdigit() or v[-2] == '.'):
        v = v[:-1]
    return v


def eval_num(v):
    """求值一个数值表达式，支持 + - * / 与括号。失败返回 None。"""
    v = strip_f(v).replace(' ', '')
    if not v:
        return None
    if not re.match(r'^[-+*/().0-9eE]+$', v):
        return None
    try:
        r = eval(v, {'__builtins__': {}}, {})
        return float(r)
    except Exception:
        return None


def to_py(raw):
    v = raw.strip()
    if v.endswith(','):
        v = v[:-1].rstrip()
    if not v:
        return ''
    if v in ('true', 'false'):
        return v == 'true'
    if v == 'null':
        return None
    if len(v) >= 2 and v[0] == '"' and v[-1] == '"':
        return v[1:-1]
    n = eval_num(v)
    if n is not None:
        return n
    return v


# ============================================================
# 三、new 表达式
# ============================================================
# 构造器语义（据各 BulletType 子类的 public 构造器签名）
CTOR_SPEED_DAMAGE = {
    'BulletType', 'BasicBulletType', 'ArtilleryBulletType', 'MissileBulletType',
    'LaserBoltBulletType', 'FlakBulletType',
    'LiquidBulletType', 'MassDriverBolt', 'ShrapnelBulletType',
    'SpaceBulletType', 'EmpBulletType', 'MultiBulletType',
    'ContinuousFlameBulletType',
}
CTOR_DAMAGE = {
    'LaserBulletType', 'ContinuousLaserBulletType', 'LightningBulletType',
    'RailBulletType',
}
# BombBulletType(float splashDamage, float splashDamageRadius)
# 曾经误放进 CTOR_SPEED_DAMAGE，导致 horizon 只拿到 speed 拿不到 splashDamage，
# 而它的 damage 写的是 `splashDamage * 0.5f` —— 两边都空，DPS 就成了 0。
CTOR_SPLASH = {'ExplosionBulletType', 'BombBulletType'}
CTOR_NONE = {'PointLaserBulletType', 'SapBulletType'}

# ShootPattern 家族的真实构造器签名（源码 entities/pattern/*.java）
SHOOT_CTORS = {
    'ShootSpread': ('shots', 'spread'),     # ShootSpread(int shots, float spread)
    'ShootAlternate': ('spread',),          # ShootAlternate(float spread)
    'ShootPattern': ('shots',),
}


def apply_shoot_ctor(o):
    """给 shoot 对象按构造器签名补 shots / spread。

    toxopid 的 `new ShootSpread(2, 17f)` 之前被当成 (speed, damage) 解析，
    shots 始终缺失（默认 1），DPS 少算一半。
    """
    ty = o.get('__type', '')
    args = o.get('__args') or []
    names = SHOOT_CTORS.get(ty)
    if not names:
        return o
    for name, raw in zip(names, args):
        if name in o:
            continue
        n = eval_num(raw)
        if n is not None:
            o[name] = int(n) if (name == 'shots' and float(n).is_integer()) else n
    return o


def parse_new_expr(s, pos=0):
    """解析 `new Type(args){{body}}` -> (type, args, body) 或 None。"""
    m = re.match(r'\s*new\s+([A-Za-z_][\w.]*)\s*\(', s[pos:])
    if not m:
        return None
    ty = m.group(1)
    op = pos + m.end() - 1
    cp = match_bracket(s, op, '(', ')')
    if cp < 0:
        return None
    args = [a for a in split_top(s[op + 1:cp], ',')]
    j = cp + 1
    while j < len(s) and s[j].isspace():
        j += 1
    body = None
    if j < len(s) and s[j] == '{':
        # Java 匿名类初始化块写作 {{ ... }}，是两个花括号。
        # 必须跳过外层那个，否则 body 从 '{' 开始，内部语句全落在 depth 1，
        # 按顶层 ';' 切分就一条都切不出来（v3 首版的回归 bug）。
        if j + 1 < len(s) and s[j + 1] == '{':
            j += 1
        end = match_brace(s, j)
        if end > 0:
            body = s[j + 1:end]
    return (ty, args, body)


def apply_ctor(o):
    """按构造器签名补 speed / damage / splashDamage。显式字段优先。"""
    ty = o.get('__type', '')
    args = o.get('__args') or []
    if ty in CTOR_SPEED_DAMAGE and len(args) >= 2:
        if 'speed' not in o:
            n = eval_num(args[0])
            if n is not None:
                o['speed'] = n
        if 'damage' not in o:
            n = eval_num(args[1])
            if n is not None:
                o['damage'] = n
    elif ty in CTOR_DAMAGE and len(args) >= 1:
        if 'damage' not in o:
            n = eval_num(args[0])
            if n is not None:
                o['damage'] = n
    elif ty in CTOR_SPLASH and len(args) >= 2:
        if 'splashDamage' not in o:
            n = eval_num(args[0])
            if n is not None:
                o['splashDamage'] = n
        if 'splashDamageRadius' not in o:
            n = eval_num(args[1])
            if n is not None:
                o['splashDamageRadius'] = n
    elif ty in CTOR_NONE:
        pass
    elif ty in SHOOT_CTORS:
        # 注意：这一支必须排在 else 之前。否则 ShootSpread(2, 17f) 会落进
        # 「未知类型」启发式，被当成 (speed=2, damage=17)，shots 永远缺失。
        apply_shoot_ctor(o)
    else:
        # 未知类型：按参数个数启发式
        if len(args) >= 2 and 'speed' not in o and 'damage' not in o:
            a, b = eval_num(args[0]), eval_num(args[1])
            if a is not None and b is not None:
                o.setdefault('speed', a)
                o.setdefault('damage', b)
        elif len(args) == 1 and 'damage' not in o:
            n = eval_num(args[0])
            if n is not None:
                o['damage'] = n
    return o


def parse_statements(body):
    """把 body 切成顶层语句列表。"""
    return [st for st in split_top(body, ';') if st.strip()]


# ============================================================
# 四、weapon / bullet
# ============================================================
def make_resolver(stmts):
    """从语句里收集局部变量声明，返回 resolve(name) -> dict|None。"""
    raw = {}
    for st in stmts:
        s = st.strip()
        m = re.match(r'^(?:var|[A-Z]\w*)\s+([a-z]\w*)\s*=\s*(.+)$', s, re.S)
        if m:
            raw[m.group(1)] = m.group(2).strip()

    cache = {}

    def resolve(name, depth=0):
        name = name.strip()
        if name in cache:
            return cache[name]
        if depth > 8 or name not in raw:
            return None
        txt = raw[name]
        if txt.startswith('new'):
            o = parse_new_obj(txt)
        else:
            o = resolve(txt, depth + 1)
        cache[name] = o
        return o

    return resolve


def resolve_symbolic(o):
    """把引用其他字段的表达式换成数值。

    源码里常见 `damage = splashDamage * 0.5f`（horizon）、
    `damage = splashDamage * 0.7f`（quad）、`cooldownTime = reload - 10f`
    （navanax）这类写法。直接 to_py 会得到字符串，DPS 就算成 0。
    这里在依赖字段已知时把结果算出来。
    """
    refs = {'splashDamage': o.get('splashDamage'), 'reload': o.get('reload'),
            'damage': o.get('damage'), 'lifetime': o.get('lifetime')}

    for field in ('damage', 'reload', 'cooldownTime', 'splashDamage'):
        v = o.get(field)
        if not isinstance(v, str):
            continue
        # 先剥 Java 数值后缀：`splashDamage * 0.5f` -> `splashDamage*0.5`
        s = v.replace(' ', '')
        s = re.sub(r'(\d)[fFdD](?![0-9A-Za-z_])', r'\1', s)
        m = re.match(r'^([A-Za-z_]\w*)(?:([-+*/])([0-9.]+))?$', s)
        if not m:
            continue
        base_name, op, const = m.group(1), m.group(2), m.group(3)
        base = refs.get(base_name)
        if not isinstance(base, (int, float)):
            continue
        if op is None:
            o[field] = base
        else:
            c = float(const)
            if op == '*':
                o[field] = base * c
            elif op == '/':
                o[field] = base / c if c else base
            elif op == '+':
                o[field] = base + c
            elif op == '-':
                o[field] = base - c
    return o


def parse_new_obj(expr):
    """解析 `new Type(args){{fields}}` 成字典。"""
    r = parse_new_expr(expr, 0)
    if not r:
        return {'__raw': expr.strip()[:300]}
    ty, args, body = r
    o = {'__type': ty, '__args': args}
    if body is not None:
        for st in parse_statements(body):
            s = st.strip()
            m = re.match(r'^([A-Za-z_][\w.]*)\s*=\s*(.+)$', s, re.S)
            if m:
                v = m.group(2)
                if re.match(r'^[A-Za-z_]\w*\s*=', v):
                    continue
                o[m.group(1)] = to_py(v)
            else:
                o.setdefault('__stmts', []).append(s[:200])
    return resolve_symbolic(apply_ctor(o))


def resolve_expr(text, resolve):
    """`new ...` 或变量名 -> dict；失败返回 None。"""
    t = text.strip()
    if t.endswith(';'):
        t = t[:-1].strip()
    if not t:
        return None
    if t.startswith('new'):
        return parse_new_obj(t)
    # 变量名（可能带 .field）
    m = re.match(r'^([A-Za-z_]\w*)\s*$', t)
    if m:
        return resolve(m.group(1))
    return None


# weapon 体内常见的标量字段。行级兜底只认这些，避免把嵌套匿名类的字段
# 误当成武器字段（比如 parts.add(new RegionPart(...){{ mirror = ... }})）。
WEAPON_SCALAR_FIELDS = {
    'name', 'x', 'y', 'shootX', 'shootY', 'rotate', 'rotateSpeed', 'mirror',
    'flipSprite', 'reload', 'cooldownTime', 'inaccuracy', 'shootCone', 'recoil',
    'shake', 'top', 'alternate', 'otherSide', 'baseRotation', 'rotationLimit',
    'layerOffset', 'minWarmup', 'shootWarmupSpeed', 'smoothReloadSpeed',
    'linearWarmup', 'continuous', 'alwaysContinuous', 'alwaysShooting',
    'autoTarget', 'controllable', 'aiControllable', 'useAmmo', 'useAttackRange',
    'targetInterval', 'targetSwitchInterval', 'minShootVelocity', 'velocityRnd',
    'extraVelocity', 'ignoreRotation', 'noAttack', 'soundPitchMin',
    'soundPitchMax', 'activeSoundVolume', 'shootSoundVolume', 'shootStatusDuration',
    # 死亡触发爆炸：anthicus / disrupt / quell 的副武器靠这个标记，
    # 漏了它就会把「命中即炸的战斗部」当成每秒输出（disrupt 曾算出 8575 DPS）。
    'shootOnDeath', 'shootOnDeathEffect', 'shootOnDeathChance',
    'shootOnDeathSpread', 'shootOnDeathSound',
    'display', 'showStatSprite', 'parentizeEffects', 'ejectEffect', 'region',
    'heatRegion', 'cellRegion', 'shootSound', 'activeSound', 'chargeSound',
    'initialShootSound', 'shootStatus', 'aimChangeSpeed', 'predictTarget',
    'barrels', 'spread', 'barrelOffset', 'shots', 'shotDelay', 'firstShotDelay',
    'widthSinMag', 'beamWidth', 'aimDst', 'repairSpeed', 'fractionRepairSpeed',
    'targetUnits', 'targetBuildings', 'laserColor', 'healColor', 'hitBuildings',
}

# `bullet = ` / `shoot = ` 出现在行首（允许缩进）。注意不能匹配 `shoot.shots =`
BULLET_LINE_RE = re.compile(r'^[ \t]*bullet[ \t]*=[ \t]*', re.M)
SHOOT_LINE_RE = re.compile(r'^[ \t]*shoot[ \t]*=[ \t]*', re.M)
SCALAR_LINE_RE = re.compile(
    r'^[ \t]*([A-Za-z_][\w.]*)[ \t]*=[ \t]*([^;\n]+);?[ \t]*$', re.M)


def read_value_at(text, pos):
    """从 pos 开始读一个值表达式。

    - 以 new 开头：读到整块 `new Type(...){{...}}` 结束
    - 否则：读到顶层 ';' 为止
    """
    i, n = pos, len(text)
    while i < n and text[i] in ' \t\r\n':
        i += 1
    if text.startswith('new', i) and re.match(r'new\s+[A-Za-z_]', text[i:]):
        op = text.find('(', i)
        if op < 0:
            return text[pos:]
        cp = match_bracket(text, op, '(', ')')
        if cp < 0:
            return text[pos:]
        k = cp + 1
        while k < n and text[k].isspace():
            k += 1
        if k < n and text[k] == '{':
            if k + 1 < n and text[k + 1] == '{':
                k += 1
            e = match_brace(text, k)
            if e > 0:
                k = e + 1
        return text[i:k]
    d = {'(': 0, '[': 0, '{': 0}
    close = {')': '(', ']': '[', '}': '{'}
    while i < n:
        c = text[i]
        if c == '"':
            i = skip_string(text, i)
            continue
        if c in d:
            d[c] += 1
        elif c in close:
            d[close[c]] -= 1
        if c == ';' and all(v == 0 for v in d.values()):
            return text[pos:i]
        i += 1
    return text[pos:]


def parse_weapon_body(body, resolve):
    """解析 weapon 的匿名类体。

    先按顶层语句切（能切多少切多少），再用行首正则兜底 bullet / shoot。

    为什么需要兜底：conquer 与 collaris 的 weapon 体里有一个 for 循环，
    循环体里又嵌套了 Java 双花括号匿名类（parts.add(new RegionPart(...){{ }}))。
    只要有任何一处花括号计数被双花括号带偏，split_top 就再也不会回到 depth 0，
    后面所有语句会被并成一条 —— `bullet = ...` 就此消失。正则兜底不依赖配平。
    """
    w = {'__type': 'Weapon'}

    # 嵌套的 weapons.add(...) 是同一单位注册的额外武器。
    # quell / anthicus / disrupt 都把「死亡爆炸」写在主炮的 bullet 匿名类体里
    # 再 add 一次：
    #     new Weapon("quell-weapon"){{
    #         reload = 55f;
    #         bullet = new BasicBulletType(...){{
    #             weapons.add(new Weapon() {{ reload = 1f; shootOnDeath = true; }});
    #         }}
    #     }}
    # scan_weapons_add 已对全 body 扫描、把嵌套那个单独收进武器列表，
    # 所以这里必须截断 —— 否则嵌套体里的 shootOnDeath 会通过行级兜底泄漏到
    # 外层主炮上，把 quell 主炮（reload=55）误判成死亡爆炸、DPS 归零。
    nest = re.search(r'\bweapons\.add\s*\(', body)
    if nest:
        body = body[:nest.start()]

    # ---- 1. 语句切分（尽力而为）----
    for st in parse_statements(body):
        s = st.strip()
        m = re.match(r'^bullet\s*=\s*(.+)$', s, re.S)
        if m:
            b = resolve_expr(m.group(1), resolve)
            w['bullet'] = b if b is not None else {'__raw': m.group(1).strip()[:300]}
            continue
        m = re.match(r'^shoot\s*=\s*(.+)$', s, re.S)
        if m:
            o = resolve_expr(m.group(1), resolve)
            w['shoot'] = o if o is not None else {'__raw': m.group(1).strip()[:300]}
            continue
        m = re.match(r'^([A-Za-z_][\w.]*)\s*=\s*(.+)$', s, re.S)
        if m:
            k = m.group(1)
            if k in WEAPON_SCALAR_FIELDS:
                w[k] = to_py(m.group(2))
        # 非标量语句（for / parts.add / if ...）忽略

    # ---- 2. bullet / shoot 正则兜底 ----
    if 'bullet' not in w:
        m = BULLET_LINE_RE.search(body)
        if m:
            val = read_value_at(body, m.end())
            b = resolve_expr(val, resolve)
            w['bullet'] = b if b is not None else {'__raw': val.strip()[:300]}
    if 'shoot' not in w:
        m = SHOOT_LINE_RE.search(body)
        if m:
            val = read_value_at(body, m.end())
            o = resolve_expr(val, resolve)
            if o is not None:
                w['shoot'] = o

    # ---- 3. 标量行级兜底 ----
    for m in SCALAR_LINE_RE.finditer(body):
        k = m.group(1)
        if k in WEAPON_SCALAR_FIELDS and k not in w:
            w[k] = to_py(m.group(2))

    return w


def parse_weapon_arg(arg, resolve):
    """weapons.add 的一个参数 -> weapon 字典 或 None。"""
    a = arg.strip()
    if not a:
        return None
    r = parse_new_expr(a, 0)
    if r:
        ty, args, body = r
        w = {'__type': ty, '__args': args}
        if args:
            a0 = args[0].strip()
            if len(a0) >= 2 and a0[0] == '"':
                w['name'] = a0[1:-1]
        if body is not None:
            w.update(parse_weapon_body(body, resolve))
        return w
    # 变量引用（可能是 Weapon 实例）
    m = re.match(r'^([A-Za-z_]\w*)\s*$', a)
    if m:
        o = resolve(m.group(1))
        if isinstance(o, dict):
            return o
    return None


# ============================================================
# 五、单位
# ============================================================
def scan_weapons_add(body):
    """在整个 unit body 里扫描 `weapons.add(...)`，返回所有参数串。

    必须扫全 body 而不是只看顶层语句：anthicus / quad 这类单位把 weapons.add
    写在 for 循环里（循环变量决定挂载点左右镜像），顶层 split_top 根本切不到。
    重叠的匹配用 (op, cp) 去重。
    """
    out = []
    seen = set()
    for m in re.finditer(r'weapons\.add\s*\(', body):
        op = body.index('(', m.start())
        cp = match_bracket(body, op, '(', ')')
        if cp < 0 or (op, cp) in seen:
            continue
        seen.add((op, cp))
        inner = body[op + 1:cp]
        for arg in split_top(inner, ','):
            if arg.strip():
                out.append(arg)
    return out


def parse_unit_body(body):
    stmts = parse_statements(body)
    resolve = make_resolver(stmts)

    u = {'weapons': [], 'misc': []}

    # ---- 武器：全 body 扫描 ----
    for arg in scan_weapons_add(body):
        w = parse_weapon_arg(arg, resolve)
        if w is None:
            u['misc'].append('weapons.add arg 未解析: ' + arg.strip()[:160])
        else:
            u['weapons'].append(w)

    # ---- 单位字段：走顶层语句 ----
    for st in stmts:
        s = st.strip()
        if not s:
            continue
        if s.startswith('weapons'):
            continue
        # 变量声明：只登记，不算字段
        if re.match(r'^(?:var|[A-Z]\w*)\s+[a-z]\w*\s*=', s):
            continue
        m = re.match(r'^([A-Za-z_][\w.]*)\s*=\s*(.+)$', s, re.S)
        if m:
            k, v = m.group(1), m.group(2)
            # 复合赋值 `x = y = 0f`：只取最左，避免把整个表达式当值
            if re.match(r'^[A-Za-z_]\w*\s*=', v):
                continue
            u[k] = to_py(v)
        else:
            u['misc'].append(s[:200])

    return u


UNIT_RE = re.compile(
    r'^[ \t]*([A-Za-z_]\w*)\s*=\s*new\s+(\w*UnitType)\s*\(\s*"([^"]+)"\s*\)', re.M)


def main():
    text = strip_comments(open(SRC, encoding='utf-8').read())
    units, order = {}, []
    for m in UNIT_RE.finditer(text):
        ident, ty, uid = m.group(1), m.group(2), m.group(3)
        j = text.find('{', m.end())
        if j < 0:
            continue
        if j + 1 < len(text) and text[j + 1] == '{':
            j += 1
        end = match_brace(text, j)
        if end < 0:
            print('WARN 括号未配平: %s' % uid, file=sys.stderr)
            continue
        u = parse_unit_body(text[j + 1:end])
        u['__ident'] = ident
        u['__class'] = ty
        u['id'] = uid
        u['__line'] = text[:m.start()].count('\n') + 1
        units[uid] = u
        order.append(uid)

    dest = os.path.normpath(os.path.join(
        os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'vanilla_units.json'))
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, 'w', encoding='utf-8') as f:
        json.dump({'source': SRC, 'count': len(units),
                   'order': order, 'units': units},
                  f, ensure_ascii=False, indent=1)

    print('解析出 %d 个单位 -> %s' % (len(units), dest))
    print()
    print('%-18s %-18s %7s %7s %9s %9s' %
          ('id', 'class', 'weapons', 'bullet', 'health', 'armor'))
    print('-' * 74)
    no_bullet = []
    for uid in order:
        u = units[uid]
        ws = u.get('weapons', [])
        nb = sum(1 for w in ws if 'bullet' not in w)
        if nb:
            no_bullet.append((uid, nb, len(ws)))
        print('  %-18s %-18s %7d %7d %9s %9s' % (
            uid, u.get('__class'), len(ws), nb,
            u.get('health'), u.get('armor')))
    print()
    if no_bullet:
        print('!! 有 weapon 缺 bullet 的单位: %s' % no_bullet)
    else:
        print('全部 weapon 都解析出 bullet')
    return 0


if __name__ == '__main__':
    sys.exit(main())