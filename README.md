# QuantaFlow

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)]()

QuantaFlow is a tiny, deterministic rate limiter with a formal proof of how far actual behavior can drift from a fractional plan in any contiguous time window.

If you plan on a 1/q grid (for example, tenths per tick), QuantaFlow guarantees that for every sliding window W:

$$\left|\sum_{t \in W} (x_t - y_t)\right| \le 1 - \frac{1}{q}$$

This bound is tight (a witness sequence achieves it exactly).

---

## Why this matters

In multi-tenant APIs you plan fractional budgets (e.g., 0.3 requests / 100ms) but must emit integer tokens each tick. Naive float accumulation or rounding causes:

- **Unlucky tenants** to get false-throttled in bad windows
- **Bursty tenants** to exploit sawtooth artifacts
- **Fuzzier SLOs/billing** than your spec implies

QuantaFlow's carry rule keeps every sliding window close to the plan — online, with O(1) state per tenant.

---

## How it works

The core algorithm is a Bresenham-style integer accumulator applied to rate limiting. The technique dates to [Bresenham (1962)](https://en.wikipedia.org/wiki/Bresenham%27s_line_algorithm) for line rasterization, and the underlying math connects to [Sturmian sequences](https://en.wikipedia.org/wiki/Sturmian_word) and [balanced words](https://en.wikipedia.org/wiki/Beatty_sequence) in combinatorics on words.

**What QuantaFlow contributes:** a clean formalization of this bound for the sliding-window rate-limiting domain, a formal proof with tight witness, a reference implementation, and a direct comparison against token bucket / leaky bucket approaches.

### The carry-rule algorithm (fixed-point)

We work in integers by scaling everything by q.

```python
# core/limiter.py
class FairLimiter:
    def __init__(self, q: int):
        assert q >= 2
        self.q = q
        self.E = 0  # leftover in [0, q-1]

    def step(self, x_q: int) -> int:
        """
        x_q: planned increment scaled by q (integer in [0..q]).
        Returns y ∈ {0,1}.
        """
        self.E += x_q
        if self.E >= self.q:
            self.E -= self.q
            return 1
        return 0
```

**State per tenant:** one integer E ∈ [0, q−1].

**On each tick:**
1. Add the planned increment (scaled by q) to E.
2. If E ≥ q, emit one token and subtract q.
3. Otherwise, emit zero.

Scaling to up to M tokens per tick is supported by looping the carry; the bound becomes M × (1 − 1/q).

---

## Sliding-window bound

**Claim.** Let planned fractional increments lie on a 1/q grid: xₜ ∈ {0, 1/q, 2/q, …, 1} for each tick t. The limiter emits integer tokens yₜ ∈ {0, 1}. Then for every contiguous window W:

$$\left|\sum_{t \in W} (x_t - y_t)\right| \le 1 - \frac{1}{q}$$

**Proof sketch.** The error accumulator E takes values in {0, 1, 2, …, q−1}. The cumulative drift Rₜ = Σ(xₜ − yₜ) satisfies Rₜ = Eₜ/q, so |Rₜ| ≤ (q−1)/q.

**Tight witness.** Choose q−1 ticks of x_q = 1 (i.e., x = 1/q) then 0. Just before an emission, E = q−1, so drift = (q−1)/q.

Full proof in `math/math_proofs.md`.

**Note on prior art:** The (1 − 1/q) bound follows from elementary properties of modular arithmetic on a finite grid and is implicit in the classical theory of balanced words and Christoffel words (see Berthé & Tijdeman, 2002; Berstel et al., 2008). The contribution here is the explicit formalization for rate-limiting with a reference implementation, not the bound itself.

---

## Comparison

| Scheme | Worst-case drift bound (any window) | State per tenant | Burst handling | Determinism |
|---|---|---|---|---|
| Token Bucket | Not globally bounded (depends on burst & window alignment) | tokens, last-refill | Allows bursts up to bucket size; window error can spike | Yes |
| Leaky Bucket | Opaque; depends on leak vs. arrivals | queue/level | Smooths bursts; error hard to reason about | Yes |
| QuantaFlow | ≤ 1 − 1/q (tight) | E ∈ [0, q−1] | Emits at carry; windows stay close to plan | Yes |

---

## Install / Quickstart

```bash
git clone <repo-url> && cd quanta-flow
pip install -e .
pytest -q
python -m sim.run_sim --q 10 --ticks 200 --scenario diurnal --amp 0.3 --seed 7
```

The simulator generates simple traffic patterns (diurnal, spiky, sawtooth) and brute-forces the worst sliding-window error to verify the bound.

## Use as a library

```python
from core.limiter import FairLimiter

q = 10
lim = FairLimiter(q)

# planned increments scaled by q (ints, here: [0,3,0,1,2,0])
plan_q = [0, 3, 0, 1, 2, 0]
out = [lim.step(x_q) for x_q in plan_q]
print(out)  # list of 0/1 tokens per tick
```

---

## Project Layout

```text
quanta-flow/
├─ core/
│  ├─ __init__.py
│  └─ limiter.py          # carry-rule engine
├─ sim/
│  ├─ __init__.py
│  └─ run_sim.py           # CLI simulator
├─ examples/
│  └─ minimal.py           # 10-line demo loop
├─ tests/
│  ├─ __init__.py
│  ├─ test_properties.py   # property tests + bound checks
│  └─ test_witness.py      # tight witness hits (1−1/q)
├─ math/
│  ├─ __init__.py
│  └─ math_proofs.md       # bound proof & tight witness
├─ README.md
├─ LICENSE
├─ CITATION.cff
└─ pyproject.toml
```

---

## Tests

Property tests verify:
- Random sequences on the 1/q grid never exceed the (1 − 1/q) bound
- A tight witness sequence hits the bound exactly
- Multi-token extension respects the scaled bound M × (1 − 1/q)

```bash
pytest tests/test_properties.py
```

---

## Status

Reference implementation and learning artifact, not production advice.

For deployment you'll likely want: fuzzing on real traces, integration with your rate-limit service, and capacity-coupling logic for global mint constraints.

---

## Credits

QuantaFlow was developed as a collaborative human-AI project:

- **Concept & system framing:** Ani
- **Model-assisted proofs, writing & validation:** El (GPT-5.0) and Ren (Opus 4.5)

---

## References

- Bresenham, J.E. (1965). "Algorithm for computer control of a digital plotter." *IBM Systems Journal*, 4(1), 25–30.
- Berthé, V. & Tijdeman, R. (2002). "Balance properties of multi-dimensional words." *Theoretical Computer Science*, 273(1–2), 197–224.
- Berstel, J., Lauve, A., Reutenauer, C. & Saliola, F. (2008). *Combinatorics on Words: Christoffel Words and Repetitions in Words.* CRM/AMS.

---

## License

Apache-2.0
