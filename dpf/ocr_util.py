"""
Lecture de texte via l'OCR Windows (winsdk/winrt), IN-PROCESS.
Sert a verifier que l'EMETTEUR d'un echange / d'une invitation est bien un de tes
persos : on OCR la zone de texte du dialogue ("X vous propose un echange") et on
cherche un de tes pseudos dedans.

100 % defensif : toute erreur -> read_text renvoie None, et l'appelant decide de ne
PAS casser l'auto-accept dans ce cas.
"""
import asyncio
import ctypes

import win32gui
import win32ui
import win32con

PW_RENDERFULLCONTENT = 0x00000002

_OK = False
try:                                   # winsdk = monolithique (comme le notifier)
    import winsdk.windows.media.ocr as _ocr
    import winsdk.windows.globalization as _glob
    import winsdk.windows.graphics.imaging as _imaging
    import winsdk.windows.storage.streams as _streams
    _OK = True
except Exception:
    try:                               # repli winrt modulaire
        import winrt.windows.media.ocr as _ocr
        import winrt.windows.globalization as _glob
        import winrt.windows.graphics.imaging as _imaging
        import winrt.windows.storage.streams as _streams
        _OK = True
    except Exception:
        _OK = False

_engine = None
_engine_tried = False


def _get_engine():
    global _engine, _engine_tried
    if _engine_tried:
        return _engine
    _engine_tried = True
    if not _OK:
        return None
    try:
        eng = None
        try:
            eng = _ocr.OcrEngine.try_create_from_language(_glob.Language("fr"))
        except Exception:
            eng = None
        if eng is None:
            eng = _ocr.OcrEngine.try_create_from_user_profile_languages()
        _engine = eng
    except Exception:
        _engine = None
    return _engine


def available():
    return _get_engine() is not None


def _capture_region(hwnd, fx0, fy0, fx1, fy1):
    """Capture une region (fractions de la fenetre) en arriere-plan -> (bits BGRA, w, h)."""
    try:
        if win32gui.IsIconic(hwnd):
            return None
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    except Exception:
        return None
    W, H = right - left, bottom - top
    if W <= 0 or H <= 0:
        return None
    rx, ry = int(W * fx0), int(H * fy0)
    rw, rh = int(W * (fx1 - fx0)), int(H * (fy1 - fy0))
    if rw <= 0 or rh <= 0:
        return None
    hwnd_dc = mfc_dc = full_dc = reg_dc = full_bmp = reg_bmp = None
    bits = None
    try:
        hwnd_dc = win32gui.GetWindowDC(hwnd)
        mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
        full_dc = mfc_dc.CreateCompatibleDC()
        full_bmp = win32ui.CreateBitmap()
        full_bmp.CreateCompatibleBitmap(mfc_dc, W, H)
        full_dc.SelectObject(full_bmp)
        ctypes.windll.user32.PrintWindow(hwnd, full_dc.GetSafeHdc(), PW_RENDERFULLCONTENT)
        reg_dc = mfc_dc.CreateCompatibleDC()
        reg_bmp = win32ui.CreateBitmap()
        reg_bmp.CreateCompatibleBitmap(mfc_dc, rw, rh)
        reg_dc.SelectObject(reg_bmp)
        reg_dc.BitBlt((0, 0), (rw, rh), full_dc, (rx, ry), win32con.SRCCOPY)
        bits = reg_bmp.GetBitmapBits(True)
    except Exception:
        bits = None
    finally:
        for obj in (full_bmp, reg_bmp):
            try:
                if obj is not None:
                    win32gui.DeleteObject(obj.GetHandle())
            except Exception:
                pass
        for dc in (full_dc, reg_dc):
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
    return bits, rw, rh


async def _recognize(bits, w, h):
    writer = _streams.DataWriter()
    writer.write_bytes(bits)
    buf = writer.detach_buffer()
    bmp = _imaging.SoftwareBitmap.create_copy_from_buffer(
        buf, _imaging.BitmapPixelFormat.BGRA8, w, h)
    res = await _engine.recognize_async(bmp)
    try:
        return res.text or ""
    except Exception:
        return ""


def read_text(hwnd, fx0=0.12, fy0=0.20, fx1=0.88, fy1=0.46):
    """OCR de la zone de texte du dialogue. Renvoie le texte lu, ou None si echec/indispo."""
    if _get_engine() is None:
        return None
    cap = _capture_region(hwnd, fx0, fy0, fx1, fy1)
    if not cap:
        return None
    bits, w, h = cap
    try:
        return asyncio.run(_recognize(bits, w, h))
    except Exception:
        return None
