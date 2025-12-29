from core.limiter import FairLimiter
from itertools import accumulate

def max_window_error(x_q, y, q):
    n = len(x_q)
    X = [0.0] + list(accumulate([v / q for v in x_q]))
    Y = [0.0] + list(accumulate(y))
    ans = 0.0
    for i in range(n):
        for j in range(i+1, n+1):
            err = abs((X[j]-X[i]) - (Y[j]-Y[i]))
            if err > ans: ans = err
    return ans

def test_random_sequences_respect_bound():
    import random
    q = 10
    for _ in range(5):
        lim = FairLimiter(q)
        x_q = [random.randint(0, q) for _ in range(200)]
        y = [lim.step(x) for x in x_q]
        assert max_window_error(x_q, y, q) <= (1 - 1/q) + 1e-9
