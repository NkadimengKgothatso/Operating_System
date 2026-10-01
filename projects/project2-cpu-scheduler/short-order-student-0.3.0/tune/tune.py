"""python3 tune/tune.py MODULE VARIANTS.json [seedA..seedB] [profiles]
VARIANTS: {"label": {param overrides}, ...}"""
import os, sys, json, time, importlib.util
from concurrent.futures import ProcessPoolExecutor
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "student-sdk"))
from kitchen import runner
PROFILES = ["default", "bake-off", "banquet-night", "blind", "brigade", "function", "one-cook", "rush", "service-line"]
_mod = {}
def load(path):
    if path not in _mod:
        spec = importlib.util.spec_from_file_location("cand_" + str(abs(hash(path))), path)
        m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); _mod[path] = m
    return _mod[path]
def job(a):
    path, label, over, prof, seed = a
    m = load(path)
    base = dict(m.BASE) if hasattr(m, "BASE") else None
    if base is None:
        m.BASE = dict(m.P); base = dict(m.P)
    m.P.clear(); m.P.update(base); m.P.update(over)
    inst = m.MyScheduler()
    cfg = os.path.join(ROOT, "configs", prof + ".toml")
    r = runner.play(inst, seed, config_path=cfg, record_debug=False, enforce_deadline=False)
    return label, prof, seed, r.score, r.result["score"]
if __name__ == "__main__":
    path = os.path.abspath(sys.argv[1]); variants = json.loads(open(sys.argv[2]).read()) if sys.argv[2].endswith(".json") else json.loads(sys.argv[2])
    a, b = (sys.argv[3] if len(sys.argv) > 3 else "3000..3030").split("..")
    profs = sys.argv[4].split(",") if len(sys.argv) > 4 else PROFILES
    jobs = [(path, l, o, p, s) for l, o in variants.items() for p in profs for s in range(int(a), int(b))]
    t = time.time()
    with ProcessPoolExecutor(os.cpu_count()) as ex:
        res = list(ex.map(job, jobs, chunksize=2))
    agg = {}; comps = {}
    for l, p, s, sc, parts in res:
        agg.setdefault(l, {}).setdefault(p, []).append(sc)
        c = comps.setdefault(l, {})
        for kk, vv in parts.items():
            if kk != "total" and isinstance(vv, (int, float)): c[kk] = c.get(kk, 0) + vv / len(profs) / (int(b) - int(a))
    print("%-26s %6s %6s " % ("variant", "MEAN", "noFn") + " ".join("%7s" % p[:7] for p in profs))
    rows = []
    for l in variants:
        ms = [sum(agg[l][p]) / len(agg[l][p]) for p in profs]
        nf = [m for p, m in zip(profs, ms) if p != "function"]
        rows.append((sum(ms) / len(ms), l, ms, sum(nf) / max(1, len(nf))))
    for mean, l, ms, nf in rows:
        print("%-26s %6.2f %6.2f " % (l[:26], mean, nf) + " ".join("%7.2f" % m for m in ms))
    print("components:", {l: {k: round(v, 3) for k, v in c.items()} for l, c in comps.items()} if len(variants) <= 3 else "")
    print("(%d runs, %.1fs)" % (len(jobs), time.time() - t))
