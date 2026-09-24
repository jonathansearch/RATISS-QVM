"""Cellule de collision 6q — reprise exacte de synchrotron-24 (batch4/harvest2).
Murs AMP (tanh) + couches rx/rzz + contact rzz(λ) sur (2,3). MIT."""
import numpy as np
from qiskit import QuantumCircuit

R = np.arange(8)
F = 0.5 * (np.tanh(1 * (R + 2.5)) - np.tanh(1 * (R - 4.5)))
AMP = np.sqrt(F / F.sum())


def init_murs(c):
    c.initialize(AMP, [0, 1, 2])
    c.initialize(AMP, [3, 4, 5])


def couche(c, lam):
    c.rx(0.2, range(6))
    for a, b in ((0, 1), (1, 2), (3, 4), (4, 5)):
        c.rzz(0.2, a, b)
    if lam:
        c.rzz(lam, 2, 3)  # LE CONTACT


def pop(lam, nl=2, echo=False):
    c = QuantumCircuit(6, 6)
    init_murs(c)
    u = QuantumCircuit(6)
    for _ in range(nl):
        couche(u, lam)
    c.compose(u, inplace=True)
    if echo:
        c.compose(u.inverse(), inplace=True)
    c.measure(range(6), range(6))
    return c


def page_circuit(qb, lam, base):
    c = QuantumCircuit(6, 6)
    init_murs(c)
    if lam:
        u = QuantumCircuit(6)
        for _ in range(2):
            couche(u, lam)
        c.compose(u, inplace=True)
    if base == 'X':
        c.h(qb)
    elif base == 'Y':
        c.sdg(qb)
        c.h(qb)
    c.measure(qb, 0)
    return c


def bell():
    c = QuantumCircuit(2, 2)
    c.h(0)
    c.cx(0, 1)
    c.measure([0, 1], [0, 1])
    return c
