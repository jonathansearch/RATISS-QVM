"""Tests extracteur S21 : fit trace synthétique réaliste + CSV + from_s21. MIT."""
import sys
sys.path.insert(0, '/home/user/RATISS-QVM')


def test_fit_overcoupled():
    from ratiss_qpu.s21 import synth_trace, fit_s21
    f, s, truth = synth_trace()
    r = fit_s21(f, s)
    assert r['success']
    assert abs(r['fr'] - truth['fr']) / truth['fr'] < 1e-6
    assert abs(r['Ql'] - truth['Ql']) / truth['Ql'] < 0.02, r['Ql']
    assert abs(r['Qc'] - truth['Qc']) / truth['Qc'] < 0.05, r['Qc']
    assert abs(r['tau'] - truth['tau']) < 2e-9, r['tau']
    assert 0.3 < r['Qint'] / truth['Qint'] < 3.0  # surcouplé : fondamental


def test_fit_undercoupled_qint():
    from ratiss_qpu.s21 import synth_trace, fit_s21
    f, s, truth = synth_trace(Qint=2e4, Qext=1e6, sigma=5e-4)
    r = fit_s21(f, s)
    assert abs(r['Qint'] - truth['Qint']) / truth['Qint'] < 0.15, r['Qint']


def test_csv_roundtrip():
    import tempfile, os
    from ratiss_qpu.s21 import synth_trace, fit_s21, save_csv, load_csv
    f, s, truth = synth_trace()
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, 'trace.csv')
        save_csv(p, f, s)
        f2, s2 = load_csv(p)
    r = fit_s21(f2, s2)
    assert abs(r['Ql'] - truth['Ql']) / truth['Ql'] < 0.02


def test_from_s21_t1t2():
    from ratiss_qpu.s21 import synth_trace, fit_s21
    from ratiss_qpu.microondes import CavityQED
    f, s, truth = synth_trace()
    c = CavityQED.from_s21(fit_s21(f, s))
    ref = CavityQED()
    assert abs(c.t1_s() - ref.t1_s()) / ref.t1_s() < 0.05, c.t1_s()
    assert abs(c.t2_s(0.01) - ref.t2_s(0.01)) / ref.t2_s(0.01) < 0.05
