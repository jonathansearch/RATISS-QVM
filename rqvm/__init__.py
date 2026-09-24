"""RATISS-QVM — ordinateur quantique virtuel (symbiose).

Fidélité Google-qsim + puissance Qiskit-Aer + architecture synchrotron-24
(cellule 6q, observables, jumeaux K/M) + outils ratiss_qpu/bench.
SPDX-License-Identifier: MIT
"""
__version__ = '0.1.0'
from .cell import AMP, init_murs, couche, pop, page_circuit, bell  # noqa: F401
from .observables import zz_contact, mi_lr, entropy_dist  # noqa: F401
from .engines import run, ExactEngine, AerEngine, QsimEngine  # noqa: F401
from .twins import TwinBackend, load_twin_data, noise_model_for  # noqa: F401
