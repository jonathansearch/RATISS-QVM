"""Banc de mesure NV — pilotage, séquences de pulses, acquisition, analyse.

Ce package fait le lien entre le simulateur quantique (ratiss_qpu) et le banc
physique. Il contient :
- `pulse_sequences.py` : les 4 séquences de mesure standard (ODMR, Rabi, Ramsey,
  Hahn echo) définies comme listes de pulses datés.
- `virtual_bench.py` : un banc SIMULÉ qui produit des données réalistes (bruit
  de comptage de photons + physique du NV) pour valider la chaîne de mesure
  AVANT d'acheter le moindre composant. C'est le "hardware virtuel" RATISS.
- `odmr_analysis.py` : ajustement des données ODMR réelles → extraction de la
  résonance → recalibrage automatique du DecoherenceModel.

Doctrine : on valide le logiciel sur le banc virtuel d'abord. Quand le vrai
matériel arrive, seule la source des données change (APD réel vs simulé) — le
code d'analyse est identique. C'est la même méthode que le firmware de
ratiss-grid validé en simulation avant flash.
"""
