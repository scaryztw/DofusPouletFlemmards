"""
Helpers Win32 — equivalents directs de ce que faisait l'AHK.

- dofus_windows()      : détecte les fenêtres Dofus (EnumWindows + nom du process)
- activate(hwnd)       : met une fenêtre au premier plan (contourne SetForegroundWindow)
- background_click()   : clic en arrière-plan (PostMessage) == ControlClick d'AHK
- reorder_taskbar()    : reordonne les boutons de la barre des taches (AppUserModelID)
"""
import ctypes
import os
import time
import threading
from ctypes import wintypes

import win32gui
import win32con
import win32process

try:
    import psutil
except Exception:
    psutil = None

WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
WM_MOUSEMOVE = 0x0200
MK_LBUTTON = 0x0001

user32 = ctypes.windll.user32
shell32 = ctypes.windll.shell32
kernel32 = ctypes.windll.kernel32
_OWN_PID = os.getpid()
_EXE_CACHE = {}          # pid -> nom d'exe (l'exe d'un pid ne change pas)

# Desactive le délai de verrou de premier plan (aide SetForegroundWindow a reussir)
try:
    user32.SystemParametersInfoW(0x2001, 0, 0, 0)  # SPI_SETFOREGROUNDLOCKTIMEOUT = 0
except Exception:
    pass


def _lparam(x, y):
    return (y << 16) | (x & 0xFFFF)


