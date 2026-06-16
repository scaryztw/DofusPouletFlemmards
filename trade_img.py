"""
Detection PIXEL d'une demande d'echange / d'invitation de groupe.

Principe (valide en test) :
  - PrintWindow capture la fenetre EN ARRIERE-PLAN, mais on ne RECOPIE et ne scanne
    QUE la bande centrale (la ou le dialogue apparait) -> beaucoup moins de CPU.
  - le dialogue du RECEVEUR a DEUX boutons orange vifs cote a cote (Accepter/Oui a
    GAUCHE, Refuser/Non a droite). Le dialogue du LANCEUR n'a qu'UN bouton (Annuler)
    -> on exige 2 boutons pour ne jamais cliquer Annuler.
  - on renvoie les coords CLIENT du bouton gauche (pour PostMessage / background_click).

Seuils PROPORTIONNELS a la taille de la fenetre -> independant de la resolution.
Aucune dependance hors pywin32.
"""
import ctypes

import win32gui
import win32ui
import win32con

PW_RENDERFULLCONTENT = 0x00000002

# Bande centrale capturee/scannee (fractions de la fenetre). Le dialogue est centre
# et ses boutons sont vers ~43 % de hauteur dans nos tests -> bande etroite = peu de CPU.
BAND_X = (0.25, 0.75)
BAND_Y = (0.33, 0.57)

# Seuils proportionnels (UI Dofus Retro scale avec la fenetre)
MIN_LEN_FRAC = 0.045    # largeur mini d'un bouton (fraction de la largeur fenetre)
MAX_LEN_FRAC = 0.18     # largeur maxi
MIN_LEN_ABS = 40        # plancher absolu (tres petites fenetres)
MIN_GAP_FRAC = 0.03     # ecart mini entre les centres des 2 boutons
MAX_DY_FRAC = 0.025     # ecart vertical maxi entre les 2 boutons (memes hauteur)
MAX_WAIT_BTN_FRAC = 0.12  # largeur MAXI du bouton « Annuler » (fraction fenetre). Une ligne
                          # surlignee de menu clic-droit est bien plus large -> on la rejette.


def _capture_band(hwnd):
    """Capture UNIQUEMENT la bande centrale de la fenetre (arriere-plan).
    Retourne (bits_bgrx, bw, bh, bx, by, left, top, W, H) ou None.
    bx/by = coin haut-gauche de la bande en coords fenetre ; left/top = pos ecran."""
    try:
        if win32gui.IsIconic(hwnd):
            return None
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    except Exception:
        return None
    W, H = right - left, bottom - top
    if W <= 0 or H <= 0:
        return None
    bx, by = int(W * BAND_X[0]), int(H * BAND_Y[0])
    bw, bh = int(W * (BAND_X[1] - BAND_X[0])), int(H * (BAND_Y[1] - BAND_Y[0]))
    if bw <= 0 or bh <= 0:
        return None

    hwnd_dc = mfc_dc = full_dc = band_dc = full_bmp = band_bmp = None
    old_full = old_band = None
    bits = None
    try:
        hwnd_dc = win32gui.GetWindowDC(hwnd)
        mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
        # 1) rendu complet (necessaire pour PrintWindow) dans un DC plein
        full_dc = mfc_dc.CreateCompatibleDC()
        full_bmp = win32ui.CreateBitmap()
        full_bmp.CreateCompatibleBitmap(mfc_dc, W, H)
        old_full = full_dc.SelectObject(full_bmp)
        ctypes.windll.user32.PrintWindow(hwnd, full_dc.GetSafeHdc(), PW_RENDERFULLCONTENT)
        # 2) on ne RECOPIE que la bande centrale (petit bitmap) -> peu de donnees
        band_dc = mfc_dc.CreateCompatibleDC()
        band_bmp = win32ui.CreateBitmap()
        band_bmp.CreateCompatibleBitmap(mfc_dc, bw, bh)
        old_band = band_dc.SelectObject(band_bmp)
        band_dc.BitBlt((0, 0), (bw, bh), full_dc, (bx, by), win32con.SRCCOPY)
        bits = band_bmp.GetBitmapBits(True)   # BGRX top-down, taille de la bande seulement
    except Exception:
        bits = None
    finally:
        # deselectionne nos bitmaps AVANT de les supprimer (sinon DeleteObject echoue -> fuite)
        try:
            if full_dc is not None and old_full is not None:
                full_dc.SelectObject(old_full)
        except Exception:
            pass
        try:
            if band_dc is not None and old_band is not None:
                band_dc.SelectObject(old_band)
        except Exception:
            pass
        for obj in (full_bmp, band_bmp):
            try:
                if obj is not None:
                    win32gui.DeleteObject(obj.GetHandle())
            except Exception:
                pass
        for dc in (full_dc, band_dc):
            try:
                if dc is not None:
                    dc.DeleteDC()
            except Exception:
                pass
        try:
            if mfc_dc is not None:
                mfc_dc.DeleteDC()
        except Exception:
            pass
        try:
            if hwnd_dc is not None:
                win32gui.ReleaseDC(hwnd, hwnd_dc)
        except Exception:
            pass
    if not bits:
        return None
    return bits, bw, bh, bx, by, left, top, W, H


