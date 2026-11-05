#!/usr/bin/env python3
"""RUAX WAD18 Loan Amortization - Reproducibility Capsule runner."""
import ast, copy, hashlib, json, os, platform, sys
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "amort.py")
W = 10**18
def R(a, b): return W * a // b

VECTORS = [
    ["parse", "0"], ["parse", "1"], ["parse", "0.5"],
    ["parse", "12.345678901234567890"], ["parse", "0.1234567890123456789"],
    ["parse", "7."], ["parse", "123456789.000000000000000001"],
    ["parse", ".5"], ["parse", "-1"], ["parse", "1.-5"], ["parse", "abc"],
    ["amortize", 250000 * W, R(65, 1000), 360],
    ["amortize", 250000 * W, 0, 360],
    ["amortize", 1000 * W, R(5, 100), 12],
    ["amortize", 1, 0, 1],
    ["amortize", 999999999999999999999, R(125, 1000), 7],
    ["amortize", 500000 * W, R(3, 100), 240],
    ["amortize", 123456789012345678901234, R(475, 10000), 48],
    ["amortize", 10000 * W, R(1, 100), 2],
    ["amortize", 10 * W + 5, 0, 10],
    ["amortize", 7 * W + 4, 0, 7],
    ["amortize", 7 * W + 1, 0, 7],
    ["amortize", 100 * W, R(12, 100), 1],
    ["amortize", 1234567 * W, R(725, 10000), 120],
    ["amortize", 88888 * W + 12345, R(399, 10000), 60],
    ["amortize", 42 * W + 7, R(9, 100), 24],
    ["amortize", 3 * W + 3, R(15, 100), 5],
    ["amortize", 99999 * W, R(2, 100), 36],
    ["amortize", 654321 * W + 99, R(55, 1000), 300],
    ["amortize", 17 * W + 13, R(111, 1000), 9],
    ["amortize", 0, 0, 12], ["amortize", -5 * W, R(5, 100), 12],
    ["amortize", W, -1, 12], ["amortize", W, 0, 0],
    ["amortize", W, R(5, 100), 0], ["amortize", W, 0, -3],
]

CMP = {ast.Lt: ast.LtE, ast.LtE: ast.Lt, ast.Gt: ast.GtE, ast.GtE: ast.Gt,
       ast.Eq: ast.NotEq, ast.NotEq: ast.Eq, ast.In: ast.NotIn, ast.NotIn: ast.In}
BIN = {ast.Add: ast.Sub, ast.Sub: ast.Add, ast.Mult: ast.FloorDiv,
       ast.FloorDiv: ast.Mult, ast.Pow: ast.Mult}

def canon(o): return json.dumps(o, sort_keys=True, separators=(",", ":"))
def sha(b): return hashlib.sha256(b).hexdigest()

def load(tree):
    ns = {}
    exec(compile(tree, "amort", "exec"), ns)
    return ns

def run(ns):
    out = []
    for fn, *args in VECTORS:
        try:
            out.append(ns[fn](*args))
        except Exception as e:
            out.append("ERR:" + type(e).__name__)
    return out

def root(results):
    h = "RUAX-WAD18-AMORT-v1"
    for v, r in zip(VECTORS, results):
        h = sha((h + canon([v, r])).encode())
    return h

def exact_pay(P, rate, n):
    if rate == 0:
        return Fraction(P, n)
    r = Fraction(rate, 12 * W)
    return P * r / (1 - (1 + r) ** (-n))

def invariants(res):
    bad = []
    for v, r in zip(VECTORS, res):
        if v[0] == "parse":
            whole, _, frac = v[1].partition(".")
            valid = whole.isdigit() and (frac == "" or frac.isdigit())
            if valid != (not isinstance(r, str)):
                bad.append(f"{v}: validity mismatch")
            elif valid and r != int(whole) * W + int((frac + "0" * 18)[:18]):
                bad.append(f"{v}: wrong value")
            continue
        _, P, rate, n = v
        valid = P > 0 and n > 0 and rate >= 0
        if valid == isinstance(r, str):
            bad.append(f"{v}: validity mismatch")
            continue
        if not valid:
            continue
        if len(r) != n: bad.append(f"{v}: row count")
        if sum(x[3] for x in r) != P: bad.append(f"{v}: principal not conserved")
        if r[-1][4] != 0: bad.append(f"{v}: final balance not zero")
        if any(x[4] < 0 for x in r): bad.append(f"{v}: negative balance")
        e = exact_pay(P, rate, n)
        if abs(Fraction(r[0][1]) - e) * 10**9 > e:
            bad.append(f"{v}: payment outside oracle tolerance")
    return bad

