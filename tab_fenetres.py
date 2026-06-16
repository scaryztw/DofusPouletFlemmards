"""AutoTrade par image — version CPU-légère (calquée sur l'AutoTrade du script AHK d'origine).

Principe (≈ 0 % CPU au repos) :
- On lit UNIQUEMENT une petite zone de l'écran visible (grabWindow), JAMAIS PrintWindow
  par fenêtre (c'est PrintWindow qui faisait grimper le CPU).
- Un "gate" ultra-léger lit une mini-zone à la position du bouton Accepter : tant qu'il
  n'a pas la couleur du bouton (= pas de pop-up d'échange), on s'arrête là (quasi gratuit).
- Le match image (numpy) ne tourne QUE quand une pop-up est effectivement détectée.

Aucune dépendance à win32 ici : capture via Qt (QScreen.grabWindow), PNG via QImage.
numpy est requis pour le match (ajouté à requirements.txt).
"""

import os

try:
    import numpy as np
except Exception:
    np = None

from PySide6.QtGui import QImage, QGuiApplication


def available():
    return np is not None


def _screen():
    try:
        return QGuiApplication.primaryScreen()
    except Exception:
        return None


def _qimage_to_array(img):
    """QImage -> numpy (h, w, 3) uint8, ou None."""
    if np is None or img is None or img.isNull():
        return None
    img = img.convertToFormat(QImage.Format_RGB888)
    w, h = img.width(), img.height()
    if w < 1 or h < 1:
        return None
    bpl = img.bytesPerLine()
    ptr = img.constBits()
    try:
        buf = bytes(ptr)
    except Exception:
        try:
            ptr.setsize(bpl * h)
            buf = bytes(ptr)
        except Exception:
            return None
    arr = np.frombuffer(buf, dtype=np.uint8)
    if arr.size < bpl * h:
        return None
    arr = arr[:bpl * h].reshape((h, bpl))
    return np.ascontiguousarray(arr[:, :w * 3].reshape((h, w, 3)))


def grab_region(x1, y1, x2, y2):
    """numpy (h, w, 3) d'une zone de l'écran (pixels visibles), ou None."""
    scr = _screen()
    if scr is None:
        return None
    x = int(min(x1, x2)); y = int(min(y1, y2))
    w = int(abs(x2 - x1)); h = int(abs(y2 - y1))
    if w < 2 or h < 2:
        return None
    try:
        pm = scr.grabWindow(0, x, y, w, h)
    except Exception:
        return None
    if pm.isNull():
        return None
    return _qimage_to_array(pm.toImage())


def gate_color(accept_x, accept_y, box=14):
    """Couleur moyenne (r, g, b) d'une mini-zone autour du bouton Accepter, ou None.
    Très léger : c'est le filtre qui évite tout match quand il n'y a pas d'échange."""
    half = max(2, box // 2)
    arr = grab_region(accept_x - half, accept_y - half, accept_x + half, accept_y + half)
    if arr is None:
        return None
    m = arr.reshape(-1, 3).mean(axis=0)
    return (float(m[0]), float(m[1]), float(m[2]))


def color_matches(rgb, target, tol=55):
    if not rgb or not target:
        return False
    return (abs(rgb[0] - target[0]) <= tol and
            abs(rgb[1] - target[1]) <= tol and
            abs(rgb[2] - target[2]) <= tol)


def load_template(path):
    """Charge un PNG (le <pseudo>.png) en array (h, w, 3), ou None."""
    if np is None or not path or not os.path.exists(path):
        return None
    try:
        return _qimage_to_array(QImage(path))
    except Exception:
        return None


_DS = 3   # downscale (moyennage) pour le match : ~13ms/template au lieu de ~1.7s, et tolère les décalages


def _avg_down(a, s):
    """Réduction par MOYENNAGE de blocs s x s (robuste aux décalages de 1-2 px,
    contrairement à un sous-échantillonnage par pas)."""
    if s <= 1:
        return a.astype(np.int16)
    h, w = a.shape[:2]
    h2, w2 = (h // s) * s, (w // s) * s
    if h2 < s or w2 < s:
        return a.astype(np.int16)
    a = a[:h2, :w2].astype(np.float32)
    return a.reshape(h2 // s, s, w2 // s, s, 3).mean(axis=(1, 3)).astype(np.int16)


def _factor(region, template):
    th, tw = template.shape[:2]
    rh, rw = region.shape[:2]
    s = _DS
    while s > 1 and (min(th, tw) // s < 8 or min(rh, rw) // s < 8):
        s -= 1
    return s


def match_score(region, template):
    """Meilleur score (0 = identique, ~22+ = autre pseudo). Downscalé pour la vitesse.
    None si impossible."""
    if np is None or region is None or template is None:
        return None
    s = _factor(region, template)
    r = _avg_down(region, s)
    t = _avg_down(template, s)
    rh, rw = r.shape[:2]
    th, tw = t.shape[:2]
    if th < 2 or tw < 2 or th > rh or tw > rw:
        return None
    try:
        from numpy.lib.stride_tricks import sliding_window_view
        best = 255.0
        for oy in range(0, rh - th + 1):
            band = r[oy:oy + th]
            win = sliding_window_view(band, (th, tw, 3))[0, :, 0]
            m = float(np.abs(win - t).mean(axis=(1, 2, 3)).min())
            if m < best:
                best = m
        return best
    except Exception:
        return None


def find_template(region, template, tol=20):
    """True si le template correspond (sous le seuil)."""
    sc = match_score(region, template)
    return sc is not None and sc <= tol
