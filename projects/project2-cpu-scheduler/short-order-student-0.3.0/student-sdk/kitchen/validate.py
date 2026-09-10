"""Local validation of a submission.

The point of this module is that an invalid submission fails on the student's
own machine, with an explanation, instead of on the marking server with a
stack trace and a zero. It checks the things the server will check, in the
order they will be checked.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .errors import SubmissionError
from .helpers import load_scheduler
from .runner import play

#: Seeds every student can test against. Marking uses a separate hidden set.
PUBLIC_SEEDS = (1001, 1002, 1003, 1004, 1005)


@dataclass
class ValidationReport:
    """What the validator found. ``ok`` is what decides acceptance."""

    ok: bool = True
    scheduler: Optional[str] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)

    def fail(self, message: str) -> "ValidationReport":
        self.ok = False
        self.errors.append(message)
        return self

    def warn(self, message: str) -> "ValidationReport":
        self.warnings.append(message)
        return self

    def render(self) -> str:
        lines = [f"submission: {self.scheduler or 'unknown'}"]
        for key, value in self.stats.items():
            lines.append(f"  {key:<28} {value}")
        for warning in self.warnings:
            lines.append(f"  warning: {warning}")
        for error in self.errors:
            lines.append(f"  ERROR:   {error}")
        lines.append("  PASSED" if self.ok else "  FAILED")
        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "scheduler": self.scheduler,
            "errors": self.errors,
            "warnings": self.warnings,
            "stats": self.stats,
        }


def validate(
    spec: str,
    *,
    seeds: Any = PUBLIC_SEEDS,
    config_path: Optional[str] = None,
    deadline_ms: Optional[float] = None,
    max_ticks: Optional[int] = None,
) -> ValidationReport:
    """Runs the acceptance checks against a submission specification."""
    report = ValidationReport()

    # 1. It has to load and implement the interface at all.
    try:
        scheduler = load_scheduler(spec)
    except SubmissionError as exc:
        report.scheduler = spec
        return report.fail(str(exc))
    report.scheduler = scheduler.describe()

    # 2. It has to survive a full run on every public seed under the marker's
    #    failure policy, without raising, timing out or being forfeited.
    total_errors = 0
    total_timeouts = 0
    total_rejected = 0
    total_decisions = 0
    total_ms = 0.0
    slowest_ms = 0.0
    served = 0
    orders = 0
    scores: List[float] = []
    first_failures: List[str] = []
    seeds = tuple(seeds)
    for seed in seeds:
        outcome = play(
            spec,
            seed,
            config_path=config_path,
            max_ticks=max_ticks,
            per_decision_timeout_ms=deadline_ms,
            record_debug=False,
        )
        r = outcome.result
        total_errors += r["policy_errors"]
        total_timeouts += r["policy_timeouts"]
        total_rejected += r["invalid_assignments"]
        total_decisions += r["decisions"]
        total_ms += r["decision_time_ms"]["total_ms"]
        slowest_ms = max(slowest_ms, r["decision_time_ms"]["max_ms"])
        served += r["metrics"]["served"]
        orders += r["metrics"]["orders"]
        scores.append(r["score"]["total"])
        if r["failures"] and len(first_failures) < 3:
            first_failures.extend(f"seed {seed}: {f}" for f in r["failures"][:2])
        if r["forfeited"]:
            report.fail(f"seed {seed}: the run was forfeited ({r['terminal_reason']})")

    mean_ms = total_ms / total_decisions if total_decisions else 0.0
    deadline = deadline_ms if deadline_ms else 50.0
    report.stats = {
        "runs played": len(seeds),
        "decisions": total_decisions,
        "mean decision (ms)": f"{mean_ms:.3f}",
        "slowest decision (ms)": f"{slowest_ms:.3f}",
        "deadline (ms)": f"{deadline:.0f}",
        "exceptions": total_errors,
        "over deadline": total_timeouts,
        "rejected assignments": total_rejected,
        "served": f"{served} of {orders}",
        "mean score": f"{sum(scores) / len(scores):.1f}" if scores else "-",
    }

    if total_errors:
        report.fail(
            f"schedule() raised {total_errors} time(s). On the server those decisions are "
            f"ignored and count against you; twenty in a row forfeits the run."
        )
    if total_timeouts:
        report.fail(
            f"{total_timeouts} of {total_decisions} decisions exceeded the {deadline:.0f} ms deadline "
            f"(slowest {slowest_ms:.1f} ms). On the server those decisions are discarded."
        )
    elif slowest_ms > deadline * 0.5:
        report.warn(
            f"the slowest decision took {slowest_ms:.1f} ms, over half the {deadline:.0f} ms deadline; "
            f"there is little headroom on a loaded marking machine"
        )
    if total_rejected:
        report.warn(
            f"{total_rejected} assignment(s) were rejected by the engine (an order in the oven, an id "
            f"that does not exist, a cook named twice). They are ignored, not penalised, but they "
            f"mean your scheduler asked for something impossible."
        )
    if served == 0 and orders > 0:
        report.warn("your scheduler never served anybody - does it ever assign a cook?")
    for message in first_failures:
        report.warn(message)
    return report
