"""Extraction Q_int/Q_ext depuis trace S21 réelle (VNA) — résonateur hanger.

Modèle standard (Probst et al. 2015, style resonator_tools) :
    S21(f) = a.e^{iα}.e^{-2πifτ} [ 1 - (Ql/Qc.e^{iφ}) / (1 + 2i.Ql.(f-fr)/fr) ]
Pipeline : délai sur ailes -> cercle algébrique (Kasa) -> phase vs f (Ql, fr,
init par pente centrale, essai ±signe) -> diamètre (Qc, φ) -> point fixe
(déconvolution résonance -> τ exact sur TOUS les points) -> polish joint.
Puis Q_int^-1 = Q_l^-1 - Q_c^-1  -> CavityQED.from_s21() -> T1/T2 MESURÉS.

Formats CSV banc acceptés : f,I,Q  ou  f,mag_dB,phase_deg. SI. MIT.
"""
from __future__ import annotations

import numpy as np
from scipy.optimize import least_squares


def s21_hanger(f, fr, Ql, Qc, phi=0.0, tau=0.0, a=1.0, alpha=0.0):
    """Réponse complexe d'un résonateur hanger. f, fr en Hz."""
    f = np.asarray(f, float)
    env = a * np.exp(1j * alpha) * np.exp(-2j * np.pi * f * tau)
    return env * (1 - (Ql / Qc * np.exp(1j * phi))
                  / (1 + 2j * Ql * (f - fr) / fr))


def synth_trace(fr=7e9, Qint=1e6, Qext=2e4, phi=0.08, tau=50e-9,
                a=0.9, alpha=0.3, npts=1001, span_lw=10.0, sigma=0.002,
                seed=7):
    """Trace VNA synthétique RÉALISTE (bruit complexe gaussien) + vrais params."""
    Ql = 1 / (1 / Qint + 1 / Qext)
    f = np.linspace(fr - span_lw * fr / Ql, fr + span_lw * fr / Ql, npts)
    ideal = s21_hanger(f, fr, Ql, Qext, phi, tau, a, alpha)
    rng = np.random.default_rng(seed)
    noisy = ideal + rng.normal(0, sigma, npts) + 1j * rng.normal(0, sigma, npts)
    truth = {'fr': fr, 'Ql': Ql, 'Qc': Qext, 'Qint': Qint, 'phi': phi,
             'tau': tau, 'a': a, 'alpha': alpha}
    return f, noisy, truth


def _tau_wings(f, s, frac=0.15):
    """Délai câble depuis la pente de phase sur les AILES (hors résonance)."""
    n = len(f)
    m = np.r_[0:int(n * frac), int(n * (1 - frac)):n]
    dphi = np.unwrap(np.angle(s[m]))
    tau = float(-np.polyfit(f[m], dphi, 1)[0] / (2 * np.pi))
    return float(np.clip(tau, -1e-6, 1e-6))


def _circle_fit(z):
    """Cercle algébrique (Kasa) -> (centre complexe, rayon). Indépendant de f."""
    z = np.asarray(z, complex)
    x, y = z.real, z.imag
    A = np.c_[x, y, np.ones_like(x)]
    D, E, F = np.linalg.lstsq(A, -(x ** 2 + y ** 2), rcond=None)[0]
    C = complex(-D / 2, -E / 2)
    return C, float(np.sqrt(max(abs(C) ** 2 - F, 1e-18)))


def _wings(n, frac=0.15):
    return np.r_[0:int(n * frac), int(n * (1 - frac)):n]


def _resonance_stage(f, s, fr0, tau):
    """Cercle + phase -> (Ql, fr, Qc, phi, a, alpha). Tau fixé."""
    n = len(f)
    wg = _wings(n)
    s2 = s * np.exp(2j * np.pi * f * tau)
    C, R = _circle_fit(s2)
    z = s2 - C
    off = float(np.angle(np.median(z[wg])))
    th = np.unwrap(np.angle(z * np.exp(-1j * off)))
    i0 = int(np.argmin(np.abs(s)))
    j = np.abs(f - f[i0]) < (f[-1] - f[0]) * 0.02
    sl = np.polyfit(f[j], th[j], 1)[0]
    Qg = float(np.clip(abs(sl) * fr0 / 4, 1e2, 1e8))
    best = None
    for sgn in (1.0, -1.0):
        def phres(p, sgn=sgn):
            t0, lQ, dfr = p
            return (t0 + sgn * 2 * np.arctan(2 * np.exp(lQ)
                    * (f - fr0 - dfr * 1e6) / fr0) - th)

        sol = least_squares(phres, [float(th[i0]), np.log(Qg), 0.0],
                            x_scale='jac', max_nfev=5000)
        if best is None or sol.cost < best.cost:
            best = sol
    _, lQl, dfr = best.x
    Ql, fr = float(np.exp(lQl)), float(fr0 + dfr * 1e6)
    off_pt = np.median(s2[wg])
    wn = s2 / off_pt
    Qc = float(Ql / max(2 * R / abs(off_pt), 1e-9))
    i_fr = int(np.argmin(np.abs(f - fr)))
    phi = float(np.angle(1 - wn[i_fr]))
    return Ql, fr, Qc, phi, float(abs(off_pt)), float(np.angle(off_pt))