def sites(tree):
    out = []
    for i, n in enumerate(ast.walk(tree)):
        if isinstance(n, ast.Compare) and type(n.ops[0]) in CMP:
            out.append((i, "swap"))
        elif isinstance(n, ast.BinOp) and type(n.op) in BIN:
            out.append((i, "swap"))
        elif isinstance(n, ast.BoolOp):
            out.append((i, "swap"))
        elif isinstance(n, ast.Constant) and type(n.value) is int:
            out += [(i, "+1"), (i, "-1")]
    return out

def apply(tree, i, how):
    t = copy.deepcopy(tree)
    n = list(ast.walk(t))[i]
    if isinstance(n, ast.Compare): n.ops[0] = CMP[type(n.ops[0])]()
    elif isinstance(n, ast.BinOp): n.op = BIN[type(n.op)]()
    elif isinstance(n, ast.BoolOp):
        n.op = (ast.And if isinstance(n.op, ast.Or) else ast.Or)()
    else: n.value += 1 if how == "+1" else -1
    return ast.fix_missing_locations(t)

def label(tree, i, how):
    n = list(ast.walk(tree))[i]
    if isinstance(n, ast.Compare):
        d = f"{type(n.ops[0]).__name__}->{CMP[type(n.ops[0])].__name__}"
    elif isinstance(n, ast.BinOp):
        d = f"{type(n.op).__name__}->{BIN[type(n.op)].__name__}"
    elif isinstance(n, ast.BoolOp): d = "BoolOp-swap"
    else: d = f"const{n.value}{how}"
    return f"L{n.lineno}C{n.col_offset}:{d}"

def mutation_run(tree, base, allow):
    sl = sites(tree)
    killed, declared, surv = 0, [], []
    for i, how in sl:
        lab = label(tree, i, how)
        try:
            dead = root(run(load(apply(tree, i, how)))) != base
        except Exception:
            dead = True
        if dead: killed += 1
        elif lab in allow: declared.append(lab)
        else: surv.append(lab)
    return len(sl), killed, declared, surv

def file_hashes():
    names = ["amort.py", "capsule.py", "EQUIVALENT.json"]
    return {n: sha(open(os.path.join(HERE, n), "rb").read()) for n in names}

def main():
    args = sys.argv[1:]
    tree = ast.parse(open(SRC).read())
    res = run(load(tree)); r0 = root(res)
    ok = True
    print("RUAX WAD18 Loan Amortization Capsule")
    print(f"python {platform.python_version()} | {platform.system()} {platform.machine()}")
    print(f"vectors: {len(VECTORS)}  root: {r0}")
    if root(run(load(tree))) != r0:
        print("FAIL: run-to-run nondeterminism"); ok = False
    bad = invariants(res)
    for b in bad: print("INVARIANT FAIL:", b)
    ok &= not bad
    print("invariants + exact-rational oracle:", "PASS" if not bad else "FAIL")

    gp = os.path.join(HERE, "GOLDEN.json")
    mp = os.path.join(HERE, "MANIFEST.sha256")
    ep = os.path.join(HERE, "EQUIVALENT.json")
    if "--init" in args:
        if bad: print("refusing to init with failures"); sys.exit(1)
        if not os.path.exists(ep): open(ep, "w").write("{}\n")
        json.dump({"root": r0, "vectors": len(VECTORS)}, open(gp, "w"), indent=2)
        with open(mp, "w") as f:
            for n, h in file_hashes().items(): f.write(f"{h}  {n}\n")
        print("initialized GOLDEN.json and MANIFEST.sha256"); return
    if not (os.path.exists(gp) and os.path.exists(mp)):
        print("run with --init first"); sys.exit(1)
    gold = json.load(open(gp))["root"]
    print("golden root match:", "PASS" if gold == r0 else "FAIL"); ok &= gold == r0
    want = dict(l.split("  ")[::-1] for l in open(mp).read().split("\n") if l)
    have = file_hashes()
    mm = [n for n in have if want.get(n) != have[n]]
    print("file manifest:", "PASS" if not mm else f"FAIL {mm}"); ok &= not mm

    if "--mutate" in args:
        allow = json.load(open(ep))
        total, killed, declared, surv = mutation_run(tree, r0, allow)
        stale = [k for k in allow if k not in declared]
        eff = total - len(declared)
        rate = 100.0 * killed / eff if eff else 100.0
        print(f"mutants: {total}  killed: {killed}  declared-equivalent: {len(declared)}  survivors: {len(surv)}")
        print(f"kill rate (non-equivalent): {killed}/{eff} = {rate:.2f}%")
        for s in surv: print("  SURVIVOR:", s)
        for s in stale: print("  STALE equivalent entry:", s)
        json.dump({"root": r0, "mutants": total, "killed": killed,
                   "declared_equivalent": declared, "survivors": surv},
                  open(os.path.join(HERE, "RESULTS.json"), "w"), indent=2)
        ok &= not surv and not stale
    print("RESULT:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)

main()
