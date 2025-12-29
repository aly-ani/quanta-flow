# QuantaFlow — quantized sliding-window fairness for API rate limits

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](#)
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)](#)
[![CI](https://github.com/aly-ani/quanta-flow/actions/workflows/ci.yml/badge.svg)](https://github.com/aly-ani/quanta-flow/actions/workflows/ci.yml)


QuantaFlow is a tiny, deterministic limiter with a provable bound on how far actual behavior can drift from a fractional plan in any contiguous time window.

If you plan on a 1/q grid (for example, tenths per tick), QuantaFlow guarantees that for every sliding window \(W\),

$$
\left|\sum_{t \in W} (x_t - y_t)\right| \le 1 - \frac{1}{q}.
$$

That’s strictly tighter than the classic “≤ 1 token per window” folklore bound.

---
## Why this matters

Token Bucket: per-window drift can spike to >1 token; Leaky Bucket: smoother but window error is opaque.  
**QuantaFlow:** on a 1/q lattice, every contiguous window’s drift is $$≤ 1−\tfrac{1}{q}$$
(tight) → Predictable SLOs, O(1) state.

**Why QuantaFlow beats Token/Leaky Bucket (in one breath)**  
• Token Bucket: worst-case per-window drift can exceed 1 token; hard to bound for arbitrary windows.  
• Leaky Bucket: smoother, but the window error is opaque and depends on leak rate vs. plan.  
• QuantaFlow: on a 1/q lattice, every contiguous window’s drift is ≤ 1 − 1/q, and that bound is tight.  
• One-sentence proof sketch: maintain E ∈ [0,q−1] as the integer leftover; cumulative drift R_t = Σ(x_t−y_t) satisfies the invariant **R_t = E_t / q**, so |R_t| ≤ (q−1)/q.  
• Tight witness: choose q−1 ticks of x_q=1 (i.e., x=1/q) then 0; just before an emission, E=q−1 ⇒ drift=(q−1)/q.  
• Result: predictable SLOs with O(1) state and no float drift.

### Comparison

| Scheme        | Worst-case drift bound (any window) | State per tenant | Burst handling         | Determinism |
|---------------|-------------------------------------|------------------|------------------------|-------------|
| Token Bucket  | Not globally bounded (depends on burst & window alignment) | tokens, last-refill | Allows bursts up to bucket size; window error can spike | Yes |
| Leaky Bucket  | Opaque; depends on leak vs. arrivals | queue/level      | Smooths bursts; error hard to reason about | Yes |
| **QuantaFlow**| **≤ 1 − 1/q (tight)**               | **E ∈ [0, q−1]** | Emits at carry; windows stay close to plan | **Yes** |

---

## Core guarantee (Ani–El–Ren lemma)

Let planned fractional increments lie on a 1/q grid:  
**xₜ ∈ {0, 1/q, 2/q, …, 1}** for each tick t.  
The limiter emits integer tokens **yₜ ∈ {0,1}**.

Then for **every** contiguous window **W**,
\[
\Big|\sum_{t\in W} (x_t - y_t)\Big| \le 1 - \frac{1}{q}.
\]

The constant \(1-\tfrac{1}{q}\) is worst-case optimal (tight witness and proof in [`math/math_proofs.md`](math/math_proofs.md))—strictly tighter than the classic “≤ 1 token per window” folklore bound for \(q\ge 2\).

---

## The carry-rule algorithm (fixed-point)

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

State per tenant:

- E = leftover in [0, q-1].
    

On each tick:

1. Add the planned increment (scaled by q) to E.
    
2. If E >= q, emit one token and subtract q.
    
3. Otherwise, emit zero.
    

Scaling to up to M tokens per tick is supported by looping the carry; the bound becomes M * (1 - 1/q).

---

## Why this matters

In multi-tenant APIs you plan fractional budgets (e.g., 0.3 / 100 ms) but must mint integer tokens each tick. Naive float accumulation or rounding causes:
- unlucky tenants to get false-throttled in bad windows,
- bursty/noisy tenants to exploit sawtooth artifacts,
- fuzzier SLOs/billing than your spec implies.

QuantaFlow’s carry rule on a 1/q lattice keeps every sliding window close to the plan—online, with **O(1)** state per tenant.

---

## Install / Quickstart

```bash
git clone <repo-url> && cd quanta-flow
pip install -e .
pytest -q
python -m sim.run_sim --q 10 --ticks 200 --scenario diurnal --amp 0.3 --seed 7
```

The simulator generates simple traffic patterns (diurnal, spiky, sawtooth) and brute-forces the worst sliding-window error to verify the bound.

---

### Use as a library

You can also call the limiter directly from Python:

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
│  └─ run_sim.py          # CLI simulator
├─ examples/
│  └─ minimal.py          # 10-line demo loop
├─ tests/
│  ├─ __init__.py
│  ├─ test_properties.py  # property tests + bound checks
│  └─ test_witness.py     # tight witness hits (1−1/q)
├─ math/
│  ├─ __init__.py
│  └─ math_proofs.md      # Ani–El–Ren lemma & theorem
├─ README.md
├─ LICENSE
├─ CITATION.cff
└─ pyproject.toml
```
Components at a glance: **core** = limiter, **sim** = CLI to brute-force worst windows, **examples** = minimal usage, **tests** = properties + tight-witness, **math** = proofs.
---

## Tests

We use simple property tests to sanity-check the implementation:

- random sequences on the 1/q grid never exceed the (1 - 1/q) bound (up to float slack),
    
- a tight witness sequence hits the bound exactly,
    
- a basic multi-token extension respects the scaled bound M * (1 - 1/q).
    
From PyCharm you can run `tests/test_properties.py` directly; or from the terminal:

```bash
pytest tests/test_properties.py
```

---

## Status

Reference implementation / learning artifact, not production advice.
For deployment you’ll likely want: more fuzzing on real traces, integration with your rate-limit service, and capacity-coupling logic for global mint constraints.  

---

## Credits  
  
QuantaFlow is based on the Ani–El–Ren sliding-window lemma:  
  
- Concept & system framing: Aly Ani    
- Model-assisted proofs / writing & validation: 'El' & 'Ren' (ChatGPT-5.0 and Opus 4.5 respectively)    
  
If you use this work, please cite the repository as:
```
Aly Ani. QuantaFlow: quantized sliding-window fairness for API rate limits (Version v0.1.0) [Computer software]. https://github.com/<aly-ani>/quanta-flow
```
**License:** Apache-2.0
