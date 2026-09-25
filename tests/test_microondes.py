"""Tests micro-ondes cQED : Q->kappa, Purcell, Bose, Gambetta, evolve. MIT."""
import sys
sys.path.insert(0, '/home/user/RATISS-QVM')


def test_kappa_from_q():
    from ratiss_qpu.microondes import CavityQED
    import numpy as np
    k = CavityQED().kappa() / 2 / np.pi
    assert abs(k - 357e3) / 357e3 < 0.05, k  # 7GHz / 19608


def test_purcell_t1():
    from ratiss_qpu.microondes import CavityQED
    c = CavityQED()
    assert 150e-6 < c.t1_purcell_s() < 210e-6, c.t1_purcell_s()  # ~178us
    assert 80e-6 < c.t1_s() < 150e-6, c.t1_s()  # ~112us avec T1_int


def test_chi_dispersif():
    from ratiss_qpu.microondes import CavityQED
    import numpy as np
    chi = CavityQED().chi() / 2 / np.pi
    assert abs(abs(chi) - 5e6) / 5e6 < 0.1, chi  # g^2/D = -5MHz


def test_bose_froid_chaud():
    from ratiss_qpu.microondes import n_th
    assert n_th(7e9, 0.010) < 1e-9  # frigo : vide
    n = n_th(5e9, 300.0)
    assert 1200 < n < 1300, n  # kT/hf = 1250


def test_t2_thermique():
    from ratiss_qpu.microondes import CavityQED
    c = CavityQED()
    t2f, t2c = c.t2_s(0.010), c.t2_s(0.050)
    assert t2f <= 2 * c.t1_s() * 1.001  # borne physique
    assert abs(t2f - 2 * c.t1_s()) / t2f < 0.01  # froid : limite T1
    assert t2c < 0.9 * t2f, (t2c, t2f)  # chaud : dephasage thermique


def test_evolve_ultra_precis():
    import numpy as np
    from ratiss_qpu.microondes import CavityQED
    from ratiss_qpu.coherence import evolve_open
    c = CavityQED()
    rho0 = np.array([[0.5, 0.5], [0.5, 0.5]], dtype=complex)  # |+>
    H = np.zeros((2, 2), dtype=complex)
    t2 = c.t2_s(0.010)
    for t in (0.2 * t2, t2):
        rho = evolve_open(rho0, H, t, c, 0.010)
        assert abs(abs(rho[0, 1]) - 0.5 * np.exp(-t / t2)) < 0.02, (t, rho)


def test_purcell_sans_filtre():
    from ratiss_qpu.microondes import CavityQED
    c = CavityQED()
    assert c.suppression() == 1.0
    assert 150e-6 < c.t1_purcell_s() < 210e-6


def test_purcell_filtre_protege():
    from ratiss_qpu.microondes import CavityQED
    b = CavityQED(kappa_filt_hz=10e6)
    assert abs(b.suppression() - 160001) / 160001 < 0.01, b.suppression()
    assert b.t1_purcell_s() > 10.0  # 28.5 s : Purcell vaincu
    assert abs(b.t1_s() - 300e-6) / 300e-6 < 0.05  # limite intrinsèque
    assert b.t2_s(0.01) > CavityQED().t2_s(0.01) * 2.0  # T2 x2.7


def test_purcell_filtre_sur_qubit():
    from ratiss_qpu.microondes import CavityQED
    q = CavityQED(f_filt_hz=5e9, kappa_filt_hz=10e6)  # filtre sur qubit : rien
    assert q.suppression() == 1.0
