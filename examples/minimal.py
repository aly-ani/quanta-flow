# examples/minimal.py
from core.limiter import FairLimiter

q = 10
lim = FairLimiter(q)

plan = [0, 3, 0, 1, 2, 0, 0, 1, 0, 2]  # plan in q-units (ints in [0..q])
out = []
for xq in plan:
    out.append(lim.step(xq))

def max_window_err(xs, ys):
    pref = [0.0]
    for i in range(len(xs)):
        pref.append(pref[-1] + (xs[i] / q - ys[i]))
    return max(abs(pref[j] - pref[i]) for i in range(len(pref)) for j in range(i+1, len(pref)))

xs = [x / q for x in plan]
print("plan:", [x / q for x in plan])
print("emit:", out)
print("max window error:", max_window_err(xs, out))
print("theory bound:", 1 - 1/q)
