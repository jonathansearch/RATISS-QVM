"""Décohérence thermique — équation maîtresse de Lindblad, dépendante de T.

Le cœur ultra-précis. Un qubit réel n'est jamais pur : il interagit avec le bain
thermique. La dynamique markovienne de sa matrice densité ρ obéit à Lindblad :

    dρ/dt = -i[H, ρ] + Σ_k γ_k ( L_k ρ L_k† − ½{L_k† L_k, ρ} )

Canaux pour le qubit NV :
- Relaxation (T1)      : L = σ₋ = |0><1|, taux γ1 = 1/T1. Le spin retombe vers ms=0.
- Déphasing pur (Tφ)   : L = σz, taux γφ. Détruit la cohérence de phase sans
                         changer les populations. 1/T2 = 1/(2T1) + 1/Tφ.

Dépendance en température (c'est LA transdisciplinarité : thermo × quantique) :
- T1(T) : relaxation spin-réseau à 2 phonons (processus Raman) pour le NV.
  À T > ~100 K, domine un comportement thermiquement activé. On utilise le modèle
  phénoménologique ajusté de Jarmola et al. (PRL 2012) : T1 chute quand T monte,
  ≈ 5 ms à 300 K, ≈ (T/300)^(-2) en première approximation locale.
- Tφ(T) : déphasing dominé par le bain de spins nucléaires ¹³C et les fluctuations
  magnétiques — faiblement dépendant de T en dessous de ~400 K (le ¹²C purifié
  le supprime presque). On le prend quasi-constant à 300 K.

RÈGLE RATISS : ces modèles sont phénoménologiques et SOURCÉS. Leurs paramètres
sont des ordres de grandeur à recalibrer sur le banc NV réel (MEMO).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .qstate import X, Z, bloch_vector, purity

SIGMA_MINUS = np.array([[0, 1], [0, 0]], dtype=complex)   # |0><1| relaxation
K_B = 1.380649e-23        # J/K
T_REF_K = 300.0           # température de référence


@dataclass
class DecoherenceModel:
    """Modèle T1/T2 d'un qubit NV en fonction de la température.

    t1_300k_s : T1 mesuré à 300 K (défaut 5 ms, Jarmola 2012)
    t2_300k_s : T2 mesuré à 300 K (défaut 1 ms diamant naturel ; ~1 s en ¹²C)
    """
    t1_300k_s: float = 5.0e-3
    t2_300k_s: float = 1.0e-3

    def t1_s(self, t_kelvin: float) -> float:
        """T1(T) : relaxation Raman 2-phonons ≈ T^-2 localement autour de 300 K
        (ordre de grandeur sourcé ; à recalibrer sur banc). Plancher à 1 µs."""
        t1 = self.t1_300k_s * (T_REF_K / max(t_kelvin, 1.0)) ** 2.0
        return float(max(t1, 1.0e-6))

    def t2_s(self, t_kelvin: float) -> float:
        """T2(T) ≤ 2·T1(T) toujours (borne physique). Déphasing quasi-indépendant
        de T à 300 K (bain ¹³C). On borne par 2·T1 pour la cohérence physique."""
        t1 = self.t1_s(t_kelvin)
        t2 = self.t2_300k_s * (T_REF_K / max(t_kelvin, 1.0)) ** 0.5
        return float(min(t2, 2.0 * t1))

    def coherent_ops(self, t_kelvin: float, gate_time_s: float) -> float:
        """Figure de mérite : nombre d'opérations cohérentes = T2 / t_porte."""
        return float(self.t2_s(t_kelvin) / max(gate_time_s, 1e-12))


def lindblad_rhs(rho, hamiltonian, gamma1, gamma_phi):
    """dρ/dt (Lindblad). γ1=1/T1 (relaxation), γφ=1/Tφ (déphasing pur). Exact."""
    drho = -1j * (hamiltonian @ rho - rho @ hamiltonian)
    L = SIGMA_MINUS
    drho += gamma1 * (L @ rho @ L.conj().T
                      - 0.5 * (L.conj().T @ L @ rho + rho @ L.conj().T @ L))
    Ld = Z
    drho += gamma_phi * (Ld @ rho @ Ld.conj().T
                         - 0.5 * (Ld.conj().T @ Ld @ rho + rho @ Ld.conj().T @ Ld))
    return drho


def evolve_open(rho0, hamiltonian, t_s, model, t_kelvin, steps=500):
    """Évolution Lindblad de ρ0 pendant t_s à température t_kelvin (RK4)."""
    t1 = model.t1_s(t_kelvin)
    t2 = model.t2_s(t_kelvin)
    gamma1 = 1.0 / t1
    gamma_phi = max(0.0, 1.0 / t2 - 0.5 / t1)   # 1/T2 = 1/(2T1) + 1/Tφ
    dt = t_s / steps
    rho = np.array(rho0, dtype=complex)
    for _ in range(steps):
        k1 = lindblad_rhs(rho, hamiltonian, gamma1, gamma_phi)
        k2 = lindblad_rhs(rho + 0.5 * dt * k1, hamiltonian, gamma1, gamma_phi)
        k3 = lindblad_rhs(rho + 0.5 * dt * k2, hamiltonian, gamma1, gamma_phi)
        k4 = lindblad_rhs(rho + dt * k3, hamiltonian, gamma1, gamma_phi)
        rho = rho + (dt / 6.0) * (k1 + 2 * k2 + 2 * k3 + k4)
    return 0.5 * (rho + rho.conj().T)   # re-Hermitisation (garde-fou numérique)


def bloch_trajectory(rho0, hamiltonian, t_max_s, model, t_kelvin, n_points=200):
    """Trajectoire du vecteur de Bloch (n_points, 3) sous décohérence.
    Un état cohérent reste près de la surface ; un état décohéré s'effondre
    vers le centre de la sphère de Bloch."""
    traj = np.zeros((n_points, 3))
    ts = np.linspace(0.0, t_max_s, n_points)
    rho = np.array(rho0, dtype=complex)
    for i in range(n_points):
        traj[i] = bloch_vector(rho)
        if i < n_points - 1:
            rho = evolve_open(rho, hamiltonian, ts[i + 1] - ts[i], model, t_kelvin)
    return traj


def psig_coherence(traj) -> float:
    """P_sig quantique = rayon de Bloch moyen le long de la trajectoire.

    ‖r‖ = 1 pour un état pur (surface), → 0 pour l'état maximalement mixte
    (centre). Contraction topologique de la sphère de Bloch = mesure géométrique
    directe de la cohérence restante. Plus proche de 1 = mieux."""
    radii = np.linalg.norm(traj, axis=1)
    return float(np.mean(radii))
