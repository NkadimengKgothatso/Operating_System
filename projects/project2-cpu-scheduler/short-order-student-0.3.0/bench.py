"""Benchmark one or more schedulers across every profile. Usage:
    python3 bench.py [--seeds A..B] [--profiles a,b] sched1 [sched2 ...]
A scheduler is a path to a .py file or a reference name."""
import os, sys, time
from concurrent.futures import ProcessPoolExecutor
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "student-sdk"))
from kitchen import runner

PROFILES = ["default", "bake-off", "banquet-night", "blind", "brigade",
            "function", "one-cook", "rush", "service-line"]

def job(args):
    spec, profile, seed = args
    cfg = os.path.join(ROOT, "configs", profile + ".toml")
    try:
        r = runner.play(spec, seed, config_path=cfg, record_debug=False, enforce_deadline=False)
        return spec, profile, seed, r.score, r.result["score"]
    except Exception as e:
        return spec, profile, seed, 0.0, {"err": repr(e)}

def main():
    argv = sys.argv[1:]
    seeds = range(3000, 3020); profiles = PROFILES
    specs = []
    i = 0
    while i < len(argv):
        if argv[i] == "--seeds":
            a, b = argv[i+1].split(".."); seeds = range(int(a), int(b)); i += 2
        elif argv[i] == "--profiles":
            profiles = argv[i+1].split(","); i += 2
        else:
            specs.append(argv[i]); i += 1
    jobs = [(s, p, sd) for s in specs for p in profiles for sd in seeds]
    t = time.time()
    with ProcessPoolExecutor(max_workers=os.cpu_count()) as pool:
        res = list(pool.map(job, jobs, chunksize=4))
    agg = {}
    comp = {}
    for spec, p, sd, sc, parts in res:
        agg.setdefault(spec, {}).setdefault(p, []).append(sc)
        if "err" in parts: print("ERR", spec, p, sd, parts["err"])
    hdr = "%-28s %6s " % ("scheduler", "MEAN") + " ".join("%8s" % p[:8] for p in profiles)
    print(hdr)
    for spec in specs:
        means = [sum(agg[spec][p]) / len(agg[spec][p]) for p in profiles]
        print("%-28s %6.2f " % (os.path.basename(os.path.dirname(spec)) + "/" + os.path.basename(spec) if "/" in spec else spec, sum(means)/len(means))
              + " ".join("%8.2f" % m for m in means))
    print("(%d runs in %.1fs)" % (len(jobs), time.time() - t))

if __name__ == "__main__":
    main()
