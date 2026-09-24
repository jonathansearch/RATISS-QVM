"""L'UNIVERS — S01 (naissance/trou noir) + S02 (Page/évaporation), N=300-1000.
Mêmes lois, mêmes formules (gravité soft-core, horizon, redshift, Kuramoto,
flips thermiques, M(t), réémission kick) + couche quantique : chaque qubit
porte un état |ψ> (produit) ; paires de Bell exactes ; déphasage gravité
(MODÈLE documenté : p = KH*DT*(rs/r)^2) ; gel à l'absorption (S01) ;
restauration à la réémission (S02 : l'info REVIT). MIT."""
import numpy as np
from . import qsubstrate as Q

MSIM, EPS = 0.5, 0.2
KAPPA, KQ, KH = 0.2, 1.0, 0.1
KH_HOLE = 0.3  # traçage intérieur : C->0 derrière horizon (Page)
DT = 0.02


def M_of(t, evap=True):
    if not evap or t < 30:
        return 0.5
    return max(0.02, 0.5 - 0.48 * (t - 30) / 170)


class Universe:
    def __init__(self, n=300, evap=True, seed=24, nv_temp=300.0, nv_t2_300k=1.0e-3):
        self.n, self.evap = n, evap
        # PROCESSEUR : déphasage NV (ratiss_qpu.coherence, Jarmola) dans l'univers
        from ratiss_qpu.coherence import DecoherenceModel
        t2 = DecoherenceModel(t2_300k_s=nv_t2_300k).t2_s(nv_temp)
        self.kh_nv = 0.005 * (1.0e-3 / t2)  # normalisé diamant naturel @300K
        rng = np.random.default_rng(seed)
        self.rng = rng
        r0 = np.concatenate([rng.uniform(2, 3.5, n // 2),
                             rng.uniform(4, 6, n - n // 2)])
        a0 = rng.uniform(0, 2 * np.pi, n)
        self.X = np.column_stack([r0 * np.cos(a0), r0 * np.sin(a0),
                                  rng.normal(0, 0.1, n)])
        vc = np.sqrt(MSIM / r0) * 0.35
        tang = np.column_stack([-np.sin(a0), np.cos(a0), np.zeros(n)])
        self.V = tang * vc[:, None] - (self.X / r0[:, None]) * 0.05
        self.th = rng.uniform(0, 2 * np.pi, n)
        self.om = rng.normal(1.0, 0.05, n)
        mlen = 4 * n
        msg = np.tile([1, 1, 0, 0], mlen // 4 + 1)[:mlen].astype(np.uint8)
        msg[:8] = [1, 0, 1, 0, 1, 0, 1, 0]
        self.tranches = [msg[i::n].copy() for i in range(n)]
        self.init = [t.copy() for t in self.tranches]
        self.vifs = np.ones(n, bool)
        self.psi = np.tile(np.array([1, 0], complex), (n, 1))
        self.pairs = {}   # a -> [b, psi4 ou rho4x4, mixed?]
        self.frozen = {}  # qubit absorbé -> état gelé
        self.t = 0.0

    # ---- portes DIRECT dans l'univers ----
    def gate(self, g, q, angle=None):
        if q in self.pairs:
            raise RuntimeError(f'q{q} en paire : 1q via pair_gate (v1: paires gelées en unitaire pur)')
        self.psi[q] = Q.apply_1q(self.psi[q], g, angle)

    def cx(self, a, b):
        if a in self.pairs or b in self.pairs:
            raise RuntimeError('v1 : CX hors-paires uniquement (paires = Bell)')
        pv = Q.apply_cx_to_pair(Q.pair_from_product(self.psi[a], self.psi[b]))
        self.pairs[a] = [b, pv, False]
        self.pairs[b] = [a, pv, False]

    def bell(self, a, b):
        if a in self.pairs or b in self.pairs:
            raise RuntimeError('qubit déjà en paire')
        pv = Q.bell_phi_plus()
        self.pairs[a] = [b, pv, False]
        self.pairs[b] = [a, pv, False]

    def concurrence(self, a):
        if a not in self.pairs:
            return 0.0
        _, s, mixed = self.pairs[a]
        return Q.concurrence_mixed(s) if mixed else Q.concurrence(s)

    def _partner(self, a):
        return self.pairs[a][0] if a in self.pairs else None

    def step(self):
        M = M_of(self.t, self.evap)
        rs = 2 * M
        r = np.linalg.norm(self.X, axis=1)
        # horizon : absorption + GEL quantique (S01)
        new = self.vifs & (r < rs)
        for i in np.where(new)[0]:
            if i in self.pairs:
                self.frozen[i] = ('pair', self.pairs[i][1].copy(), self.pairs[i][2])
            else:
                self.frozen[i] = ('prod', self.psi[i].copy())
            self.vifs[i] = False
        # réémission (S02) : kick + RESTAURATION (l'info revit)
        if self.evap:
            for i in np.where(~self.vifs)[0]:
                if r[i] > rs + 0.05 and i in self.frozen:
                    vesc = np.sqrt(2 * M / max(r[i], 1e-6))
                    self.V[i] = (self.X[i] / max(r[i], 1e-6)) * 1.5 * vesc
                    fr = self.frozen.pop(i)
                    if fr[0] == 'prod':
                        self.psi[i] = fr[1]
                    elif fr[0] == 'pair':
                        b = self._partner(i)
                        if b is not None and b in self.pairs:
                            self.pairs[i] = [b, fr[1], fr[2]]
                            self.pairs[b] = [i, fr[1], fr[2]]
                    self.vifs[i] = True
        # gravité
        rn = np.linalg.norm(self.X, axis=1)
        A = -MSIM * self.X / (rn[:, None] ** 2 + EPS ** 2) ** 1.5
        self.V[self.vifs] += A[self.vifs] * DT
        self.X[self.vifs] += self.V[self.vifs] * DT
        # horloges redshiftées + Kuramoto
        rn = np.linalg.norm(self.X, axis=1)
        self.th[self.vifs] += self.om[self.vifs] * np.sqrt(np.maximum(0, 1 - rs / np.maximum(rn[self.vifs], rs))) * DT
        thv = self.th[self.vifs]
        self.th[self.vifs] += DT * (KQ / self.n) * np.sin(self.th - thv[:, None]).sum(1)
        # flips thermiques
        for i in np.where(self.vifs)[0]:
            if self.rng.random() < KAPPA * DT / max(rn[i], rs):
                tr = self.tranches[i]
                tr[self.rng.integers(len(tr))] ^= 1
        # DÉPHASAGE gravité (modèle) sur états vifs
        for i in np.where(self.vifs)[0]:
            p = min(0.5, (KH * (rs / max(rn[i], rs)) ** 2 + self.kh_nv) * DT)
            if p <= 0:
                continue
            if i in self.pairs:
                b, s, mixed = self.pairs[i]
                rho = s if mixed else np.outer(s, s.conj())
                w = 0 if i < b else 1
                z1 = Q.Z if w == 0 else np.eye(2)
                z2 = np.eye(2) if w == 0 else Q.Z
                k0 = np.sqrt(1 - p) * np.eye(4)
                k1 = np.sqrt(p) * np.kron(z1, z2)
                rho = k0 @ rho @ k0.T.conj() + k1 @ rho @ k1.T.conj()
                self.pairs[i] = [b, rho, True]
                if b in self.pairs:
                    self.pairs[b] = [i, rho, True]
            else:
                a, c = self.psi[i]
                self.psi[i] = np.array([a, c * (1 - p)], complex)
                self.psi[i] /= np.linalg.norm(self.psi[i])
        # TRAÇAGE intérieur : paires coupées par l'horizon -> C s'effondre
        for i in np.where(~self.vifs)[0]:
            if i in self.pairs:
                b, s_, mixed = self.pairs[i]
                rho = s_ if mixed else np.outer(s_, s_.conj())
                w = 0 if i < b else 1
                z1 = Q.Z if w == 0 else np.eye(2)
                z2 = np.eye(2) if w == 0 else Q.Z
                p = min(0.5, KH_HOLE * DT)
                k0 = np.sqrt(1 - p) * np.eye(4)
                k1 = np.sqrt(p) * np.kron(z1, z2)
                rho = k0 @ rho @ k0.T.conj() + k1 @ rho @ k1.T.conj()
                self.pairs[i] = [b, rho, True]
                if b in self.pairs:
                    self.pairs[b] = [i, rho, True]
        self.t += DT

    def f_info(self):
        return float(np.mean([np.mean(self.tranches[i] == self.init[i])
                              for i in range(self.n)]))

    def run(self, steps, sample=10, watch=()):
        serie = []
        for s in range(steps + 1):
            if s % sample == 0:
                serie.append({'t': round(self.t, 2),
                              'n_abs': int((~self.vifs).sum()),
                              'F_info': round(self.f_info(), 4),
                              'C': {a: round(self.concurrence(a), 4) for a in watch}})
            if s == steps:
                break
            self.step()
        return serie
