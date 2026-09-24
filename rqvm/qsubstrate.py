"""Substrat quantique de l'univers : états-produit (N=300-1000) + paires exactes.
1q exact partout ; CX(a,b) promeut la paire en état 2q exact (4-dim).
Limite assumée v1 : paires uniquement (pas de GHZ-3+). MIT."""
import numpy as np

H = np.array([[1, 1], [1, -1]], complex) / np.sqrt(2)
X = np.array([[0, 1], [1, 0]], complex)
Y = np.array([[0, -1j], [1j, 0]], complex)
Z = np.array([[1, 0], [0, -1]], complex)


def rx(t):
    return np.cos(t / 2) * np.eye(2) - 1j * np.sin(t / 2) * X


def ry(t):
    return np.cos(t / 2) * np.eye(2) - 1j * np.sin(t / 2) * Y


def rz(t):
    return np.cos(t / 2) * np.eye(2) - 1j * np.sin(t / 2) * Z


GATES_1Q = {'h': H, 'x': X, 'y': Y, 'z': Z, 'rx': rx, 'ry': ry, 'rz': rz}


def apply_1q(psi, g, angle=None):
    u = GATES_1Q[g](angle) if g in ('rx', 'ry', 'rz') else GATES_1Q[g]
    return (u @ psi.reshape(2)).ravel()


def bell_phi_plus():
    return np.array([1, 0, 0, 1], complex) / np.sqrt(2)


def pair_from_product(pa, pb):
    return np.kron(pa.reshape(2), pb.reshape(2)).reshape(4)


CX = np.array([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0, 1], [0, 0, 1, 0]], complex)


def apply_cx_to_pair(rho_vec):
    return (CX @ rho_vec.reshape(4)).ravel()


def concurrence(psi4):
    """Wootters pour état pur 2q : C = |<ψ|σy⊗σy|ψ*>|."""
    yy = np.kron(Y, Y)
    return float(abs(psi4.reshape(4).conj() @ yy @ psi4.reshape(4)))


def dephase_pair(psi4, which, p):
    """Canal déphasage (modèle) sur un membre : mélange via Kraus Z.
    Retourne matrice densité 4x4 (la paire devient mixte)."""
    rho = np.outer(psi4, psi4.conj())
    z = Z if which == 0 else np.eye(2)
    w = np.eye(2) if which == 0 else Z
    k1 = np.kron(np.sqrt(1 - p) * np.eye(2), np.sqrt(1 - p) * np.eye(2))
    k2 = np.kron(np.sqrt(p) * z, np.sqrt(p) * w)
    return k1 @ rho @ k1.conj().T + k2 @ rho @ k2.conj().T


def concurrence_mixed(rho):
    """Wootters mixte : max(0, l1-l2-l3-l4) des vp de R."""
    yy = np.kron(Y, Y)
    r = rho @ yy @ rho.conj() @ yy
    ev = np.sort(np.real(np.linalg.eigvals(r)))[::-1]
    ev = np.maximum(ev, 0)
    return float(max(0, np.sqrt(ev[0]) - np.sqrt(ev[1]) - np.sqrt(ev[2]) - np.sqrt(ev[3])))


def measure_1q(psi, rng):
    p0 = float(abs(psi[0]) ** 2)
    return 0 if rng.random() < p0 else 1