# --------------------------------------------------------------------------
#  Détection des fenêtres Dofus
# --------------------------------------------------------------------------
def dofus_windows():
    """Liste [{hwnd, title, pid, exe}] des fenêtres Dofus visibles."""
    out = []

    def cb(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return True
        title = win32gui.GetWindowText(hwnd)
        if not title:
            return True
        exe, pid = "", 0
        try:
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            # cache pid -> exe : l'exe d'un pid ne change jamais, inutile de relancer
            # psutil pour CHAQUE fenetre a CHAQUE enumeration (gros gain CPU).
            if pid in _EXE_CACHE:
                exe = _EXE_CACHE[pid]
            elif psutil is not None:
                try:
                    exe = psutil.Process(pid).name()
                except Exception:
                    exe = ""
                _EXE_CACHE[pid] = exe
        except Exception:
            pass
        if pid == _OWN_PID:          # jamais notre propre fenêtre (l'appli)
            return True
        is_dofus = exe.lower().startswith("dofus")
        if not is_dofus and not exe and "dofus retro" in title.lower():
            is_dofus = True          # secours si l'exe est inaccessible
        if is_dofus:
            out.append({"hwnd": hwnd, "title": title, "pid": pid, "exe": exe or "?"})
        return True

    win32gui.EnumWindows(cb, None)
    # purge legere : si le cache enfle (pids recycles), on le borne
    if len(_EXE_CACHE) > 256:
        _EXE_CACHE.clear()
    return out


def window_alive(hwnd):
    try:
        return bool(win32gui.IsWindow(hwnd))
    except Exception:
        return False


# --------------------------------------------------------------------------
#  Activation (premier plan)
# --------------------------------------------------------------------------
def disable_foreground_lock():
    """Desactive le VERROU DE PREMIER PLAN de Windows (SPI_SETFOREGROUNDLOCKTIMEOUT=0).
    Sans ca, Windows refuse SetForegroundWindow quand l'appel ne vient pas de l'appli
    active -> la fenetre clignote dans la barre des taches au lieu de passer devant
    (le fameux "1 switch sur 2"). A appeler une fois au demarrage."""
    try:
        SPI_SETFOREGROUNDLOCKTIMEOUT = 0x2001
        SPIF_SENDCHANGE = 0x0002
        user32.SystemParametersInfoW(SPI_SETFOREGROUNDLOCKTIMEOUT, 0, 0, SPIF_SENDCHANGE)
    except Exception:
        pass


def activate(hwnd):
    """Premier plan. Le verrou de premier plan étant désactivé au démarrage
    (disable_foreground_lock), un simple SetForegroundWindow suffit dans le cas
    normal — PAS de ruse ALT ni d'AttachThreadInput ici (c'est ce qui provoquait
    le curseur « chargement » et des à-coups au switch). Repli musclé seulement
    si la fenêtre refuse vraiment de passer devant."""
    try:
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    except Exception:
        pass
    try:
        win32gui.SetForegroundWindow(hwnd)
    except Exception:
        pass
    # vérifie ; si déjà devant, terminé (cas normal, sans aucune gymnastique)
    try:
        if win32gui.GetForegroundWindow() == hwnd:
            return
    except Exception:
        return
    _activate_forceful(hwnd)   # repli (AttachThreadInput + ALT) uniquement si échec réel


def _activate_forceful(hwnd):
    """Repli : attache le thread d'entree du premier plan puis force le focus."""
    cur = kernel32.GetCurrentThreadId()
    fg_thread = 0
    try:
        fg = win32gui.GetForegroundWindow()
        fg_thread = win32process.GetWindowThreadProcessId(fg)[0] if fg else 0
    except Exception:
        fg_thread = 0
    attached = False
    try:
        if fg_thread and fg_thread != cur:
            attached = bool(user32.AttachThreadInput(fg_thread, cur, True))
        try:
            win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
            win32gui.BringWindowToTop(hwnd)
            win32gui.SetForegroundWindow(hwnd)
        except Exception:
            try:
                user32.SetForegroundWindow(hwnd)
            except Exception:
                pass
    finally:
        if attached:
            try:
                user32.AttachThreadInput(fg_thread, cur, False)
            except Exception:
                pass


def maximize(hwnd):
    """Agrandit une fenêtre (au lancement)."""
    try:
        win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
    except Exception:
        pass


def minimize(hwnd):
    """Réduit une fenêtre dans la barre des tâches."""
    try:
        win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
    except Exception:
        pass


def restore(hwnd):
    """Restaure une fenêtre réduite."""
    try:
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    except Exception:
        pass


def get_foreground_lock_timeout():
    """Lit le délai du verrou de premier plan (SPI_GETFOREGROUNDLOCKTIMEOUT).
    0 = verrou désactivé (état voulu pour un switch combat fiable)."""
    try:
        val = ctypes.c_uint(0)
        SPI_GETFOREGROUNDLOCKTIMEOUT = 0x2000
        user32.SystemParametersInfoW(SPI_GETFOREGROUNDLOCKTIMEOUT, 0, ctypes.byref(val), 0)
        return int(val.value)
    except Exception:
        return None


# --------------------------------------------------------------------------
#  Clic en arrière-plan (coordonnees CLIENT) == ControlClick d'AHK
# --------------------------------------------------------------------------
def background_click(hwnd, x, y, clicks=1):
    """Clic en arrière-plan (la fenêtre n'a pas besoin d'être au premier plan).
    Fiabilisé : on positionne d'abord le curseur (WM_MOUSEMOVE), puis on MAINTIENT
    brièvement le bouton enfoncé (sinon Dofus ne reconnaît pas toujours le clic ->
    fenêtres qui « ratent »). clicks=2 -> double-clic."""
    import time as _t
    lp = _lparam(x, y)
    try:
        # hover : certains éléments d'UI n'arment le clic qu'après un survol
        win32gui.PostMessage(hwnd, WM_MOUSEMOVE, 0, lp)
        for i in range(max(1, int(clicks))):
            win32gui.PostMessage(hwnd, WM_LBUTTONDOWN, MK_LBUTTON, lp)
            _t.sleep(0.03)                 # maintien -> clic fiablement reconnu
            win32gui.PostMessage(hwnd, WM_LBUTTONUP, 0, lp)
            if i + 1 < clicks:
                _t.sleep(0.05)             # écart entre les 2 clics (double-clic)
    except Exception:
        pass


# --------------------------------------------------------------------------
#  Reorder de la barre des taches  (port de Dracoon : ungroup -> Z-order -> regroup)
# --------------------------------------------------------------------------
class _GUID(ctypes.Structure):
    _fields_ = [("Data1", ctypes.c_uint32), ("Data2", ctypes.c_uint16),
                ("Data3", ctypes.c_uint16), ("Data4", ctypes.c_ubyte * 8)]


class _PROPERTYKEY(ctypes.Structure):
    _fields_ = [("fmtid", _GUID), ("pid", ctypes.c_ulong)]


class _PROPVARIANT(ctypes.Structure):
    _fields_ = [("vt", ctypes.c_ushort), ("r1", ctypes.c_ushort),
                ("r2", ctypes.c_ushort), ("r3", ctypes.c_ushort),
                ("p", ctypes.c_void_p)]


_IID_PS = _GUID(0x886D8EEB, 0x8CF2, 0x4446,
                (ctypes.c_ubyte * 8)(0x8D, 0x02, 0xCD, 0xBA, 0x1D, 0xBD, 0xCF, 0x99))
_PKEY_AUMI = _PROPERTYKEY(
    _GUID(0x9F4C2855, 0x9F79, 0x4B39,
          (ctypes.c_ubyte * 8)(0xA8, 0xD0, 0xE1, 0xD4, 0x2D, 0xE1, 0xD5, 0xF3)), 5)


def set_window_app_id(hwnd, app_id):
    """Affecte (ou efface) l'AppUserModelID d'une fenêtre."""
    try:
        pstore = ctypes.c_void_p()
        hr = shell32.SHGetPropertyStoreForWindow(
            wintypes.HWND(hwnd), ctypes.byref(_IID_PS), ctypes.byref(pstore))
        if hr != 0 or not pstore.value:
            return False
        vtbl = ctypes.cast(pstore, ctypes.POINTER(ctypes.c_void_p))[0]
        funcs = ctypes.cast(vtbl, ctypes.POINTER(ctypes.c_void_p))
        proto_sv = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p,
                                      ctypes.c_void_p, ctypes.c_void_p)
        proto_c = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p)
        SetValue = proto_sv(funcs[6])
        Commit = proto_c(funcs[7])
        Release = proto_c(funcs[2])
        pv = _PROPVARIANT()
        buf = None
        if app_id:
            buf = ctypes.create_unicode_buffer(app_id)
            pv.vt = 31  # VT_LPWSTR
            pv.p = ctypes.cast(buf, ctypes.c_void_p)
        else:
            pv.vt = 0   # VT_EMPTY
        hr = SetValue(pstore, ctypes.byref(_PKEY_AUMI), ctypes.byref(pv))
        if hr == 0:
            Commit(pstore)
        Release(pstore)
        return hr == 0
    except Exception as e:
        print("[set_window_app_id] :", e)
        return False


