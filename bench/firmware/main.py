"""Firmware de pulsation NV — MicroPython pour Raspberry Pi Pico / RP2040.

Génère les séquences de pulses micro-onde (ODMR, Rabi, Ramsey, Hahn echo) avec
un timing à la microseconde, et synchronise la fenêtre de comptage de l'APD.

Branchements (RP2040) :
  - GP0 : trigger laser (pompage / lecture optique)
  - GP1 : switch micro-onde (RF switch, ouvre/ferme la µ-onde vers l'antenne)
  - GP2 : gate APD (fenêtre de comptage — ouvre le compteur de photons)
  - GP15 : retour des impulsions APD (TTL) si comptage embarqué (extension)

Le RP2040 tourne à 125 MHz → résolution temporelle native ~8 ns, largement
suffisant pour des pulses de ~µs. Pour du sub-µs strict, on utiliserait le PIO
du RP2040 (machine d'état dédiée) — laissé en extension.

Ce firmware est la contrepartie NV du firmware ESP32 de ratiss-grid : on valide
la logique ici, on flashe, et le banc physique n'a qu'à suivre.
"""

from machine import Pin
import time

# --- Broches ---
PIN_LASER = 0      # trigger laser (pompage + lecture)
PIN_MW = 1         # switch micro-onde
PIN_APD_GATE = 2   # fenêtre de comptage APD

# --- Durées de référence (microsecondes) ---
LASER_INIT_US = 3000      # pompage optique vers ms=0
LASER_READ_US = 300       # fenêtre de lecture fluorescence
SETTLE_US = 1000          # repos entre répétitions


class PulseSequencer:
    """Génère les séquences de pulses NV sur GPIO avec timing µs.

    Usage :
        seq = PulseSequencer()
        seq.odmr_cw()                 # ODMR continu (laser + µ-onde ensemble)
        seq.rabi(tau_us=5)            # pulse µ-onde de durée variable
        seq.ramsey(tau_us=2)          # π/2 — τ — π/2
        seq.hahn_echo(tau_us=10)      # π/2 — τ — π — τ — π/2
    """

    def __init__(self, pi_time_us=1, pi_half_us=0.5):
        self.laser = Pin(PIN_LASER, Pin.OUT, value=0)
        self.mw = Pin(PIN_MW, Pin.OUT, value=0)
        self.apd_gate = Pin(PIN_APD_GATE, Pin.OUT, value=0)
        self.pi_time_us = pi_time_us        # durée d'un pulse π (µs) — à calibrer (Rabi)
        self.pi_half_us = pi_half_us        # durée d'un pulse π/2

    # --- primitives ---
    def _laser_on_us(self, us):
        self.laser.value(1)
        time.sleep_us(int(us))
        self.laser.value(0)

    def _mw_on_us(self, us):
        self.mw.value(1)
        time.sleep_us(int(us))
        self.mw.value(0)

    def _init_spin(self):
        """Pompage optique : initialise le spin dans ms=0."""
        self._laser_on_us(LASER_INIT_US)

    def _read(self):
        """Lecture : ouvre la fenêtre APD pendant le pulse laser de lecture.
        La fluorescence dans cette fenêtre encode l'état de spin."""
        self.laser.value(1)
        self.apd_gate.value(1)          # ouvre le comptage photons
        time.sleep_us(int(LASER_READ_US))
        self.apd_gate.value(0)          # ferme la fenêtre
        self.laser.value(0)

    def _settle(self):
        time.sleep_us(int(SETTLE_US))

    # --- séquences ---
    def odmr_cw(self, duration_us=10000):
        """ODMR continu : laser + micro-onde ensemble, on compte la fluorescence.
        On balaie la FRÉQUENCE µ-onde côté synthétiseur (pas ici)."""
        self.laser.value(1)
        self.mw.value(1)
        self.apd_gate.value(1)
        time.sleep_us(int(duration_us))
        self.apd_gate.value(0)
        self.mw.value(0)
        self.laser.value(0)

    def rabi(self, tau_us):
        """Rabi : init → pulse µ-onde de durée tau (balayé) → lecture."""
        self._init_spin()
        self._mw_on_us(tau_us)
        self._read()
        self._settle()

    def ramsey(self, tau_us):
        """Ramsey : init → π/2 → attente libre tau → π/2 → lecture. Mesure T2*."""
        self._init_spin()
        self._mw_on_us(self.pi_half_us)     # premier π/2
        time.sleep_us(int(tau_us))          # évolution libre
        self._mw_on_us(self.pi_half_us)     # second π/2
        self._read()
        self._settle()

    def hahn_echo(self, tau_us):
        """Hahn echo : init → π/2 → tau → π → tau → π/2 → lecture. Mesure T2."""
        self._init_spin()
        self._mw_on_us(self.pi_half_us)     # π/2
        time.sleep_us(int(tau_us))
        self._mw_on_us(self.pi_time_us)     # π (refocalisation)
        time.sleep_us(int(tau_us))
        self._mw_on_us(self.pi_half_us)     # π/2
        self._read()
        self._settle()

    def all_off(self):
        """Sécurité : tout à zéro."""
        self.laser.value(0)
        self.mw.value(0)
        self.apd_gate.value(0)


# --- Point d'entrée ---
if __name__ == "__main__":
    seq = PulseSequencer(pi_time_us=1, pi_half_us=0.5)
    print("Firmware pulsation NV prêt. Séquences : odmr_cw, rabi, ramsey, hahn_echo")
    # Exemple : balayage Rabi (à piloter depuis l'ordinateur via REPL/USB)
    # for tau_us in range(0, 20):
    #     seq.rabi(tau_us)
    seq.all_off()
