# sim/run_sim.py

import argparse
import math
import random

from core import FairLimiter


def gen_plan(n: int, q: int, scenario: str, amp: float, seed: int) -> list[int]:
    """
    Generate a sequence of planned increments x_t scaled by q.

    Returns a list of integers in [0, q].
    """
    random.seed(seed)

    if scenario == "diurnal":
        base = int(0.4 * q)
        a = int(amp * q)
        xs = []
        for i in range(n):
            val = base + int(a * math.sin(2 * math.pi * i / 100.0))
            xs.append(max(0, min(q, val)))
        return xs

    if scenario == "spiky":
        # bursts every 40 ticks: 5 high, 35 zero
        return [q if (i % 40 < 5) else 0 for i in range(n)]

    if scenario == "saw":
        # alternating low/high
        return [1 if (i % 2 == 1) else 0 for i in range(n)]

    # default: random
    return [random.randint(0, q) for _ in range(n)]


def max_window_error(xs_q: list[int], ys: list[int], q: int) -> float:
    """
    Brute-force max sliding-window error:

        max_{s <= t} | sum_{i=s..t} (x_i/q - y_i) |
    """
    n = len(xs_q)
    prefix = [0.0]
    for i in range(n):
        prefix.append(prefix[-1] + xs_q[i] / q - ys[i])

    worst = 0.0
    for a in range(n):
        for b in range(a + 1, n + 1):
            err = abs(prefix[b] - prefix[a])
            if err > worst:
                worst = err
    return worst


def main() -> None:
    ap = argparse.ArgumentParser(
        description="QuantaFlow simulator (sliding-window fairness limiter)."
    )
    ap.add_argument("--q", type=int, default=10, help="granularity (e.g. 10 -> tenths)")
    ap.add_argument("--ticks", type=int, default=200, help="number of time steps")
    ap.add_argument(
        "--scenario",
        choices=["diurnal", "spiky", "saw", "rand"],
        default="diurnal",
        help="plan generation scenario",
    )
    ap.add_argument(
        "--amp",
        type=float,
        default=0.3,
        help="amplitude for diurnal scenario (0.0–1.0-ish)",
    )
    ap.add_argument("--seed", type=int, default=7, help="random seed")

    args = ap.parse_args()

    xs_q = gen_plan(args.ticks, args.q, args.scenario, args.amp, args.seed)
    limiter = FairLimiter(args.q)
    ys = [limiter.step(x) for x in xs_q]

    werr = max_window_error(xs_q, ys, args.q)

    print(f"QuantaFlow simulation")
    print(f"  q           = {args.q}")
    print(f"  ticks       = {args.ticks}")
    print(f"  scenario    = {args.scenario}")
    print(f"  max window error = {werr:.6f}")
    print(f"  theory bound     = {1 - 1 / args.q:.6f}")


if __name__ == "__main__":
    main()
