# QuantaFlow — quantized sliding-window fairness for API rate limits

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](#)
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)](#)

QuantaFlow is a tiny, deterministic limiter with a provable bound on how far actual behavior can drift from a fractional plan in any contiguous time window.

If you plan on a 1/q grid (for example, tenths per tick), QuantaFlow guarantees that for every sliding window \(W\),

$$
\left|\sum_{t \in W} (x_t - y_t)\right| \le 1 - \frac{1}{q}.
$$

That’s strictly tighter than the classic “≤ 1 token per window” folklore bound.


**License**: Apache-2.0

---

## Why?

In a multi-tenant API, you often have:

- per-tenant fractional budgets like 0.3 tokens per 100ms, and
    
- a rate limiter that must mint integer tokens each tick.
    

Naive rounding or float accumulation gives you:

- good tenants get false-throttled in unlucky windows,
    
- abusive or noisy tenants can exploit sawtooth bursts,
    
- SLOs and billing envelopes are fuzzier than they look on paper.
    

QuantaFlow uses a simple carry rule on a 1/q lattice to keep every window close to the plan, online and with O(1) state per tenant.

---

## Core guarantee (Ani–El–Ren lemma)

Assume each planned increment lies on a grid of step 1/q:

- x_t in {0, 1/q, 2/q, ..., 1}
    

Then there is an online, O(1)-state algorithm that outputs y_t in {0,1} such that for every window [s..t]:

```
| sum_{i = s..t} (x_i - y_i) | <= 1 - 1/q
```

and this constant is worst-case optimal. QuantaFlow implements that algorithm as a per-tenant mint loop.

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

## Usage

### Run the simulator

From the project root:

```bash
python -m sim.run_sim --q 10 --ticks 200 --scenario diurnal --amp 0.3 --seed 7
```

Example output:

```text
QuantaFlow simulation
  q           = 10
  ticks       = 200
  scenario    = diurnal
  max window error = 0.900000
  theory bound     = 0.900000
```

The simulator generates simple traffic patterns (diurnal, spiky, sawtooth) and brute-forces the worst sliding-window error to verify the bound.

---
### Use as a library

You can also call the limiter directly from Python:

```python
from core.limiter import FairLimiter

q = 10
lim = FairLimiter(q)

# planned increments scaled by q (here: [0, 0.3, 0, 0.1, 0.2, 0])
plan_q = [0, 3, 0, 1, 2, 0]

out = [lim.step(x_q) for x_q in plan_q]
print(out)  # list of 0/1 tokens per tick
```
---

## Project Layout

```text
quanta-flow/
  core/
    __init__.py
    limiter.py          # carry-rule engine
  sim/
    __init__.py
    run_sim.py          # CLI simulator
  tests/
    __init__.py
    test_properties.py  # property tests
  math/
    math_proofs.md      # Ani–El–Ren lemma & theorem
  README.md
  LICENSE
  CITATION.cff
  pyproject.toml
```

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

This is a reference implementation and learning artifact, not production advice.

The core algorithm and bound (the Ani–El–Ren lemma) are math-level solid; real systems would want:

- more extensive fuzzing on realistic traces,
    
- integration into an existing rate-limit service,
    
- capacity-coupling logic when global mint capacity is tight.
    

---

## Credits  
  
QuantaFlow is based on the Ani–El–Ren sliding-window lemma:  
  
- Concept & system framing: Aly Ani    
- Model-assisted proofs / writing: 'El' & 'Ren' (ChatGPT-5.0 and 5.1 respectively)    
  
If you use this work, please cite the repository as:
```
Aly Ani. QuantaFlow: quantized sliding-window fairness for API rate limits (Version v0.1.0) [Computer software]. https://github.com/<aly-ani>/quanta-flow
```