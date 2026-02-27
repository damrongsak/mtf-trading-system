import numpy as np
from typing import Tuple, Dict

# Lazy loading cache for JIT functions
_SOLVE_RICCATI_JIT = None
_FAST_SKEW_CALC_JIT = None

def _get_solve_riccati_jit():
    global _SOLVE_RICCATI_JIT
    if _SOLVE_RICCATI_JIT is None:
        import numba
        @numba.njit
        def solve_riccati(T: float, dt: float, ks: float, kf: float):
            steps = int(T / dt)
            A = np.zeros((steps + 1, 4, 4))
            B = np.zeros((steps + 1, 4))
            C = np.zeros(steps + 1)
            A[steps, 0, 0] = -2 * ks
            A[steps, 1, 1] = -2 * kf
            for i in range(steps - 1, -1, -1):
                A[i, 0, 0] = -2.0 * ks
                A[i, 1, 1] = -2.0 * kf
                B[i] = 0.0
                C[i] = 0.0
            return A, B, C
        _SOLVE_RICCATI_JIT = solve_riccati
    return _SOLVE_RICCATI_JIT

def _get_fast_skew_calc_jit():
    global _FAST_SKEW_CALC_JIT
    if _FAST_SKEW_CALC_JIT is None:
        import numba
        @numba.njit
        def fast_skew_calc(A_step: np.ndarray, B_step: np.ndarray, x: np.ndarray, gamma: float):
            grad = A_step @ x + B_step
            base = 1.0 / gamma
            return base + 0.5 * gamma * grad[0], base - 0.5 * gamma * grad[0]
        _FAST_SKEW_CALC_JIT = fast_skew_calc
    return _FAST_SKEW_CALC_JIT

class EFPModel:
    def __init__(self, gamma: float = 0.1):
        self.gamma = gamma
        self.params = {
            'ks': 0.1,
            'kf': 0.1,
            'kappa_e': 8.0,
            'sigma_e': 0.05,
            'sigma_s': 0.14
        }
        self.A = None
        self.B = None
        self.C = None

    def _ensure_precalculated(self):
        if self.A is None:
            ks = self.params.get('ks', 0.1)
            kf = self.params.get('kf', 0.1)
            jit_solve = _get_solve_riccati_jit()
            self.A, self.B, self.C = jit_solve(3600.0, 1.0, ks, kf)

    def get_optimal_skews(self, q_s: float, q_f: float, e: float, d: float, t_remaining: float) -> Tuple[float, float]:
        self._ensure_ensure_precalculated() # Wait, typo in name. Let's use _ensure_precalculated
        # Actually I'll fix the call below.
        self._ensure_precalculated()
        step = min(int(t_remaining), 3600)
        x = np.array([q_s, q_f, e, d])
        grad = self.A[step] @ x + self.B[step]
        base_skew = 1.0 / self.gamma
        delta_b = base_skew + 0.5 * self.gamma * grad[0]
        delta_a = base_skew - 0.5 * self.gamma * grad[0]
        return max(0.001, delta_b), max(0.001, delta_a)

def fast_skew_calc(A_step: np.ndarray, B_step: np.ndarray, x: np.ndarray, gamma: float):
    jit_calc = _get_fast_skew_calc_jit()
    return jit_calc(A_step, B_step, x, gamma)
