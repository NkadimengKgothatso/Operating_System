"""Your scheduler.

Strategy: shortest-remaining-work first for orders that are in no danger,
switching to deadline urgency only for the ones actually at risk of being
lost - station-aware, with threshold-gated preemption. See the numbered
sections in `schedule` below for the reasoning behind each part.

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
    version = "2"

    # How many ticks of slack still counts as "in no immediate danger".
    # Scaled off switch_cost since that is the only natural timescale the
    # kitchen gives us; a run of `evaluate` after changing this is the way
    # to check whether a bigger or smaller margin helps a given profile.
    CRITICAL_MARGIN_SWITCHES = 4

    def reset(self, seed):
        """Nothing to carry between runs - every decision below is made
        fresh from `obs`, so there is no state to set up here."""

    def schedule(self, obs):
        est = obs.estimate_remaining
        switch_cost = obs.kitchen.switch_cost
        margin = self.CRITICAL_MARGIN_SWITCHES * switch_cost

        # *******************************************************************
        # 1. ONE URGENCY SCALE, THREE REGIMES
        # *******************************************************************
        # slack = how much spare time is left: deadline minus the work still
        # needed. slack < 0 means the order is already lost - no cook can
        # save it now.
        #
        # A first version of this scheduler ranked *everything* by least
        # slack (a textbook EDF). It maximised completion, but tanked
        # response, turnaround and fairness - worth 40 of the 100 points
        # between them - because a patient customer can get pushed to the
        # back of the rail indefinitely while cooks sit idle, just because
        # something else always looks marginally more urgent on paper.
        #
        # The fix: only let deadline pressure override everything once an
        # order is actually in danger (slack <= margin). Anything with room
        # to spare is instead ranked by shortest remaining work - SRTF, which
        # is the classic minimiser of *average* waiting time when there is no
        # deadline pressure forcing a different order.
        #
        # `urgency()` folds all three regimes onto one number, smaller =
        # served sooner, so it can be used both to sort the rail and, by
        # simple subtraction, to decide whether a preemption is worth its own
        # cost in section 3:
        #
        #   doomed   (slack < 0)        -> +inf, never worth a dedicated cook
        #   critical (0 <= slack <= margin) -> slack itself: least slack first
        #   safe     (slack > margin)   -> margin + est(order) / (1 + waited):
        #                                  ranked by shortest job, but *aged*
        #                                  by how long it has already sat on
        #                                  the rail
        #
        # Pure SRTF for the "safe" tier (margin + est(order), no aging term)
        # was tried first: it lifted response and slowdown a lot, but hurt
        # fairness - a long job with room to spare can be jumped by an
        # unbroken stream of short arrivals and wait a very long time before
        # its slack finally shrinks enough to be treated as critical. Nothing
        # about any single decision looks wrong; the unfairness is the sum of
        # many of them.
        #
        # Dividing est(order) by `1 + order.waited` fixes that: a job that
        # just arrived (waited = 0) is ranked exactly as before, purely by
        # its own length. The longer it sits, the more that term shrinks
        # toward zero regardless of how long the job itself is, so its
        # overall value drifts down toward `margin` - as urgent as a
        # borderline-critical order - well before its deadline forces the
        # issue. A large job does not get a permanent free pass just because
        # it is large.
        def slack(order):
            return order.time_left - est(order)

        def urgency(order):
            sl = slack(order)
            if sl < 0:
                return float("inf")
            if sl <= margin:
                return sl
            return margin + est(order) / (1 + order.waited)

        # A light tie-break: an order whose *next* step lands on a station
        # that is full right now is likely to get bumped straight back onto
        # the rail the moment it finishes this step - costing a switch to
        # resume it later. Prefer starting something that will not
        # immediately walk into a wall.
        def next_step_blocked(order):
            nxt = order.step + 1
            if nxt < len(order.steps):
                station_name = order.steps[nxt].station
                if station_name is not None:
                    station = obs.station(station_name)
                    return station is not None and station.free <= 0
            return False

        def rank_key(order):
            return (
                urgency(order),
                -order.priority,       # tie-break only, never an override
                next_step_blocked(order),
                est(order),
            )

        rail = sorted(obs.ready, key=rank_key)

        decision = Decision()

        # *******************************************************************
        # 2. HAND IDLE COOKS THE HIGHEST-RANKED ORDER THEIR STATION HAS ROOM FOR
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
        # overhead, for nothing. So a preemption only pays for itself if the
        # waiting order's urgency beats the running order's by more than that
        # round-trip cost. Because `urgency` already blends slack and
        # shortest-job-first onto one scale, a single comparison covers every
        # case that matters:
        #
        #   * a critical order can bump a safe one that has room to spare
        #     (a large urgency gap, since "safe" values start above `margin`
        #     and "critical" values are below it);
        #   * among two safe orders, this reduces to the classic SRTF-with-
        #     overhead rule: only take over if the new job is shorter than
        #     the one running by more than the round-trip switch cost;
        #   * a doomed running order (urgency = +inf) is always worth
        #     freeing - finishing it buys nothing, so any savable candidate
        #     is an improvement, no threshold needed.
        for core in obs.working_cores:
            if not rest:
                break

            current = obs.order_on(core)
            if current is None:
                continue

            current_urgency = urgency(current)

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

                gap = current_urgency - urgency(candidate)
                if gap > 2 * switch_cost:
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
        # quiet kitchen with one at-risk order sitting on the rail would
        # never get revisited until it was too late to matter. Wake up right
        # when the most urgent still-savable order would run out of slack
        # entirely, so there is still a chance to act on it.
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
            text="SRTF with deadline override, station-aware",
            queue=[o.id for o in rail],
            tags=tags,
        )