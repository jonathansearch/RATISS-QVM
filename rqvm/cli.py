"""CLI : python -m rqvm.cli circuit.qasm --twin kingston --shots 2000. MIT."""
import argparse


def main():
    ap = argparse.ArgumentParser(description='RATISS-QVM : ordinateur quantique virtuel')
    ap.add_argument('qasm', help='fichier QASM2')
    ap.add_argument('--twin', default='kingston', choices=['kingston', 'marrakesh'])
    ap.add_argument('--shots', type=int, default=2000)
    ap.add_argument('--engine', default='twin', choices=['twin', 'exact', 'aer'])
    a = ap.parse_args()
    from qiskit import qasm2
    from .twins import TwinBackend
    from .engines import run
    circ = qasm2.load(a.qasm)
    if a.engine == 'twin':
        counts = TwinBackend(a.twin).run(circ, shots=a.shots).result().get_counts()
    else:
        counts = run(circ, shots=a.shots, engine=a.engine)
    from .observables import zz_contact
    print('counts:', dict(sorted(counts.items(), key=lambda x: -x[1])[:5]), '...')
    if circ.num_qubits == 6:
        print('zz_contact:', round(zz_contact(counts), 4))


if __name__ == '__main__':
    main()
