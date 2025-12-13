# tests/test_properties.py

import random

from core import FairLimiter


def _max_window_error(xs_q, ys, q):
    """
    max over all windows [s..t] of | sum_{i=s..t}(x_i/q - y_i) |
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


def test_tight_witness_q4():
    """
    Witness sequence for q=4: x = [0, 1/4, 1/4, 1/4] hits the bound 1 - 1/q.
    """
    q = 4
    # x values scaled by q: 0, 1/4, 1/4, 1/4 -> [0, 1, 1, 1]
    xs_q = [0, 1, 1, 1]
    limiter = FairLimiter(q)
    ys = [limiter.step(x) for x in xs_q]

    werr = _max_window_error(xs_q, ys, q)
    target = 1 - 1 / q
    assert abs(werr - target) < 1e-9


def test_random_sequences_bound():
    """
    For random sequences, error should never exceed 1 - 1/q (up to tiny float slack).
    """
    q = 10
    runs = 25
    length = 200

    for seed in range(runs):
        random.seed(seed)
        xs_q = [random.randint(0, q) for _ in range(length)]
        limiter = FairLimiter(q)
        ys = [limiter.step(x) for x in xs_q]

        werr = _max_window_error(xs_q, ys, q)
        assert werr <= (1 - 1 / q) + 1e-9


def test_multi_token_scaling_simple():
    """
    Very simple sanity check for multi-token extension: we can loop the carry rule
    up to M times per tick; bound should be <= M * (1 - 1/q).
    """
    q = 10
    M = 3

    class MultiTokenLimiter:
        def __init__(self, q, M):
            self.q = q
            self.M = M
            self.E = 0

        def step(self, x_q):
            self.E += x_q
            y = 0
            for _ in range(self.M):
                if self.E >= self.q:
                    self.E -= self.q
                    y += 1
            return y

    xs_q = [0, 5, 10, 15, 0, 10]  # scaled by q
    limiter = MultiTokenLimiter(q, M)
    ys = [limiter.step(x) for x in xs_q]

    werr = _max_window_error(xs_q, ys, q)
    assert werr <= M * (1 - 1 / q) + 1e-9
