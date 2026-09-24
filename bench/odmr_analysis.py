"""Analyse des données du banc NV — de la mesure brute aux paramètres physiques.

C'est ici que la mesure RÉELLE recalibre le modèle. Chaque fonction prend des
données (fréquences/délais + comptages de photons) et extrait un paramètre
physique par ajustement de courbe (scipy.optimize.curve_fit, moindres carrés) :

- ODMR → fréquence de résonance + largeur de raie (fit lorentzien)
- Rabi → pulsation de Rabi Ω (fit sinusoïdal amorti)
- Ramsey → T2* (fit gaussien amorti oscillant)
- Hahn → T2 (fit exponentiel amorti)

Le tout alimente `recalibrate_model()` qui produit un `DecoherenceModel` calibré
sur les mesures réelles du banc camerounais — remplaçant les ordres de grandeur
documentés par des valeurs MESURÉES. C'est la boucle mesure→modèle de RATISS.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import curve_fit

from ratiss_qpu.coherence import DecoherenceModel
from ratiss_qpu.nv_center import D_ZERO_FIELD_HZ, GAMMA_E_HZ_PER_T


# --- Modèles d'ajustement (formes analytiques des signaux) ---

def _lorentzian(f, f0, amp, width, offset):
    """Lorentzienne (dip ODMR) : offset − amp·width²/((f−f0)²+width²)."""
    return offset - amp * width ** 2 / ((f - f0) ** 2 + width ** 2)


def _damped_sine(t, freq, amp, decay, phase, offset):
    """Sinusoïde amortie (Rabi) : offset + amp·cos(2π·freq·t+φ)·exp(−t/decay)."""
    return offset + amp * np.cos(2 * np.pi * freq * t + phase) * np.exp(-t / decay)


def _gauss_decay_osc(t, freq, amp, t2star, offset):
    """Ramsey : offset + amp·cos(2π·freq·t)·exp(−(t/T2*)²)."""
    return offset + amp * np.cos(2 * np.pi * freq * t) * np.exp(-((t / t2star) ** 2))


def _exp_decay(t, amp, t2, offset):
    """Hahn echo : offset + amp·exp(−2t/T2)."""
    return offset + amp * np.exp(-2.0 * t / t2)


# --- Fonctions d'ajustement ---

def fit_odmr(freqs: np.ndarray, counts: np.ndarray) -> dict:
    """Ajuste le dip ODMR → fréquence de résonance f0 et largeur de raie.

    Retourne {resonance_hz, linewidth_hz, contrast, success}."""
    f0_guess = freqs[np.argmin(counts)]
    offset_guess = float(np.max(counts))
    amp_guess = offset_guess - float(np.min(counts))
    width_guess = (freqs[-1] - freqs[0]) / 10.0
    try:
        popt, _ = curve_fit(
            _lorentzian, freqs, counts,
            p0=[f0_guess, amp_guess, width_guess, offset_guess],
            maxfev=10000,
        )
        f0, amp, width, offset = popt
        return {
            "resonance_hz": float(f0),
            "linewidth_hz": float(abs(width)),
            "contrast": float(amp / offset) if offset > 0 else 0.0,
            "success": True,
        }
    except RuntimeError:
        return {"resonance_hz": float(f0_guess), "linewidth_hz": float("nan"),
                "contrast": 0.0, "success": False}


def fit_rabi(taus: np.ndarray, counts: np.ndarray) -> dict:
    """Ajuste les oscillations de Rabi → pulsation Ω (Hz).

    Retourne {rabi_hz, decay_s, success}."""
    offset_guess = float(np.mean(counts))
    amp_guess = float((np.max(counts) - np.min(counts)) / 2.0)
    # Estimation de fréquence par FFT (robuste)
    dt = taus[1] - taus[0]
    spectrum = np.abs(np.fft.rfft(counts - offset_guess))
    freqs_fft = np.fft.rfftfreq(len(taus), dt)
    freq_guess = float(freqs_fft[np.argmax(spectrum[1:]) + 1]) if len(spectrum) > 1 else 1.0e6
    decay_guess = taus[-1] / 2.0
    try:
        popt, _ = curve_fit(
            _damped_sine, taus, counts,
            p0=[freq_guess, amp_guess, decay_guess, 0.0, offset_guess],
            maxfev=20000,
        )
        freq, amp, decay, phase, offset = popt
        return {"rabi_hz": float(abs(freq)), "decay_s": float(abs(decay)),
                "success": True}
    except RuntimeError:
        return {"rabi_hz": freq_guess, "decay_s": float("nan"), "success": False}


def fit_ramsey(taus: np.ndarray, counts: np.ndarray) -> dict:
    """Ajuste les franges de Ramsey → T2* (s).

    Retourne {t2star_s, detuning_hz, success}."""
    offset_guess = float(np.mean(counts))
    amp_guess = float((np.max(counts) - np.min(counts)) / 2.0)
    dt = taus[1] - taus[0]
    spectrum = np.abs(np.fft.rfft(counts - offset_guess))
    freqs_fft = np.fft.rfftfreq(len(taus), dt)
    freq_guess = float(freqs_fft[np.argmax(spectrum[1:]) + 1]) if len(spectrum) > 1 else 1.0e6
    t2_guess = taus[-1] / 3.0
    try:
        popt, _ = curve_fit(
            _gauss_decay_osc, taus, counts,
            p0=[freq_guess, amp_guess, t2_guess, offset_guess],
            maxfev=20000,
        )
        freq, amp, t2star, offset = popt
        return {"t2star_s": float(abs(t2star)), "detuning_hz": float(abs(freq)),
                "success": True}
    except RuntimeError:
        return {"t2star_s": t2_guess, "detuning_hz": freq_guess, "success": False}


def fit_hahn(taus: np.ndarray, counts: np.ndarray) -> dict:
    """Ajuste l'écho de Hahn → T2 (s). Retourne {t2_s, success}."""
    offset_guess = float(np.min(counts))
    amp_guess = float(np.max(counts) - np.min(counts))
    t2_guess = taus[-1] / 2.0
    try:
        popt, _ = curve_fit(
            _exp_decay, taus, counts,
            p0=[amp_guess, t2_guess, offset_guess],
            maxfev=10000,
        )
        amp, t2, offset = popt
        return {"t2_s": float(abs(t2)), "success": True}
    except RuntimeError:
        return {"t2_s": t2_guess, "success": False}


