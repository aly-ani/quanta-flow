# tests/test_witness.py
from core.limiter import FairLimiter

def worst_window_error(q=10, reps=50):
    # adversarial pattern: push q-1 remainders just below carry, then trigger
    plan = ([q-1] * (q-1) + [1]) * reps  # scaled by q
    lim = FairLimiter(q)
    out = []
    E = 0
    for xq in plan:
        out.append(lim.step(xq))
    # brute force worst absolute prefix/window error
    errs = []
    prefix_x = prefix_y = 0
    sx = [0]; sy = [0]
    for xq in plan: sx.append(sx[-1] + xq/q)
    for y in out:   sy.append(sy[-1] + y)
    for i in range(len(plan)+1):
        for j in range(i):
            errs.append(abs((sx[i]-sx[j]) - (sy[i]-sy[j])))
    return max(errs)

def test_bound_tight():
    q = 10
    assert abs(worst_window_error(q) - (1 - 1/q)) < 1e-6
