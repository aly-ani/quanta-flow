# core/limiter.py

class FairLimiter:
    """
    QuantaFlow core: fixed-point carry-rule limiter.

    q: granularity (e.g. q=10 -> tenths; q=20 -> twentieths)
    E: leftover in [0, q-1], stored as integer
    """

    def __init__(self, q: int):
        if q < 2:
            raise ValueError("q must be >= 2")
        self.q = q
        self.E = 0  # invariant: 0 <= E < q

    def step(self, x_q: int) -> int:
        """
        Single time-step update.

        Parameters
        ----------
        x_q : int
            Planned increment scaled by q. Must be an integer in [0, q].

        Returns
        -------
        y : int
            0 or 1. Number of tokens to emit this tick.
        """
        if not 0 <= x_q <= self.q:
            raise ValueError(f"x_q must be in [0, {self.q}] (got {x_q})")

        self.E += x_q
        if self.E >= self.q:
            self.E -= self.q
            return 1
        return 0

    def reset(self) -> None:
        """Reset leftover to 0."""
        self.E = 0

    def __repr__(self) -> str:
        return f"FairLimiter(q={self.q}, E={self.E})"
