"""Organe PORTEURS : cubes-qubits simulés, tranches disjointes, transport->seuil."""
import numpy as np


class Porteur:
    def __init__(self, pid, ptype, tranche, position):
        self.id = pid
        self.type = ptype          # 'I' = info pure, 'S' = structure
        self.tranche = tranche     # indices métriques (disjoints)
        self.position = np.array(position, float)
        self.phases = np.zeros(8)  # cube simulé : 8 sommets


def creer_porteurs(n_bits_total, n_porteurs=8, ptype="I", seed=3):
    rng = np.random.default_rng(seed + (0 if ptype == "I" else 1000))
    tailles = [n_bits_total // n_porteurs] * n_porteurs
    for i in range(n_bits_total % n_porteurs):
        tailles[i] += 1
    porteurs, debut = [], 0
    for i, t in enumerate(tailles):
        pos = rng.uniform(-3, 3, 3)  # départ : zone condensateur (externe)
        porteurs.append(Porteur(i, ptype, list(range(debut, debut + t)), pos))
        debut += t
    tous = [x for p in porteurs for x in p.tranche]
    assert len(set(tous)) == len(tous), "tranches NON disjointes !"
    return porteurs


def transporter(porteurs, point_focal, alpha=0.25):
    pf = np.array(point_focal, float)
    for p in porteurs:
        p.position += alpha * (pf - p.position)


def concentration(porteurs, tau, v_info=1.0):
    """Phi = (N_int x tau) / V_info. Le volume se resserre -> Phi explose."""
    n_int = sum(len(p.tranche) for p in porteurs)
    pos = np.array([p.position for p in porteurs])
    portee = pos.max(axis=0) - pos.min(axis=0)
    volume = float(max(np.prod(portee), 1e-6)) * v_info
    return (n_int * tau) / volume
