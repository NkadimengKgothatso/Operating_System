"""Tuning candidate: parameters can be overridden with SCHED_P='{"k": v}'."""

import json
import os

from kitchen import Decision, Scheduler

P = dict(
    burst_w=0.0,        # 0 = rank on total remaining work, 1 = on next burst only
    wait_w=0.0,         # weight of remaining oven time in the length key
    sd_w=0.0,           # 1 = weight length by max(span, bound) (slowdown-optimal)
    age=0.03,           # ticks of length forgiven per tick waited
    prio=0.0,           # ticks of length forgiven per priority level above 1
    urg_margin=0,       # slack (ticks) below which an order is "urgent"
    urg_bonus=0.0,      # ticks of length forgiven when urgent
    bump_pen=0.0,       # ticks added when next step's station is full now
    started_bonus=0.0,  # ticks forgiven for an order already started
    doomed="last",      # "last" | "never"
    pre_margin=16.0,    # preempt if key gap > pre_margin * switch_cost
    pre_doomed=1,       # free a cook holding a doomed order
    fn_touch=1,         # function-style: touch every order once early
    fn_quantum=1,       # ticks of work in the touch
    fn_mode="sjf",      # order after touching
    wake=1,
)
if os.environ.get("SCHED_P"):
    P.update(json.loads(os.environ["SCHED_P"]))


class MyScheduler(Scheduler):
    name = "cand"
    version = "1"

    def reset(self, seed):
        self.touched = set()

    def schedule(self, obs):
        if not hasattr(self, "touched"):
            self.touched = set()
        k = obs.kitchen
        sc = k.switch_cost
        bound = k.slowdown_bound
        known = k.known_durations
        est_cache = {}

        def est(o):
            v = est_cache.get(o.id)
            if v is None:
                v = float(o.work_remaining) if o.work_remaining is not None else obs.estimate_remaining(o)
                est_cache[o.id] = v
            return v

        def waits_left(o):
            t = 0.0
            for s in o.steps[o.step:]:
                if s.kind == "wait":
                    t += s.remaining if s.remaining is not None else 0.0
            return t

        def burst(o):
            w = o.work_until_wait
            return float(w) if w is not None else est(o)

        def span_total(o):
            t = 0.0
            for s in o.steps:
                if s.duration is not None:
                    t += s.duration
            return t if t > 0 else est(o)

        def slack(o):
            return o.time_left - est(o) - waits_left(o) - sc

        def next_blocked(o):
            n = o.step + 1
            if n < len(o.steps):
                st = o.steps[n].station
                if st is not None and st != o.station:
                    s = obs.station(st)
                    return s is not None and s.free <= 0
            return False

        def key(o):
            sl = slack(o)
            if sl < 0:
                return 1e9 + est(o)
            length = (1 - P["burst_w"]) * est(o) + P["burst_w"] * burst(o) + P["wait_w"] * waits_left(o)
            if P["sd_w"]:
                length *= (max(span_total(o), bound) / bound) ** P["sd_w"]
            v = length - P["age"] * o.waited - P["prio"] * (o.priority - 1)
            if sl <= P["urg_margin"]:
                v -= P["urg_bonus"]
            if P["bump_pen"] and next_blocked(o):
                v += P["bump_pen"]
            if P["started_bonus"] and o.started is not None:
                v -= P["started_bonus"]
            return v

        d = Decision()

        # ---- private function: everybody seated at once ----------------
        if P["fn_touch"] and "function" in k.name:
            return self.function(obs, d, est)

        ready = obs.ready
        if P["doomed"] == "never":
            ready = [o for o in ready if slack(o) >= 0]
        rail = sorted(ready, key=key)
        free = obs.free_stations()
        idle = list(obs.idle_cores)
        rest = []
        for o in rail:
            st = o.station
            if idle and (st is None or free.get(st, 0) > 0):
                d.assign(idle.pop(0), o)
                if st is not None:
                    free[st] -= 1
            else:
                rest.append(o)

        if rest:
            thr = P["pre_margin"] * sc
            for core in obs.working_cores:
                if not rest:
                    break
                cur = obs.order_on(core)
                if cur is None:
                    continue
                stp = cur.current_step
                if stp is not None and stp.remaining is not None and stp.remaining <= sc:
                    continue
                ck = key(cur)
                doomed_cur = slack(cur) < -0 and cur.time_left < est(cur)
                fh = cur.station
                if fh is not None:
                    free[fh] = free.get(fh, 0) + 1
                chosen = None
                for c in rest:
                    st = c.station
                    if st is not None and free.get(st, 0) <= 0:
                        continue
                    if (P["pre_doomed"] and doomed_cur and key(c) < 1e9) or ck - key(c) > thr:
                        chosen = c
                    break
                if chosen is not None:
                    d.assign(core, chosen)
                    rest.remove(chosen)
                    if chosen.station is not None:
                        free[chosen.station] -= 1
                elif fh is not None:
                    free[fh] -= 1

        if P["wake"]:
            sav = [slack(o) for o in obs.ready if slack(o) >= 0]
            if sav:
                h = int(min(sav))
                if h > 0:
                    d.wake_in(h)
        return d

    def function(self, obs, d, est):
        sc = obs.kitchen.switch_cost
        q = P["fn_quantum"]
        free = obs.free_stations()
        untouched = [o for o in obs.ready if o.started is None]
        idle = list(obs.idle_cores)
        # cooks: either idle, or working on an order
        assign = {}
        if untouched:
            untouched.sort(key=est)
            # preempt any cook whose order has had its touch (started and worked >= q)
            cands = []
            for c in obs.cores:
                cur = obs.order_on(c)
                if cur is None:
                    cands.append(c)
                elif cur.started is not None and cur.work_done >= q and len(untouched) > 0:
                    cands.append(c)
            for c in cands:
                if not untouched:
                    break
                o = untouched.pop(0)
                d.assign(c, o)
            # wake when the touch should be done
            d.wake_in(sc + q)
            return d
        # all touched: shortest remaining first, non-preemptive
        rail = sorted(obs.ready, key=est)
        for c in idle:
            if not rail:
                break
            d.assign(c, rail.pop(0))
        return d
