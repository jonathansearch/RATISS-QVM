"""Séquences de pulses micro-onde pour la mesure NV — définitions exactes.

Chaque séquence est une liste d'événements datés (temps en secondes, action).
Le contrôleur (Pico/Arduino) traduit ces séquences en signaux sur le switch RF
et en fenêtres de comptage APD. Les 4 séquences standard de la magnétométrie NV :

1. **ODMR** (Continuous Wave) : laser + micro-onde en continu, on balaie la
   fréquence micro-onde. Le dip de fluorescence localise la résonance spin.
2. **Rabi** : laser (init) → pulse micro-onde de durée variable τ → laser (lecture).
   La population oscille à la pulsation de Rabi Ω → mesure Ω et t_porte.
3. **Ramsey** : laser → π/2 → attente libre τ → π/2 → lecture. Franges dont la
   décroissance donne T2* (déphasing libre).
4. **Hahn echo** : laser → π/2 → τ → π → τ → π/2 → lecture. L'écho refocalise
   le déphasing statique → décroissance donne T2 (cohérence vraie).

Convention temporelle : le laser initialise le spin dans ms=0 (pompage optique),
et la lecture se fait par la fluorescence pendant le premier ~300 ns du pulse
laser de lecture (le spin ms=0 fluoresce plus que ms=±1).
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Pulse:
    """Un événement de la séquence.

    t_start_s : début (s) ; duration_s : durée (s)
    channel   : 'laser' (pompage/lecture optique) ou 'mw' (micro-onde)
    kind      : pour 'mw', le type de rotation ('pi_half', 'pi', 'cw', 'free')
    """
    t_start_s: float
    duration_s: float
    channel: str
    kind: str = "cw"


@dataclass
class Sequence:
    """Une séquence de mesure = nom + liste de pulses + paramètre balayé."""
    name: str
    pulses: list[Pulse] = field(default_factory=list)
    sweep_param: str = ""        # 'frequency' (ODMR) ou 'tau' (Rabi/Ramsey/Hahn)

    def total_duration_s(self) -> float:
        if not self.pulses:
            return 0.0
        return max(p.t_start_s + p.duration_s for p in self.pulses)


# Durées de référence (sourcées : Doherty 2013, bancs NV standard)
LASER_INIT_S = 3.0e-6        # pompage optique vers ms=0 (~3 µs)
LASER_READ_S = 0.3e-6        # fenêtre de lecture de la fluorescence (~300 ns)
SETTLE_S = 1.0e-6            # temps de repos entre séquences


def odmr_sequence() -> Sequence:
    """ODMR continu : laser et micro-onde simultanés, on balaie la FRÉQUENCE.
    Pas de pulsation temporelle — le paramètre balayé est la fréquence µ-onde."""
    return Sequence(
        name="ODMR",
        pulses=[
            Pulse(0.0, LASER_INIT_S + LASER_READ_S, "laser", "cw"),
            Pulse(0.0, LASER_INIT_S + LASER_READ_S, "mw", "cw"),
        ],
        sweep_param="frequency",
    )


def rabi_sequence(tau_s: float, pi_time_s: float) -> Sequence:
    """Rabi : init → pulse µ-onde de durée τ (balayé) → lecture."""
    seq = Sequence(name="Rabi", sweep_param="tau")
    t = 0.0
    seq.pulses.append(Pulse(t, LASER_INIT_S, "laser", "init")); t += LASER_INIT_S
    seq.pulses.append(Pulse(t, tau_s, "mw", "cw")); t += tau_s   # durée variable
    seq.pulses.append(Pulse(t, LASER_READ_S, "laser", "read")); t += LASER_READ_S
    return seq


def ramsey_sequence(tau_s: float, pi_half_time_s: float) -> Sequence:
    """Ramsey : init → π/2 → évolution libre τ (balayé) → π/2 → lecture.
    Détecte le déphasing libre → T2*."""
    seq = Sequence(name="Ramsey", sweep_param="tau")
    t = 0.0
    seq.pulses.append(Pulse(t, LASER_INIT_S, "laser", "init")); t += LASER_INIT_S
    seq.pulses.append(Pulse(t, pi_half_time_s, "mw", "pi_half")); t += pi_half_time_s
    t += tau_s                                                     # évolution libre
    seq.pulses.append(Pulse(t, pi_half_time_s, "mw", "pi_half")); t += pi_half_time_s
    seq.pulses.append(Pulse(t, LASER_READ_S, "laser", "read")); t += LASER_READ_S
    return seq


def hahn_echo_sequence(tau_s: float, pi_half_time_s: float, pi_time_s: float) -> Sequence:
    """Hahn echo : init → π/2 → τ → π → τ → π/2 → lecture.
    Le pulse π central refocalise le déphasing quasi-statique → T2 (cohérence)."""
    seq = Sequence(name="HahnEcho", sweep_param="tau")
    t = 0.0
    seq.pulses.append(Pulse(t, LASER_INIT_S, "laser", "init")); t += LASER_INIT_S
    seq.pulses.append(Pulse(t, pi_half_time_s, "mw", "pi_half")); t += pi_half_time_s
    t += tau_s
    seq.pulses.append(Pulse(t, pi_time_s, "mw", "pi")); t += pi_time_s
    t += tau_s
    seq.pulses.append(Pulse(t, pi_half_time_s, "mw", "pi_half")); t += pi_half_time_s
    seq.pulses.append(Pulse(t, LASER_READ_S, "laser", "read")); t += LASER_READ_S
    return seq
