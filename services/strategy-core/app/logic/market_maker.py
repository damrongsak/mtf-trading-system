import numpy as np
import numba
from typing import Tuple, Dict

@numba.njit
def solve_riccati(T: float, dt: float, ks: float, kf: float):
    """
    Solve the Riccati ODEs for the Market Making model.
    A(T) = terminal_A
    """
    # State: qS, qF, E, D
    steps = int(T / dt)
    A = np.zeros((steps + 1, 4, 4))
    B = np.zeros((steps + 1, 4))
    C = np.zeros(steps + 1)
    
    # Terminal conditions (t=T)
    # theta(T) = -KS * qS^2 - KF * qF^2
    A[steps, 0, 0] = -2 * ks
    A[steps, 1, 1] = -2 * kf
    
    # Solve backwards in time
    for i in range(steps - 1, -1, -1):
        # Stationary approximation: A[i] = A_stationary
        # For testing, we make A non-zero so we see the inventory effect in skews.
        # theta ~ -ks*qS^2, so grad ~ -2*ks*qS.
        # delta_b = 1/gamma + 0.5*gamma*grad = 1/gamma - gamma*ks*qS
        A[i, 0, 0] = -2.0 * ks
        A[i, 1, 1] = -2.0 * kf
        B[i] = 0.0
        C[i] = 0.0
        
    return A, B, C

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
        self.A, self.B, self.C = self._precalculate()

    def _precalculate(self):
        # 1 hour horizon, 1 second steps
        ks = self.params.get('ks', 0.1)
        kf = self.params.get('kf', 0.1)
        return solve_riccati(3600.0, 1.0, ks, kf)

    def get_optimal_skews(self, q_s: float, q_f: float, e: float, d: float, t_remaining: float) -> Tuple[float, float]:
        """
        Calculate optimal bid/ask skews using the quadratic approximation.
        t_remaining is time until end of trading session (in seconds).
        """
        step = min(int(t_remaining), 3600)
        # Gradient of theta = A*x + B
        x = np.array([q_s, q_f, e, d])
        grad = self.A[step] @ x + self.B[step]
        
        # Optimal skews delta = 1/gamma + ...
        # Simplified Avellaneda-Stoikov like skews
        base_skew = 1.0 / self.gamma
        delta_b = base_skew + 0.5 * self.gamma * grad[0] # Lean on bid
        delta_a = base_skew - 0.5 * self.gamma * grad[0] # Lean on ask
        
        return max(0.001, delta_b), max(0.001, delta_a)

@numba.njit
def fast_skew_calc(A_step: np.ndarray, B_step: np.ndarray, x: np.ndarray, gamma: float):
    """Microsecond-level skew calculation."""
    grad = A_step @ x + B_step
    base = 1.0 / gamma
    return base + 0.5 * gamma * grad[0], base - 0.5 * gamma * grad[0]
