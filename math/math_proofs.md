# QuantaFlow Math Note (v1)

Quantized sliding-window fair rounding $≤ 1 − 1/q$, an optimal online carry rule,
and a mapping to multi-tenant API rate limiting.

## 1. Lemma (sliding-window bound)

Fix an integer $q \ge 2$. Let $x_1,\dots,x_n \in {0, 1/q, \dots, 1}$.

Then there exist $y_1,\dots,y_n \in {0,1}$ such that for every window $[s..t]$

$\left|\sum_{i=s}^{t} (x_i - y_i)\right| \le 1 - \frac{1}{q},$  


and this bound is tight.

Sketch:

- Let $S_k = \sum_{i=1}^k x_i$.
- Pick $\delta \in (0, 1/q)$.
- Define  
    
    $y_k = \lfloor S_k + \delta \rfloor - \lfloor S_{k-1} + \delta \rfloor,$  
    $\qquad$  
    $E_k = S_k - \sum_{i=1}^k y_i = {S_k + \delta} - \delta.$  
    
    
- Because each $x_i$ is a multiple of $1/q$, each $E_k$ lies in ${0, 1/q, \dots, 1-1/q}$.
- Any window sum is $E_t - E_{s-1}$, a difference of two values in $[0, 1-1/q]$, so the absolute value is at most $1 - 1/q$.
- Tightness is witnessed by $x = (0, 1/q, \dots, 1/q)$.

## 2. Online theorem (carry rule)

Inputs $x_k \in {0, 1/q, \dots, 1}$  arrive one by one. We must output $y_k \in {0,1}$ immediately.

Algorithm (carry rule):

- Maintain $E \in [0, 1 - 1/q].$
- On step $k$:
    - if $E + x_k < 1$, set $y_k = 0$, $E \leftarrow E + x_k$;
    - else set $y_k = 1$, (E \leftarrow E + x_k - 1).

Then at every time $t$, for every window $[s..t]$,

$\left|\sum_{i=s}^{t} (x_i - y_i)\right| \le 1 - \frac{1}{q}.$  

The constant $1 - 1/q$ is worst-case optimal for any online algorithm.

## 3. API rate-limit interpretation

Treat $x_{t,j}$ as per-tenant fractional mint plans on a 1/q grid and $y_{t,j}$ as integer tokens. Running the carry rule independently per tenant yields:


$\left|\sum_{i\in W} (x_{i,j} - y_{i,j})\right| \le 1 - \frac{1}{q}$  


for every tenant $j$ and every window $W$. Aggregating over a set of tenants $S$ gives a bound of $|S|(1 - 1/q)$.

This is strictly tighter than the usual “≤ 1 token per window” bound when plans are q-granular.
