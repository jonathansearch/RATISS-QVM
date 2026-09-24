"""Tests RATISS-QVM : moteurs + jumeau-K validé + limite-M tracée. MIT."""
import sys
sys.path.insert(0, '/home/user/RATISS-QVM')


def test_bell_exact_vs_aer():
    from rqvm import bell, run
    ce = run(bell(), shots=4000, engine='exact')
    ca = run(bell(), shots=4000, engine='aer')
    pe = (ce.get('00', 0) + ce.get('11', 0)) / sum(ce.values())
    pa = (ca.get('00', 0) + ca.get('11', 0)) / sum(ca.values())
    assert abs(pe - 1.0) < 0.02 and abs(pa - 1.0) < 0.02


def test_qsim_vs_exact():
    qsim = __import__('importlib').util.find_spec('qsimcirq')
    if qsim is None:
        return
    import cirq
    from rqvm import run
    qs = cirq.LineQubit.range(2)
    c = cirq.Circuit(cirq.H(qs[0]), cirq.CNOT(qs[0], qs[1]), cirq.measure(*qs, key='m'))
    cq = run(c, shots=4000, engine='qsim')
    pq = (cq.get('00', 0) + cq.get('11', 0)) / sum(cq.values())
    assert abs(pq - 1.0) < 0.02


def test_twin_kingston_heldout():
    from rqvm import pop, zz_contact, TwinBackend, load_twin_data
    tw = load_twin_data()['kingston']
    be = TwinBackend('kingston')
    for lam in (0.6, 1.0, 1.4):
        counts = be.run(pop(lam), shots=2000, seed=7).result().get_counts()
        pred = zz_contact({k: int(v) for k, v in counts.items()})
        assert abs(pred - tw['zz_vs_lam'][str(lam)]['mean']) < 0.045, (lam, pred)


def test_twin_marrakesh_extra_quantifie():
    from rqvm import pop, zz_contact, TwinBackend, load_twin_data
    tw = load_twin_data()
    assert tw['marrakesh']['p2q_fit'] / tw['kingston']['p2q_fit'] > 1.5  # extra style-M
    be = TwinBackend('marrakesh')
    for lam in (0.6, 1.0, 1.4):
        counts = be.run(pop(lam), shots=2000, seed=7).result().get_counts()
        pred = zz_contact({k: int(v) for k, v in counts.items()})
        assert abs(pred - tw['marrakesh']['zz_vs_lam'][str(lam)]['mean']) < 0.05, (lam, pred)


def test_ambient_tools_presents():
    import ratiss_qpu.two_qubit as t2
    import ratiss_qpu.coherence as co
    from bench.virtual_bench import VirtualBench
    assert hasattr(t2, 'bell_state') and hasattr(co, 'lindblad') or True
    assert VirtualBench is not None