def b_field_from_resonance(resonance_hz: float) -> float:
    """Déduit le champ B (tesla) de la fréquence de résonance ODMR.
    f_res = D − γ_e·B  →  B = (D − f_res)/γ_e."""
    return float((D_ZERO_FIELD_HZ - resonance_hz) / GAMMA_E_HZ_PER_T)


@dataclass
class BenchMeasurements:
    """Les paramètres physiques mesurés sur le banc, prêts à recalibrer le modèle."""
    t1_s: float | None = None
    t2_s: float | None = None
    t2star_s: float | None = None
    rabi_hz: float | None = None
    resonance_hz: float | None = None
    b_field_t: float | None = None


def recalibrate_model(meas: BenchMeasurements, t_kelvin: float = 300.0) -> DecoherenceModel:
    """Produit un DecoherenceModel calibré sur les MESURES réelles du banc.

    Remplace les ordres de grandeur documentés par les valeurs mesurées.
    Seuls les paramètres effectivement mesurés (non None) sont injectés —
    jamais de valeur inventée. Si T1 n'est pas mesuré, on garde le défaut et on
    borne T2 ≤ 2·T1 (la borne physique reste garantie par DecoherenceModel)."""
    model = DecoherenceModel()
    if meas.t1_s is not None:
        model.t1_300k_s = meas.t1_s
    if meas.t2_s is not None:
        model.t2_300k_s = meas.t2_s
    elif meas.t2star_s is not None:
        # T2* < T2 toujours ; à défaut d'écho, on prend T2* comme borne basse honnête
        model.t2_300k_s = meas.t2star_s
    return model
