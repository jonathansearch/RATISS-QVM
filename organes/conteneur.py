"""Organe CONTENEUR : fond (vide structuré) + mesure P_sig. R7: graines fixées."""
import numpy as np
from ripser import ripser


def fond(n_tore=160, n_sphere=90, seed=24):
    """Fond commun : tore (cycles H1) + petite sphère décalée (cycle H2)."""
    rng = np.random.default_rng(seed)
    u = rng.uniform(0, 2 * np.pi, n_tore)
    v = rng.uniform(0, 2 * np.pi, n_tore)
    R, r = 1.0, 0.32
    tore = np.column_stack([(R + r * np.cos(v)) * np.cos(u),
                            (R + r * np.cos(v)) * np.sin(u),
                            r * np.sin(v)])
    phi = rng.uniform(0, 2 * np.pi, n_sphere)
    c = rng.uniform(-1, 1, n_sphere)
    s = np.sqrt(1 - c * c)
    sph = np.column_stack([0.45 * s * np.cos(phi) + 2.6,
                           0.45 * s * np.sin(phi), 0.45 * c])
    return np.vstack([tore, sph])


def p_sig(points, seuil=0.05):
    """Persistance totale H1+H2 au-dessus du seuil de bruit."""
    dgms = ripser(points, maxdim=2)["dgms"]
    tot = 0.0
    for d in (1, 2):
        if d < len(dgms):
            for naissance, mort in dgms[d]:
                if np.isfinite(mort) and (mort - naissance) > seuil:
                    tot += mort - naissance
    return float(tot)


def boucle_focale(point_focal, rayon=0.25, n=10):
    """Petite boucle stable = la structure qui APPARAÎT à la focalisation."""
    a = np.linspace(0, 2 * np.pi, n, endpoint=False)
    pf = np.array(point_focal, float)
    return np.column_stack([pf[0] + rayon * np.cos(a),
                            pf[1] + rayon * np.sin(a),
                            np.full(n, pf[2])])
