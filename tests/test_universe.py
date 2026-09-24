"""Tests univers 300q : portes exactes, paires, dip+revival, N=1000. MIT."""
import sys
sys.path.insert(0, '/home/user/RATISS-QVM')
import numpy as np


def test_gates_exact():
    from rqvm.universe import Universe
    U = Universe(n=10)
    U.gate('h', 0)
    assert np.allclose(np.abs(U.psi[0]), [0.7071, 0.7071], atol=1e-3)
    U.gate('x', 1)
    assert np.allclose(np.abs(U.psi[1]), [0, 1], atol=1e-6)
    U.gate('rx', 2, angle=np.pi)
    assert np.allclose(np.abs(U.psi[2]), [0, 1], atol=1e-6)


def test_bell_and_cx():
    from rqvm.universe import Universe
    U = Universe(n=10)
    U.bell(0, 1)
    assert abs(U.concurrence(0) - 1.0) < 1e-9
    U.gate('h', 2)
    U.cx(2, 3)
    assert abs(U.concurrence(2) - 1.0) < 1e-9


def test_dephasing_monotone():
    from rqvm.universe import Universe
    U = Universe(n=60, seed=1)
    U.bell(0, 1)
    cs = [U.concurrence(0)]
    for _ in range(300):
        U.step()
    cs.append(U.concurrence(0))
    assert cs[1] < cs[0] and cs[1] >= 0.0


def test_dip_revival_mini():
    from rqvm.universe import Universe
    U = Universe(n=60, seed=1)
    r0 = np.linalg.norm(U.X, axis=1)
    a = int(np.where(r0 < 3.0)[0][0])
    b = int(np.where(r0 > 4.5)[0][0])
    U.X[a] = np.array([2.5, 0.0, 0.0])
    U.V[a] = np.array([-0.05, 0.0, 0.0])
    U.bell(a, b)
    cs = []
    for s in range(2601):
        if s % 100 == 0:
            cs.append(U.concurrence(a))
        U.step()
    i = int(np.argmin(cs))
    assert min(cs) < 0.25, cs
    assert max(cs[i:]) > min(cs) + 0.2, cs  # résurrection


def test_n1000_smoke():
    from rqvm.universe import Universe
    U = Universe(n=1000, seed=7)
    U.bell(0, 999)
    for _ in range(20):
        U.step()
    assert U.concurrence(0) > 0.9
