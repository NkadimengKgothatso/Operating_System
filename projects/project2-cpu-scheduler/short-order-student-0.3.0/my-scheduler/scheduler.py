"""Your scheduler.

Strategy: least-slack-time, priority-weighted, station-aware, with
threshold-gated preemption. See the numbered sections in `schedule` below
for the reasoning behind each part.

    START.cmd play my-scheduler                (Windows)
    ./start.sh play my-scheduler               (macOS and Linux)
    ./start.sh compare my-scheduler            (against every reference)
    ./start.sh evaluate my-scheduler --seeds 1000..1020

The picture: cooks are CPU cores, orders are processes, a recipe's `work`
steps are CPU bursts and its `wait` steps (the oven) are I/O bursts. Every
time a cook takes on an order it pays a context switch of
`obs.kitchen.switch_cost` ticks, and every order has a `deadline` - miss it
and the customer walks out, whatever progress was made.
"""

from kitchen import Decision, Scheduler


class MyScheduler(Scheduler):
    name = "least_slack_chef"
    version = "1"

    def reset(self, seed):
        """Nothing to carry between runs - every decision below is made
        fresh from `obs`, so there is no state to set up here."""

    def schedule(self, obs):
        est = obs.estimate_remaining
        switch_cost = obs.kitchen.switch_cost

        # *******************************************************************
        # 1. HOW URGENT IS EACH ORDER? ("slack")
        # *******************************************************************
        # Slack is how much spare time an order has: its deadline, minus the
        # work it still needs. Slack < 0 means it is already lost - no cook,
        # however good, can finish it before the customer walks. That is a
        # very different problem from "which job is biggest", which is all
        # idiot_sandwich ever asked.
        def slack(order):
            return order.time_left - est(order)

        # A light tie-break: an order whose *next* step lands on a station
        # that is full right now is likely to get bumped straight back onto
        # the rail the moment it finishes this step - costing a switch to
        # resume it later. Prefer starting something that will not immediately
        # walk into a wall.
        def next_step_blocked(order):
            nxt = order.step + 1
            if nxt < len(order.steps):
                station_name = order.steps[nxt].station
                if station_name is not None:
                    station = obs.station(station_name)
                    return station is not None and station.free <= 0
            return False

        # The rail, ranked:
        #   1. savable orders before doomed ones - a doomed order is not
        #      worth a dedicated cook while a savable one is waiting;
        #   2. within that, VIPs before hurried before regular customers;
        #   3. within that, least slack first - the customer closest to
        #      giving up goes next (this is what "least slack time"
        #      scheduling means);
        #   4. a light penalty for orders about to walk into a full station;
        #   5. shortest remaining work as the final tiebreak (SJF), so two
        #      equally urgent orders are broken by which one clears fastest.
        def rank_key(order):
            sl = slack(order)
            return (
                sl < 0,
                -order.priority,
                sl,
                next_step_blocked(order),
                est(order),
            )

        rail = sorted(obs.ready, key=rank_key)

        decision = Decision()

        # *******************************************************************
        # 2. HAND IDLE COOKS THE MOST URGENT ORDER THEIR STATION HAS ROOM FOR
        # *******************************************************************
        # obs.free_stations() is a snapshot from before this decision, so we
        # keep our own copy and spend it as we go - every assignment below
        # updates `free` so the next one sees an accurate count.
        free = obs.free_stations()
        idle = list(obs.idle_cores)
        rest = []  # orders we could not seat this round

        for order in rail:
            if not idle:
                rest.append(order)
                continue
            station = order.station
            if station is not None and free.get(station, 0) <= 0:
                # This order's station is full right now. Leave it for
                # later (or for the next scheduling point) rather than
                # stall a cook waiting for it - some other order on the
                # rail may be ready to go right now.
                rest.append(order)
                continue
            decision.assign(idle.pop(0), order)
            if station is not None:
                free[station] -= 1

        # *******************************************************************
        # 3. PREEMPTION: ONLY WORTH IT IF IT SURVIVES ITS OWN COST
        # *******************************************************************
        # Taking a cook off an order costs a switch now, and another switch
        # later to resume that order - `2 * switch_cost` ticks of pure
        # overhead, for nothing. So a preemption only pays for itself if:
        #
        #   * the waiting order is more urgent than the one running by more
        #     than that round-trip cost (otherwise we are burning ticks to
        #     reorder two things that were both going to finish in time), and
        #   * the order currently running can actually afford the delay
        #     without becoming doomed itself.
        #
        # The one exception: if the running order is *already* doomed (slack
        # < 0), finishing it buys nothing, so the cook should be freed for
        # whoever can still be saved - no threshold needed.
        for core in obs.working_cores:
            if not rest:
                break

            current = obs.order_on(core)
            if current is None:
                continue

            current_slack = slack(current)

            # A job about to hand the cook back on its own is not worth
            # interrupting - it will free up almost as fast as a switch
            # would cost anyway.
            step = current.current_step
            if (
                step is not None
                and step.kind == "work"
                and step.remaining is not None
                and step.remaining <= switch_cost
            ):
                continue

            # Preempting frees the cook's current station within this same
            # decision - reflect that in `free` for the search below. If we
            # end up not preempting, give the place back before moving on.
            freed_here = current.station
            if freed_here is not None:
                free[freed_here] = free.get(freed_here, 0) + 1

            chosen = None
            for candidate in rest:
                station = candidate.station
                if station is not None and free.get(station, 0) <= 0:
                    continue  # no room for it even after freeing `current`

                doomed_current = current_slack < 0
                gap = current_slack - slack(candidate)
                worth_it = doomed_current or (
                    gap > 2 * switch_cost and current_slack >= 2 * switch_cost
                )
                if worth_it:
                    chosen = candidate
                    break  # `rest` is already ranked - the first hit is best

            if chosen is not None:
                decision.assign(core, chosen)
                rest.remove(chosen)
                if chosen.station is not None:
                    free[chosen.station] -= 1
                # current's old station stays freed - the cook has left it.
            elif freed_here is not None:
                free[freed_here] -= 1  # no swap made; give the place back

        # *******************************************************************
        # 4. SET AN ALARM FOR THE NEXT MOMENT THAT MATTERS
        # *******************************************************************
        # We are only called when something happens. Without a timer, a
        # quiet kitchen with one urgent order sitting on the rail would never
        # get revisited until it was too late to matter. Wake up right when
        # the most urgent still-savable order would start running out of
        # slack, so there is still a chance to act on it.
        savable = [o for o in obs.ready if slack(o) >= 0]
        if savable:
            horizon = min(slack(o) for o in savable)
            if horizon > 0:
                decision.wake_in(max(1, horizon))

        # *******************************************************************
        # 5. SHOW YOUR WORKING (ignored by the marker, useful in the viewer)
        # *******************************************************************
        tags = {o.id: "can't make it" for o in rail if slack(o) < 0}
        return decision.annotate(
            text="least slack, priority-weighted, station-aware",
            queue=[o.id for o in rail],
            tags=tags,
        )