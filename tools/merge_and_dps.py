#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""合并「原版数值」与「数据包改动」，算出生效数值与 DPS，产出站点数据。

输入
----
  data/vanilla_units.json   由 parse_java_units.py 从 UnitTypes.java 提取
  data/datapack.json        由 hjson_datapack.py 从 8 个补丁包提取

输出
----
  docs/public/data/units.json      每个单位的完整记录（含 diff 与 DPS）
  docs/public/data/buildings.json  每个建筑的完整记录
  docs/public/data/index.json      索引（分类、作者、星级、DPS 排序）

DPS 公式（源自源码，非估算）
---------------------------
常规武器（Weapon.java:446  `mount.reload = reload`；
          ShootPattern.java:23-25  `for i<shots: shoot(..., firstShotDelay + shotDelay*i)`）

    每轮扣扳机打出 shots 发，随后 reload tick 冷却。

    单发伤害 = bullet.damage
    单武器 DPS = shots × damage × 60 / reload

持续光束（PointLaserBulletType.java:49-50  `damage / damageInterval * 60f`）

    单武器 DPS = damage / damageInterval × 60

溅射（splashDamage）不计入单体 DPS，单独列出。
"""
import os, re, json, sys, collections

HOME = os.path.expanduser('~')
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
DATA = os.path.join(ROOT, 'data')
PUB  = os.path.join(ROOT, 'docs', 'public', 'data')
UNIT_DIR = os.path.join(HOME, 'Downloads', '数据包单位总览')
BUNDLE = os.path.join(HOME, 'Downloads', 'Mindustry-master',
                      'core', 'assets', 'bundles', 'bundle_zh_CN.properties')

TICKS = 60.0   # 一秒的 tick 数

# ---------------- 分类 ----------------
S_UNIT_DIRS = ['陆军类-S', '陆辅类-S', '爬行类-S', '飞机类-S',
               '空辅类-S', '海军类-S', '海辅类-S']
E_UNIT_DIRS = ['坦克类-E', '机甲类-E', '飞船类-E']
S_CORE = {'alpha', 'beta', 'gamma'}
E_CORE = {'evoke', 'incite', 'emanate'}

CATEGORY_LABEL = {
    '陆军类-S': '陆军（赛普罗）', '陆辅类-S': '陆辅（赛普罗）',
    '爬行类-S': '爬行（赛普罗）', '飞机类-S': '飞机（赛普罗）',
    '空辅类-S': '空辅（赛普罗）', '海军类-S': '海军（赛普罗）',
    '海辅类-S': '海辅（赛普罗）', '核心机-S＆E': '核心机',
    '坦克类-E': '坦克（埃里克尔）', '机甲类-E': '机甲（埃里克尔）',
    '飞船类-E': '飞船（埃里克尔）', '未知类-O.o': '未知',
}

# ---------------- 读中文名 ----------------
zh_unit, zh_block = {}, {}
if os.path.exists(BUNDLE):
    for line in open(BUNDLE, encoding='utf-8'):
        m = re.match(r'^unit\.([a-z0-9\-]+)\.name\s*=\s*(.+)$', line.strip())
        if m:
            zh_unit[m.group(1)] = m.group(2)
        m = re.match(r'^block\.([a-z0-9\-]+)\.name\s*=\s*(.+)$', line.strip())
        if m:
            zh_block[m.group(1)] = m.group(2)

# ---------------- 从单文件目录取「分类 / 中文名 / 作者」 ----------------
def scan_units_dir():
    """返回 {unit_id: {category, label, author, star}}"""
    out = {}
    for root, dirs, fs in os.walk(UNIT_DIR):
        for f in fs:
            if not f.endswith('.hjson'):
                continue
            p = os.path.join(root, f)
            rel = os.path.relpath(p, UNIT_DIR).replace(os.sep, '/')
            if rel.startswith('_') or '/' not in rel:
                continue
            txt = open(p, encoding='utf-8').read().split('\n')
            m = re.match(r'^//\s*(unit|block|status)\.([A-Za-z0-9_\-]+)', txt[0]) if txt else None
            if not m:
                continue
            kind, uid = m.group(1), m.group(2)
            lm = re.search(r'「(.+?)」', txt[0])
            label = lm.group(1) if lm else ''
            top = rel.split('/')[0]
            if kind == 'unit':
                if top == '核心机-S＆E':
                    cat = top
                    star = 'S' if uid in S_CORE else ('E' if uid in E_CORE else '?')
                elif top in S_UNIT_DIRS:
                    cat, star = top, 'S'
                elif top in E_UNIT_DIRS:
                    cat, star = top, 'E'
                else:
                    cat, star = '未知类-O.o', '?'
                out[uid] = dict(kind=kind, category=cat,
                                category_label=CATEGORY_LABEL.get(cat, cat),
                                label=label or zh_unit.get(uid, uid),
                                star=star,
                                author=('UT' if star == 'S' else 'UP' if star == 'E' else '?'))
    return out


UNIT_META = scan_units_dir()

# 建筑 → 星（从目录推断）
BLOCK_STAR = {}
for root, dirs, fs in os.walk(os.path.join(UNIT_DIR, '建筑修改类-S＆E')):
    for f in fs:
        if not f.endswith('.hjson'):
            continue
        rel = os.path.relpath(os.path.join(root, f),
                              os.path.join(UNIT_DIR, '建筑修改类-S＆E'))
        txt = open(os.path.join(root, f), encoding='utf-8').read().split('\n')
        m = re.match(r'^//\s*block\.([A-Za-z0-9_\-]+)', txt[0]) if txt else None
        if not m:
            continue
        star = 'S' if rel.startswith('S星') else ('E' if rel.startswith('E星') else '?')
        kind = '炮塔' if '炮塔' in rel else ('墙体' if '墙体' in rel else '其他')
        BLOCK_STAR[m.group(1)] = (star, kind)


# ============================================================
# 补丁应用
# ============================================================
def get_at(obj, segs):
    cur = obj
    for s in segs:
        if isinstance(cur, dict):
            if s not in cur:
                return None
            cur = cur[s]
        elif isinstance(cur, list):
            try:
                cur = cur[int(s)]
            except (ValueError, IndexError):
                return None
        else:
            return None
    return cur


def set_path(root, segs, value):
    """按点号路径写入 root。

    segs 的最后一段含义：
      '数字'   → 写入该下标（数组不够长则补位）
      '+'      → 追加（list 尾部 / dict 用自增数字键）
      其它     → 普通键

    中间段遇到 list 时用数字下标索引，遇到 '+' 视为追加目标。

    v2 的 bug：apply_patch 把 `weapons.+` 拆成 set_at(unit, ['weapons'], ...)，
    于是整个 weapons 数组被替换掉，原版武器全丢（reign 因此只剩数据包追加的
    那门武器）。v3 让 set_path 自己识别末段的 '+'。
    """
    if not segs:
        return False
    cur = root
    for i, s in enumerate(segs[:-1]):
        nxt = segs[i + 1]
        want_list = nxt.isdigit() or nxt == '+'
        if isinstance(cur, dict):
            if s not in cur or not isinstance(cur[s], (dict, list)):
                cur[s] = [] if want_list else {}
            cur = cur[s]
        elif isinstance(cur, list):
            if not s.isdigit():
                return False
            idx = int(s)
            while len(cur) <= idx:
                cur.append([] if want_list else {})
            if not isinstance(cur[idx], (dict, list)):
                cur[idx] = [] if want_list else {}
            cur = cur[idx]
        else:
            return False

    last = segs[-1]
    if isinstance(cur, list):
        if last == '+':
            if isinstance(value, list):
                cur.extend(value)
            else:
                cur.append(value)
            return True
        if last.isdigit():
            idx = int(last)
            while len(cur) <= idx:
                cur.append(None)
            cur[idx] = value
            return True
        return False
    if isinstance(cur, dict):
        if last == '+':
            n = 0
            while str(n) in cur:
                n += 1
            cur[str(n)] = value
            return True
        cur[last] = value
        return True
    return False


def apply_patch(unit, bucket):
    """把数据包 bucket（{path_str: value}）应用到 unit 字典。

    `+` 追加必须**先归并再追加**。

    数据包里新增一门武器是拆成几十条独立路径写的：

        weapons.+.name           "plasma-laser-mount"
        weapons.+.reload         170
        weapons.+.bullet.damage  16.5
        weapons.+.bullet.speed   12
        ...

    它们全都指向**同一个**待追加的武器对象。逐条 set_path 会在中间段遇到
    `+` 而失败（或退化成写进 weapons['+'] 这种垃圾键），结果是追加出一堆
    只有 reload 没有伤害的空壳 —— scepter / navanax / gamma 的幽灵武器
    就是这么来的。

    正确做法：按 `+` 之前的前缀分组，把同一组的 rest 路径拼成一个完整对象，
    最后整体追加一次。
    """
    grouped = collections.OrderedDict()   # head(tuple) -> {rest(tuple): value}
    plain = []

    for path_str, val in bucket.items():
        segs = [s for s in path_str.split('.') if s]
        if not segs:
            continue
        if '+' in segs:
            i = segs.index('+')
            head = tuple(segs[:i])
            rest = tuple(segs[i + 1:])
            grouped.setdefault(head, collections.OrderedDict())[rest] = val
        else:
            plain.append((segs, val))

    # 普通路径先写
    for segs, val in plain:
        set_path(unit, segs, val)

    # 追加目标整体构造后追加
    for head, rest_map in grouped.items():
        items = []
        full = rest_map.get(())
        if full is not None:
            # `weapons.+` 直接给了整个对象或数组
            if isinstance(full, list):
                items.extend(full)
            elif isinstance(full, dict):
                items.append(full)
        # 其余是 `weapons.+.字段` 形式，拼成一个对象
        obj = {}
        for rest, val in rest_map.items():
            if not rest:
                continue
            set_path(obj, list(rest), val)
        if obj:
            items.append(obj)

        for it in items:
            set_path(unit, list(head) + ['+'], it)


# ============================================================
# DPS
# ============================================================
LASER_TYPES = {'PointLaserBulletType', 'ContinuousLaserBulletType',
               'ContinuousFlameBulletType', 'SapBulletType'}


def num(v, d=0.0):
    if isinstance(v, bool):
        return d
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        try:
            return float(v)
        except ValueError:
            return d
    return d


# 非持续输出型武器：不计入 DPS
WEAPON_ROLE = {
    'PointDefenseWeapon': 'pointDefense',
    'PointDefenseBulletWeapon': 'pointDefense',
    'RepairBeamWeapon': 'support',
    'RepairTowerWeapon': 'support',
    'BuildWeapon': 'support',
    'MineWeapon': 'support',
    'WarheadWeapon': 'warhead',
}


def type_of(d, default):
    """取对象的类型名。

    Java 源码侧用 `__type`，hjson/JSON 数据包侧用 `type`。合并后同一个 dict 里
    两个键可能同时存在 —— 此时**数据包必须优先**，因为它才是最终生效的覆盖值。
    曾经写成 `__type or type`，导致 merui 这类「数据包把弹种从 ArtilleryBulletType
    换成 PointLaserBulletType」的单位仍按原版弹种算 DPS。
    """
    if not isinstance(d, dict):
        return default
    v = d.get('type')
    if isinstance(v, str) and v:
        return v
    v = d.get('__type')
    if isinstance(v, str) and v:
        return v
    return default


MAX_FRAG_DEPTH = 3


def bullet_profile(bullet, depth=0):
    """算一颗子弹「单发」造成的直伤与溅射。

    一次扣扳机打出的伤害不只有主弹，还包括这些派生伤害，递归累加：

      分裂子母弹 fragBullet × fragBullets （可再分裂，深度上限 MAX_FRAG_DEPTH）
      间隔弹     intervalBullet × intervalBullets × 寿命内的生成次数
      电弧       lightning 条，每条 lightningDamage（负值取主弹伤害）

    返回 (direct, splash)。
    """
    if not isinstance(bullet, dict) or depth > MAX_FRAG_DEPTH:
        return 0.0, 0.0

    own = num(bullet.get('damage'), 0.0)
    direct = own
    splash = num(bullet.get('splashDamage'), 0.0)

    # 分裂子母弹
    n = int(num(bullet.get('fragBullets'), 0) or 0)
    frag = bullet.get('fragBullet')
    if n > 0 and isinstance(frag, dict):
        fd, fs = bullet_profile(frag, depth + 1)
        direct += n * fd
        splash += n * fs

    # 间隔弹：BulletType.updateBulletInterval()，飞行期间每 bulletInterval
    # （默认 20 tick）生成 intervalBullets 枚，但要等 b.time >= intervalDelay
    # 才开始（intervalDelay 默认 -1，源码注释即「负值表示不延迟」）。
    iv = bullet.get('intervalBullet')
    if isinstance(iv, dict):
        cnt = int(num(bullet.get('intervalBullets'), 1) or 1)
        gap = num(bullet.get('bulletInterval'), 20.0) or 20.0
        life = num(bullet.get('lifetime'), 0.0)
        delay = num(bullet.get('intervalDelay'), -1.0)
        if delay < 0:
            delay = 0.0
        events = int((life - delay) // gap) if (life > delay and gap > 0) else 0
        if cnt > 0 and events > 0:
            idd, iss = bullet_profile(iv, depth + 1)
            direct += cnt * events * idd
            splash += cnt * events * iss

    # 电弧：BulletType.hit() 里 `for(i < lightning) Lightning.create(...)`，
    # 每次命中派生 lightning 条电弧。指定了 lightningType 就按那颗子弹递归算，
    # 否则每条造成 lightningDamage（负值取主弹伤害）。
    # 电弧沿路径会同时命中多个目标，所以归入「范围」而非单体。
    lb = int(num(bullet.get('lightning'), 0) or 0)
    if lb > 0:
        lt = bullet.get('lightningType')
        if isinstance(lt, dict):
            l_d, l_s = bullet_profile(lt, depth + 1)
            splash += lb * (l_d + l_s)
        else:
            ld = num(bullet.get('lightningDamage'), -1.0)
            if ld < 0:
                ld = own
            splash += lb * ld

    return direct, splash


def compute_weapon_dps(w, unit_is_projectile=False):
    """返回单个武器的 DPS 明细。

    unit_is_projectile=True 表示这个「单位」其实是弹体（MissileUnitType，
    如 anthicus-missile / disrupt-missile / quell-missile）。它们的 weapons
    是战斗部，命中即炸，没有「每秒输出」的概念。
    """
    bullet = w.get('bullet') if isinstance(w.get('bullet'), dict) else {}
    btype = type_of(bullet, 'BulletType')
    wtype = type_of(w, 'Weapon')
    role = WEAPON_ROLE.get(wtype, 'damage')

    reload_raw = w.get('reload')
    reload_explicit = reload_raw is not None

    # 源码里有一类 reload 无法静态求值，例如 vanquish 的
    #   `reload = 22 + fi * 5;`   （fi 是 for 循环变量，每门炮递增）
    # num() 对字符串返回 0，再被 `or 1.0` 兜成 1 tick —— DPS 会算成
    # damage × 60 这种荒谬值（vanquish 曾因此报 3112.5）。
    # 识别出这种情况后不报 DPS，只报单发伤害。
    reload_known = not isinstance(reload_raw, str)
    reload = num(reload_raw, 1.0) or 1.0

    # 死亡触发的爆炸（源码 shootOnDeath = true）与弹体战斗部一样，
    # 只该报单发伤害 —— 否则 damage*60 会算出 disrupt 8575 这种荒谬数字。
    #
    # 判据：直接看 `shootOnDeath`。
    #
    # 早期这里还加了 `reload <= 1.5` 的附加条件，那是为了绕开一个解析 bug
    # （shootOnDeath 从嵌套武器泄漏到主炮）。泄漏已在解析器侧修好
    # （parse_weapon_body 遇嵌套 weapons.add 即截断），附加条件于是变成误判源：
    # crawler 是 shootOnDeath 且 reload=24 的殉爆单位，因为不满足阈值
    # 被当成持续输出，一度混进总量榜第 6 名。
    death_blast = bool(w.get('shootOnDeath'))
    if role == 'damage' and (unit_is_projectile or death_blast):
        role = 'warhead'

    shoot = w.get('shoot') if isinstance(w.get('shoot'), dict) else {}
    shots = int(num(shoot.get('shots'), 1) or 1)
    shot_delay = num(shoot.get('shotDelay'), 0.0)
    first_delay = num(shoot.get('firstShotDelay'), 0.0)

    damage = num(bullet.get('damage'), 0.0)
    splash = num(bullet.get('splashDamage'), 0.0)
    splash_r = num(bullet.get('splashDamageRadius'), -1.0)

    # 含分裂子母弹的完整单发伤害
    prof_direct, prof_splash = bullet_profile(bullet)
    frag_n = int(num(bullet.get('fragBullets'), 0) or 0)
    frag_bullet = bullet.get('fragBullet') if isinstance(bullet.get('fragBullet'), dict) else None
    frag_direct = frag_splash = 0.0
    if frag_n and frag_bullet:
        frag_direct, frag_splash = bullet_profile(frag_bullet, 1)
        frag_direct *= frag_n
        frag_splash *= frag_n

    continuous = bool(w.get('continuous')) or btype in LASER_TYPES

    if btype in ('PointLaserBulletType', 'ContinuousLaserBulletType',
                 'ContinuousFlameBulletType'):
        di = num(bullet.get('damageInterval'), 5.0) or 5.0
        dps = damage / di * TICKS
        shots_eff = 1
        mode = 'continuous'
    elif btype == 'SapBulletType':
        di = num(bullet.get('damageInterval'), 5.0) or 5.0
        dps = damage / di * TICKS
        shots_eff = 1
        mode = 'continuous'
    else:
        # 常规武器**只算直伤**。此前这里写的是
        #     eff_damage = damage if damage else splash
        # 也就是「没有直伤就拿溅射顶替」，结果纯溅射武器（conquer-shockwave
        # 是 damage=0 / splashDamage=440）被算进单体榜，越靠后虚高越离谱。
        # 现在溅射单独统计，另立榜单。
        dps = shots * prof_direct * TICKS / reload
        shots_eff = shots
        mode = 'burst'

    # 单发伤害：直伤与溅射分开，均含分裂子母弹
    per_shot = shots_eff * prof_direct
    per_shot_splash = shots_eff * prof_splash

    # 穿透只作信息展示，**不折算成 DPS**。
    # 源码：pierce 是 boolean（BulletType.java:53），pierceCap 是穿透上限（:57），
    # pierceDamageFactor 默认 0f，语义是「每穿透一点生命值降低的伤害倍率」（:59）
    # —— 不是逐目标衰减系数，拿它算群体倍率是错的。
    pierce = bool(bullet.get('pierce'))
    pierce_cap = bullet.get('pierceCap')
    pierce_factor = bullet.get('pierceDamageFactor')

    # 穿透只作信息展示，**不折算成 DPS**。
    # 源码：pierce 是 boolean（BulletType.java:53），pierceCap 是上限（:57），
    # pierceDamageFactor 默认 0f 且语义是「每穿透一点生命值降低的伤害倍率」
    # （:59），不是逐目标衰减系数 —— 拿它算倍率是错的。

    # ammoPerShot：每发消耗多少弹药（默认 1），不影响 DPS 但影响弹药经济
    ammo_per_shot = int(num(w.get('ammoPerShot'), 1) or 1)

    if role != 'damage':
        dps = None
    elif not reload_explicit or not reload_known:
        dps = None
        mode = 'oneshot'

    # 弹种对空/对地
    collides_air = bullet.get('collidesAir', True) is not False
    collides_ground = bullet.get('collidesGround', True) is not False
    if bullet.get('collides') is False:
        collides_air = collides_ground = False

    # 射程（tick × speed）
    speed = num(bullet.get('speed'), 0.0)
    lifetime = num(bullet.get('lifetime'), 0.0)
    bullet_range = speed * lifetime if (speed and lifetime) else None
    range_override = bullet.get('rangeOverride')
    if range_override is not None:
        bullet_range = num(range_override)

    splash_dps = None
    if prof_splash and reload_explicit and reload_known and role == 'damage':
        splash_dps = round(shots_eff * prof_splash * TICKS / reload, 2)

    return dict(
        name=w.get('name') or '(未命名)',
        weaponType=wtype,
        role=role,
        bulletType=btype,
        mode=mode,
        reload=reload,
        reloadSec=round(reload / TICKS, 3),
        reloadExplicit=reload_explicit,
        shots=shots_eff,
        shotDelay=shot_delay,
        firstShotDelay=first_delay,
        damage=damage,
        splashDamage=splash,
        splashDamageRadius=splash_r,
        # 含分裂子母弹的完整单发伤害（主弹 + fragBullets × 每颗）
        perShotDirect=round(per_shot, 2),
        perShotSplash=round(per_shot_splash, 2),
        fragBullets=frag_n,
        fragDirect=round(frag_direct, 2),
        fragSplash=round(frag_splash, 2),
        dps=round(dps, 2) if dps is not None else None,
        perShot=round(per_shot, 2),
        splashDps=splash_dps,
        collidesAir=collides_air,
        collidesGround=collides_ground,
        bulletRange=round(bullet_range, 1) if bullet_range else None,
        continuous=continuous,
        # 新增字段
        ammoPerShot=ammo_per_shot,
        pierce=pierce,
        pierceCap=(int(pierce_cap) if isinstance(pierce_cap, (int, float)) else None),
        pierceDamageFactor=(num(pierce_factor) if pierce_factor is not None else None),
        pierceArmor=bullet.get('pierceArmor', False),
        armorPiercing=bullet.get('armorPiercing', False),
        raw=w,
    )


def unit_dps(unit):
    """单位的总 DPS / 对空 DPS / 对地 DPS。"""
    ws = unit.get('weapons') or []
    details = [compute_weapon_dps(w) for w in ws if isinstance(w, dict)]
    if not details:
        return dict(weapons=[], direct=0.0, splash=0.0, total=0.0,
                    air=0.0, ground=0.0, suicide=False, airGroundOnly=False)

    target_air = unit.get('targetAir', True) is not False
    target_ground = unit.get('targetGround', True) is not False

    def v(d):
        return d['dps'] if isinstance(d['dps'], (int, float)) else 0.0

    def sp(d):
        return d['splashDps'] if isinstance(d['splashDps'], (int, float)) else 0.0

    # 一门持续输出武器都没有、只能靠死亡爆炸造成伤害的单位（如 crawler）
    suicide = bool(details) and all(
        d['role'] in ('warhead', 'support', 'pointDefense') for d in details)

    direct = sum(v(d) for d in details)
    splash = sum(sp(d) for d in details)
    air = sum(v(d) for d in details if d['collidesAir']) if target_air else 0.0
    ground = sum(v(d) for d in details if d['collidesGround']) if target_ground else 0.0

    for d in details:
        d['canHitAir'] = bool(target_air and d['collidesAir'])
        d['canHitGround'] = bool(target_ground and d['collidesGround'])

    return dict(
        weapons=details,
        # 单体 DPS（直伤，含分裂弹全命中）
        direct=round(direct, 2),
        # 范围 DPS（溅射，含分裂弹的溅射）
        splash=round(splash, 2),
        # 理论总量 = 单体 + 范围
        total=round(direct + splash, 2),
        air=round(air, 2),
        ground=round(ground, 2),
        suicide=suicide,
        targetAir=target_air,
        targetGround=target_ground,
        airGroundOnly=(target_air and not target_ground),
    )


# ============================================================
# 建筑（炮塔）DPS
# ============================================================
VAN_BLOCKS_PATH = os.path.join(DATA, 'vanilla_blocks.json')


def load_vanilla_blocks():
    """原版炮塔的装填与弹药基准。数据包对建筑的改动是稀疏补丁，
    多数条目没有 reload，必须回到源码取基准才能算 DPS。"""
    if not os.path.exists(VAN_BLOCKS_PATH):
        return {}
    with open(VAN_BLOCKS_PATH, encoding='utf-8') as f:
        return json.load(f).get('blocks', {})


def ammo_key(s):
    """Items.silicon / "silicon" / silicon -> silicon"""
    s = str(s).strip().strip('"')
    return s.split('.')[-1] if '.' in s else s


def merge_node(base, over):
    """把数据包的覆盖合并进原版节点；两边都是 dict 时逐字段合。"""
    out = dict(base) if isinstance(base, dict) else {}
    if isinstance(over, dict):
        for k, v in over.items():
            if isinstance(v, dict) and isinstance(out.get(k), dict):
                out[k] = merge_node(out[k], v)
            else:
                out[k] = v
    return out


# 持续型弹种：不吃 reload，按 damageInterval 结算
CONTINUOUS_BTYPES = {
    'PointLaserBulletType', 'ContinuousLaserBulletType', 'ContinuousFlameBulletType',
    'ContinuousBulletType', 'SapBulletType', 'LightningBulletType',
}


def _row_dps(reload_v, shots, merged, d, sp):
    """把单发伤害折成 DPS。

    两条路径：
      - 有 reload 的常规炮塔：shots × 伤害 × 60 / reload
      - 持续型炮塔（lustre / sublimate）：damage / damageInterval × 60
    都不是则返回 None（例如纯推液的 wave/tsunami 液体弹药没有伤害字段）。
    """
    btype = merged.get('type') or merged.get('__type') or ''
    if reload_v:
        return (round(shots * d * TICKS / reload_v, 2),
                round(shots * sp * TICKS / reload_v, 2), 'burst')
    if btype in CONTINUOUS_BTYPES:
        di = num(merged.get('damageInterval'), 5.0) or 5.0
        return (round(d / di * TICKS, 2), round(sp / di * TICKS, 2), 'continuous')
    return None


def building_dps(bid, patch, van_blocks):
    """算一个炮塔各弹药的 DPS；不可计算时返回 None。"""
    vb = van_blocks.get(bid)
    if not vb:
        return None

    # 注意：持续型炮塔没有 reload，不能在这里就放弃 —— 交给 _row_dps 判断
    reload_v = num(patch.get('reload', vb.get('reload')), 0.0)

    shoot = patch.get('shoot')
    if not isinstance(shoot, dict):
        shoot = vb.get('shoot')
    if not isinstance(shoot, dict):
        shoot = {}
    shots = int(num(shoot.get('shots'), 1) or 1)

    patch_ammo = patch.get('ammoTypes')
    patch_ammo = ({ammo_key(k): v for k, v in patch_ammo.items() if isinstance(v, dict)}
                  if isinstance(patch_ammo, dict) else {})

    rows = []
    for item, bullet in (vb.get('ammo') or []):
        if not isinstance(bullet, dict):
            continue
        key = ammo_key(item)
        merged = merge_node(bullet, patch_ammo.get(key))
        d, sp = bullet_profile(merged)
        calc = _row_dps(reload_v, shots, merged, d, sp)
        if calc is None:
            continue
        rd, rs, mode = calc
        rows.append(dict(
            item=key,
            damage=round(num(merged.get('damage'), 0.0), 2),
            splashDamage=round(num(merged.get('splashDamage'), 0.0), 2),
            perShot=round(shots * d, 2),
            direct=rd,
            splash=rs,
            mode=mode,
        ))

    # 激光 / 电力炮台没有弹药表，用 shootType 当唯一弹种
    if not rows and isinstance(vb.get('shootType'), dict):
        merged = merge_node(vb['shootType'],
                            patch.get('shootType') if isinstance(patch.get('shootType'), dict) else {})
        d, sp = bullet_profile(merged)
        calc = _row_dps(reload_v, shots, merged, d, sp)
        if calc is None:
            return None
        rd, rs, mode = calc
        rows.append(dict(
            item='(默认弹种)',
            damage=round(num(merged.get('damage'), 0.0), 2),
            splashDamage=round(num(merged.get('splashDamage'), 0.0), 2),
            perShot=round(shots * d, 2),
            direct=rd,
            splash=rs,
            mode=mode,
        ))

    if not rows:
        return None

    best = max(rows, key=lambda r: r['direct'] + r['splash'])
    return dict(
        mode=rows[0]['mode'],
        reload=round(reload_v, 2) if reload_v else None,
        reloadSec=round(reload_v / TICKS, 3) if reload_v else None,
        shots=shots,
        ammo=rows,
        best=dict(item=best['item'],
                  direct=best['direct'],
                  splash=best['splash'],
                  total=round(best['direct'] + best['splash'], 2)),
        directMax=max(r['direct'] for r in rows),
        splashMax=max(r['splash'] for r in rows),
        totalMax=max(r['direct'] + r['splash'] for r in rows),
    )


# ============================================================
# 主流程
# ============================================================
def main():
    van = json.load(open(os.path.join(DATA, 'vanilla_units.json'), encoding='utf-8'))
    vanilla_units = van['units']

    packs = json.load(open(os.path.join(DATA, 'datapack.json'), encoding='utf-8'))

    # 收集每个实体在哪些包里出现
    ent_packs = collections.defaultdict(list)
    for pack_name, pk in packs.items():
        for key in pk['entities']:
            ent_packs[key].append(pack_name)

    # 合并所有包的补丁（后写的覆盖先写的；同值不影响）
    merged_patch = {}
    for pack_name, pk in packs.items():
        for key, bucket in pk['entities'].items():
            merged_patch.setdefault(key, {}).update(bucket)

    units_out = []
    for key, bucket in sorted(merged_patch.items()):
        kind, uid = key.split('.', 1)
        if kind != 'unit':
            continue
        base = json.loads(json.dumps(vanilla_units.get(uid, {})))
        if not base:
            base = {}
        base['id'] = uid
        apply_patch(base, bucket)

        meta = UNIT_META.get(uid, {})
        label = meta.get('label') or zh_unit.get(uid, uid)

        # 描述里的 T 级
        desc = base.get('description', '') or ''
        if not isinstance(desc, str):
            desc = str(desc)
        tm = re.search(r'T(\d)\s*级', desc)
        tier = int(tm.group(1)) if tm else None

        vbase = vanilla_units.get(uid, {})
        dps = unit_dps(base)

        # 原版 DPS 对照
        vdps = unit_dps(vbase) if vbase else dict(total=0, air=0, ground=0, weapons=[])

        def pick(d, k, default=None):
            v = d.get(k)
            return v if v is not None else default

        rec = dict(
            id=uid,
            nameZh=label,
            nameEn=(base.get('name') if isinstance(base.get('name'), str) else None) or uid,
            star=meta.get('star', '?'),
            author=meta.get('author', '?'),
            category=meta.get('category'),
            categoryLabel=meta.get('category_label'),
            tier=tier,
            unitClass=base.get('__class', ''),
            isSubUnit=uid.endswith('-missile'),
            packs=sorted(set(ent_packs.get(key, []))),
            description=desc,
            stats=dict(
                health=pick(base, 'health'),
                armor=pick(base, 'armor', 0),
                speed=pick(base, 'speed'),
                hitSize=pick(base, 'hitSize'),
                range=pick(base, 'range'),
                maxRange=pick(base, 'maxRange'),
                targetAir=pick(base, 'targetAir', True),
                targetGround=pick(base, 'targetGround', True),
                fogRadius=pick(base, 'fogRadius'),
                payloadCapacity=pick(base, 'payloadCapacity'),
            ),
            vanillaStats=dict(
                health=pick(vbase, 'health'),
                armor=pick(vbase, 'armor', 0),
                speed=pick(vbase, 'speed'),
                hitSize=pick(vbase, 'hitSize'),
                range=pick(vbase, 'range'),
                maxRange=pick(vbase, 'maxRange'),
            ),
            dps=dict(direct=dps['direct'], splash=dps['splash'], total=dps['total'],
                     air=dps['air'], ground=dps['ground'],
                     suicide=dps.get('suicide', False),
                     targetAir=dps.get('targetAir', True),
                     targetGround=dps.get('targetGround', True)),
            vanillaDps=dict(direct=vdps.get('direct', 0.0), splash=vdps.get('splash', 0.0),
                            total=vdps['total'], air=vdps['air'], ground=vdps['ground']),
            weapons=[{k: v for k, v in d.items() if k != 'raw'} for d in dps['weapons']],
            abilities=[a for a in (base.get('abilities') or []) if isinstance(a, dict)],
            parts=base.get('parts') or [],
            description_en=None,
            raw=base,
        )
        units_out.append(rec)

    # 建筑
    blocks_out = []
    van_blocks = load_vanilla_blocks()
    for key, bucket in sorted(merged_patch.items()):
        kind, bid = key.split('.', 1)
        if kind != 'block':
            continue
        base = {}
        apply_patch(base, bucket)
        star, cat = BLOCK_STAR.get(bid, ('?', '其他'))
        blocks_out.append(dict(
            id=bid,
            nameZh=zh_block.get(bid, bid),
            star=star,
            author='UT' if star == 'S' else ('UP' if star == 'E' else '?'),
            category=cat,
            packs=sorted(set(ent_packs.get(key, []))),
            isTurret=bool(van_blocks.get(bid)),
            dps=building_dps(bid, base, van_blocks),
            raw=base,
        ))

    os.makedirs(PUB, exist_ok=True)
    json.dump(units_out, open(os.path.join(PUB, 'units.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    json.dump(blocks_out, open(os.path.join(PUB, 'buildings.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)

    # 索引
    by_cat = collections.defaultdict(list)
    for u in units_out:
        by_cat[u['categoryLabel'] or '未分类'].append(u['id'])
    # 三份榜单：单体（直伤）、范围（溅射）、总量。
    # 副单位（-missile 战斗部）一律剔除 —— 它们的 DPS 语义是「命中即炸」，
    # 混进榜单会把真正的作战单位全挤下去。
    # 殉爆单位（crawler 之类）没有持续输出，值为 0 只是噪声，一并剔出榜单
    ranked = [x for x in units_out
              if not x.get('isSubUnit') and not x['dps'].get('suicide')]
    top_total = sorted(ranked, key=lambda x: -x['dps']['total'])[:15]
    top_direct = sorted(ranked, key=lambda x: -x['dps']['direct'])[:15]
    top_splash = sorted(ranked, key=lambda x: -x['dps']['splash'])[:15]
    idx = dict(
        unitCount=len(units_out),
        blockCount=len(blocks_out),
        vanillaCount=van['count'],
        categories={k: v for k, v in sorted(by_cat.items())},
        # 副单位（-missile 战斗部）不参与排行：它们的 DPS 语义是「命中即炸」，
        # 混进榜单会把真正的作战单位全挤下去（曾经前两名是 disrupt-missile
        # 19200 与 quell-missile 14400）。
        topDps=[dict(id=x['id'], name=x['nameZh'], dps=x['dps']['total'])
                for x in top_total],
        topDirect=[dict(id=x['id'], name=x['nameZh'], dps=x['dps']['direct'])
                   for x in top_direct],
        topSplash=[dict(id=x['id'], name=x['nameZh'], dps=x['dps']['splash'])
                   for x in top_splash],
        units=[dict(id=u['id'], nameZh=u['nameZh'], star=u['star'], author=u['author'],
                    category=u['categoryLabel'], tier=u['tier'],
                    dps=u['dps']['total'], air=u['dps']['air'],
                    ground=u['dps']['ground'],
                    direct=u['dps']['direct'], splash=u['dps']['splash'],
                    isSubUnit=u.get('isSubUnit', False),
                    suicide=u['dps'].get('suicide', False),
                    health=u['stats']['health']) for u in units_out],
        blocks=[dict(id=b['id'], nameZh=b['nameZh'], star=b['star'],
                     author=b['author'], category=b['category']) for b in blocks_out],
    )
    json.dump(idx, open(os.path.join(PUB, 'index.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)

    # ---------------- 报告 ----------------
    print('单位 %d 个 / 建筑 %d 个 -> %s' % (len(units_out), len(blocks_out), PUB))
    print()
    print('%-16s %-6s %-6s %-4s %8s %8s %8s %8s' %
          ('id', '中文', '作者', 'T', 'HP', '总DPS', '对空', '原版DPS'))
    print('-' * 78)
    for u in sorted(units_out, key=lambda x: (x['star'], x['category'] or '', -(x['tier'] or 0))):
        print('%-16s %-6s %-6s %-4s %8s %8.1f %8.1f %8.1f' % (
            u['id'], u['nameZh'], u['author'], u['tier'] or '-',
            u['stats']['health'], u['dps']['total'], u['dps']['air'],
            u['vanillaDps']['total']))
    return 0


if __name__ == '__main__':
    sys.exit(main())