def _fit_joint(f, s, fr, Ql, Qc, phi, tau, a, alpha):
    """Polish joint 7 params depuis une excellente initialisation."""
    bnd = float(f[-1] - f[0]) / 2 / 1e6

    def res1(p):
        dd, lL, lC, ph_, ta, aa, al = p
        m = s21_hanger(f, fr + dd * 1e6, float(np.exp(lL)),
                       float(np.exp(lC)), ph_, ta, aa, al)
        return np.r_[((m - s).real), ((m - s).imag)]

    p1 = [0.0, np.log(Ql), np.log(Qc), phi, tau, a, alpha]
    lo1 = [-bnd, np.log(Ql) - 1, np.log(Qc) - 1, phi - 0.3, tau - 20e-9,
           a * 0.5, alpha - 1]
    hi1 = [bnd, np.log(Ql) + 1, np.log(Qc) + 1, phi + 0.3, tau + 20e-9,
           a * 1.5, alpha + 1]
    sol1 = least_squares(res1, p1, bounds=(lo1, hi1), x_scale='jac',
                         max_nfev=5000)
    dd, lL, lC, ph_, ta, aa, al = sol1.x
    return (float(fr + dd * 1e6), float(np.exp(lL)), float(np.exp(lC)),
            float(ph_), float(ta), float(aa), float(al), bool(sol1.success))


def fit_s21(f, s):
    """Fit complet -> dict(fr, Ql, Qc, Qint, phi, tau, a, alpha, success)."""
    f = np.asarray(f, float)
    s = np.asarray(s, complex)
    fr0 = float(f[int(np.argmin(np.abs(s)))])
    tau = _tau_wings(f, s)
    for _ in range(2):  # point fixe : résonance -> τ exact -> résonance
        Ql, fr, Qc, phi, a, alpha = _resonance_stage(f, s, fr0, tau)
        res = 1 - (Ql / Qc * np.exp(1j * phi)) / (1 + 2j * Ql * (f - fr) / fr)
        dphi = np.unwrap(np.angle(s / res))
        tau = float(np.clip(-np.polyfit(f, dphi, 1)[0] / (2 * np.pi),
                            -1e-6, 1e-6))
    Ql, fr, Qc, phi, a, alpha = _resonance_stage(f, s, fr0, tau)
    fr, Ql, Qc, phi, tau, a, alpha, ok = _fit_joint(f, s, fr, Ql, Qc, phi,
                                                   tau, a, alpha)
    inv = 1 / Ql - 1 / Qc
    return {'fr': fr, 'Ql': Ql, 'Qc': Qc,
            'Qint': float(1 / inv) if inv > 0 else float('inf'),
            'phi': float(phi), 'tau': float(tau), 'a': float(a),
            'alpha': float(alpha), 'success': ok}


def save_csv(path, f, s):
    f = np.asarray(f, float)
    s = np.asarray(s, complex)
    np.savetxt(path, np.c_[f, s.real, s.imag], delimiter=',',
               header='f_Hz,I,Q', comments='')


def load_csv(path):
    """Lit f,I,Q (|.|<10) ou f,mag_dB,phase_deg -> (f, S21 complexe)."""
    d = np.loadtxt(path, delimiter=',', skiprows=1)
    f = d[:, 0]
    if np.max(np.abs(d[:, 1:3])) < 10:
        return f, d[:, 1] + 1j * d[:, 2]
    mag = 10 ** (d[:, 1] / 20)
    return f, mag * np.exp(1j * np.deg2rad(d[:, 2]))