def _reorder_taskbar_blocking(hwnds, focus_hwnd=0):
    if len(hwnds) < 2:
        if focus_hwnd:
            try:
                activate(focus_hwnd)
            except Exception:
                pass
        return
    for h in hwnds:
        set_window_app_id(h, "DofusRetro.Char.%d" % h)
    time.sleep(0.3)
    swp = 0x0010 | 0x0002 | 0x0001  # NOACTIVATE | NOMOVE | NOSIZE
    for i in range(len(hwnds) - 1):
        try:
            user32.SetWindowPos(hwnds[i], hwnds[i + 1], 0, 0, 0, 0, swp)
        except Exception:
            pass
        time.sleep(0.05)
    time.sleep(0.2)
    for h in hwnds:
        set_window_app_id(h, "DofusRetro.SharedGroup")
    if focus_hwnd:
        # la réorganisation du Z-order a fait passer une autre fenêtre devant
        # -> on remet au premier plan celle sur laquelle l'utilisateur était.
        try:
            activate(focus_hwnd)
        except Exception:
            pass


def reorder_taskbar(hwnds, focus_hwnd=0):
    """Reordonne les boutons de la taskbar dans l'ordre de hwnds (non bloquant).
    focus_hwnd : fenêtre à remettre au premier plan une fois la réorganisation finie."""
    threading.Thread(target=_reorder_taskbar_blocking, args=(list(hwnds), focus_hwnd), daemon=True).start()


def foreground():
    """hwnd de la fenêtre actuellement au premier plan (0 si indéterminé)."""
    try:
        return win32gui.GetForegroundWindow()
    except Exception:
        return 0