def _is_orange(r, g, b):
    """Orange VIF du bouton (#FD6000-ish). Le brun-terre du decor (#9D7F28) est exclu."""
    return (r > 195 and 60 < g < 185 and b < 85
            and (r - g) > 45 and (g - b) > 25)


def _orange_runs(bits, bw, bh, full_w, gap_tol=3, y_step=2):
    """Lignes horizontales continues de orange vif dans la bande (coords bande-locales)."""
    min_len = max(MIN_LEN_ABS, int(full_w * MIN_LEN_FRAC))
    max_len = int(full_w * MAX_LEN_FRAC)
    runs = []
    for y in range(0, bh, y_step):
        base = y * bw
        cur = last = None
        gap = 0
        for x in range(0, bw):
            off = (base + x) * 4
            b = bits[off]; g = bits[off + 1]; r = bits[off + 2]
            if _is_orange(r, g, b):
                if cur is None:
                    cur = x
                last = x
                gap = 0
            else:
                if cur is not None:
                    gap += 1
                    if gap > gap_tol:
                        runs.append((last - cur + 1, y, cur, last))
                        cur = None
                        gap = 0
        if cur is not None:
            runs.append((last - cur + 1, y, cur, last))
    return [r for r in runs if min_len <= r[0] <= max_len]


def _cluster(runs, min_rows=5):
    """Regroupe les lignes qui se chevauchent en X -> 1 cluster = 1 bouton."""
    buttons = []
    for (ln, y, x0, x1) in sorted(runs, key=lambda r: r[2]):
        placed = False
        for btn in buttons:
            if not (x1 < btn["x0"] - 12 or x0 > btn["x1"] + 12):
                btn["x0"] = min(btn["x0"], x0)
                btn["x1"] = max(btn["x1"], x1)
                btn["ys"].append(y)
                placed = True
                break
        if not placed:
            buttons.append({"x0": x0, "x1": x1, "ys": [y]})
    buttons = [b for b in buttons if len(b["ys"]) >= min_rows]
    for b in buttons:
        b["cx"] = (b["x0"] + b["x1"]) // 2
        ys = sorted(b["ys"])
        b["cy"] = ys[len(ys) // 2]
    buttons.sort(key=lambda b: b["cx"])
    return buttons


def detect_accept(hwnd):
    """Si la fenetre affiche un dialogue a 2 boutons (echange/invite), renvoie les
    coords CLIENT (x, y) du bouton GAUCHE (Accepter/Oui). Sinon None."""
    cap = _capture_band(hwnd)
    if not cap:
        return None
    bits, bw, bh, bx, by, left, top, W, H = cap
    buttons = _cluster(_orange_runs(bits, bw, bh, W))
    if len(buttons) < 2:
        return None
    a, bb = buttons[0], buttons[1]          # les deux plus a gauche
    if abs(a["cy"] - bb["cy"]) > int(H * MAX_DY_FRAC):   # memes hauteur ?
        return None
    if (bb["cx"] - a["cx"]) < int(W * MIN_GAP_FRAC):     # ecart franc ?
        return None
    # bande-local -> fenetre -> ecran -> client
    wx, wy = bx + a["cx"], by + a["cy"]
    sx, sy = left + wx, top + wy
    try:
        cx, cy = win32gui.ScreenToClient(hwnd, (sx, sy))
    except Exception:
        return None
    return (cx, cy)


def detect_waiting(hwnd):
    """True si la fenetre affiche le dialogue REQUESTEUR « En attente de la reponse
    de X » : UN seul bouton orange (Annuler), a peu pres centre. C'est la PREUVE qu'un
    de tes persos a lance une demande -> l'echange/invite en cours est INTERNE."""
    cap = _capture_band(hwnd)
    if not cap:
        return False
    bits, bw, bh, bx, by, left, top, W, H = cap
    buttons = _cluster(_orange_runs(bits, bw, bh, W))
    if len(buttons) != 1:
        return False
    b = buttons[0]
    if (b["x1"] - b["x0"]) > int(W * MAX_WAIT_BTN_FRAC):   # trop large = ligne de menu, pas « Annuler »
        return False
    cx_frac = (bx + b["cx"]) / float(W)        # centre horizontal du bouton (fraction fenetre)
    return 0.33 < cx_frac < 0.67
