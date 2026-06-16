"""
Application principale DPF (PySide6).

Onglets : Fenêtres · Échange · Focus · Système.
Câblage : rotation (raccourcis), autofocus combat/échange (notifications),
échange (popup auto + validation auto par miroir de clic ou touche), overlay.
"""
import time
import threading
import re

import ctypes
import win32api
import win32gui
import win32process

try:
    import keyboard
except Exception:
    keyboard = None

from PySide6.QtCore import Qt, QTimer, Signal, QRect, QPoint
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QPen, QGuiApplication
from PySide6.QtWidgets import (
    QApplication, QWidget, QTabWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QListWidget, QListWidgetItem, QLineEdit, QCheckBox,
    QInputDialog, QScrollArea, QComboBox, QPlainTextEdit, QDialog, QFrame, QLayout,
    QAbstractItemView, QMenu, QSlider,
)

from . import config
from . import win32util
from .notifier import Notifier
from .inputs import Inputs

ACCENT = "#7C6CF6"       # accent moderne (indigo-violet), commun aux 2 thèmes
ACCENT_HI = "#8E80F8"    # survol de l'accent
BLUE = "#4F8EF7"         # AutoFocus (overlay) ; statut
GREEN = "#8DC63F"        # vert du logo (accents discrets)
RED = "#E0585C"          # combat / alertes (overlay)
import os
ICON_PATH = os.path.join(config.RES_DIR, "dpf-icone.ico")
BANNER_LIGHT = os.path.join(config.RES_DIR, "dpf-banner-light.png")
BANNER_DARK = os.path.join(config.RES_DIR, "dpf-banner-dark.png")


def _tray_log(msg):
    try:
        with open(os.path.join(config.APP_DIR, "dpf_tray_log.txt"), "a", encoding="utf-8") as f:
            f.write(str(msg) + "\n")
    except Exception:
        pass

THEMES = {
    "dark": {
        "bg1": "#121218", "bg2": "#0B0B10", "pane": "rgba(22,22,29,0.55)",
        "surface": "#16161D", "card": "#17171F", "card_bd": "#262630",
        "input": "#0F0F14", "bd": "#26262F", "bd_hi": "#34343F",
        "text": "#ECECF1", "muted": "#9A9AA8", "dim": "#C4C4CE",
        "hover": "rgba(255,255,255,0.05)", "sel": "rgba(124,108,246,0.22)",
        "tabtxt": "#8A8A98", "sb": "#2C2C36", "sb_hi": "#3A3A46",
        "btn": "#1A1A22", "btn_hi": "#23232D", "inforow": "#0E0E13", "tip": "#1A1A22",
    },
    "light": {
        "bg1": "#F7F7FA", "bg2": "#EEEEF3", "pane": "rgba(255,255,255,0.70)",
        "surface": "#FFFFFF", "card": "#FFFFFF", "card_bd": "#E6E6EC",
        "input": "#FFFFFF", "bd": "#E3E3EA", "bd_hi": "#CFCFD9",
        "text": "#1B1B22", "muted": "#6E6E7C", "dim": "#43434E",
        "hover": "rgba(0,0,0,0.04)", "sel": "rgba(124,108,246,0.16)",
        "tabtxt": "#6E6E7C", "sb": "#D5D5DE", "sb_hi": "#C0C0CC",
        "btn": "#FFFFFF", "btn_hi": "#F1F1F6", "inforow": "#F4F4F8", "tip": "#FFFFFF",
    },
}

_QSS_TMPL = """
* { font-family: 'Segoe UI Variable Text', 'Segoe UI', sans-serif; color: %text%; font-size: 13px; }
QToolTip { background: %tip%; color: %text%; border: 1px solid %bd%;
           border-radius: 8px; padding: 6px 9px; font-size: 12px; }
#root { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 %bg1%, stop:1 %bg2%); }
#header { background: transparent; }
QDialog { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 %bg1%, stop:1 %bg2%); }
QTabWidget::pane { border: 1px solid %bd%; border-radius: 14px; top: -1px; background: %pane%; }
QTabBar::tab { background: transparent; color: %tabtxt%; padding: 8px 16px;
    border: none; border-radius: 9px; margin: 0 2px 5px 2px; font-weight: 500; }
QTabBar::tab:hover { color: %text%; background: %hover%; }
QTabBar::tab:selected { color: #ffffff; background: %ACCENT%; font-weight: 600; }
#title  { font-size: 16px; font-weight: 800; color: %text%; }
#sub    { color: %muted%; font-size: 12px; }
#status { color: %ACCENT%; font-size: 12px; }
#muted  { color: %muted%; background: transparent; }
#dim    { color: %dim%; background: transparent; }
#strike { color: %muted%; background: transparent; text-decoration: line-through; }
#cardtitle { color: %ACCENT%; font-weight: 700; font-size: 13px; background: transparent; border: none; }
#inforow { background: %inforow%; border-radius: 8px; }
#linkbtn { background: transparent; color: %ACCENT%; border: 1px solid %bd%; border-radius: 8px; padding: 6px 10px; }
#linkbtn:hover { border-color: %ACCENT%; }
#dbgview { background: #0E0E13; color: #C7C7D2; border: 1px solid %bd%; border-radius: 10px; }
#helpdot { background: %bd%; color: %text%; border-radius: 9px; font-weight: 700; font-size: 11px; border: none; }
QFrame#card { background: %card%; border: 1px solid %card_bd%; border-radius: 14px; }
QListWidget { background: %surface%; border: 1px solid %bd%; border-radius: 12px; padding: 4px; outline: none; }
QListWidget::item { padding: 9px 10px; border-radius: 8px; border: none; }
QListWidget::item:hover { background: %hover%; }
QListWidget::item:selected { background: %sel%; color: %ACCENT%; border: none; outline: none; }
QMenu { background: #17171F; color: #ECECF1; border: 1px solid #2A2A34; border-radius: 10px; padding: 5px; }
QMenu::item { padding: 7px 22px 7px 14px; border-radius: 7px; }
QMenu::item:selected { background: rgba(124,108,246,0.30); color: #ffffff; }
QMenu::separator { height: 1px; background: #2A2A34; margin: 4px 8px; }
#acctrow { background: %surface%; border: 1px solid %bd%; border-radius: 10px; }
#acctrow:hover { background: %hover%; border: 1px solid %bd_hi%; }
#colhead { color: %muted%; font-size: 11px; font-weight: 700; background: transparent; }
QPushButton { background: %btn%; color: %text%; border: 1px solid %bd%; border-radius: 9px; padding: 7px 12px; }
QPushButton:hover { background: %btn_hi%; border-color: %bd_hi%; }
QPushButton:pressed { background: %hover%; }
QPushButton#accent { border: 1px solid %ACCENT%; color: #ffffff; font-weight: 600; background: %ACCENT%; }
QPushButton#accent:hover { background: %ACCENT_HI%; border-color: %ACCENT_HI%; }
QLineEdit { background: %input%; border: 1px solid %bd%; border-radius: 9px; padding: 6px 9px; color: %text%; }
QLineEdit:focus { border: 1px solid %ACCENT%; }
QComboBox { background: %input%; border: 1px solid %bd%; border-radius: 9px; padding: 5px 30px 5px 10px; color: %text%; }
QComboBox:hover { border-color: %bd_hi%; }
QComboBox:focus { border-color: %ACCENT%; }
QComboBox::drop-down { subcontrol-origin: padding; subcontrol-position: center right;
                       width: 26px; border: none; background: transparent; }
QComboBox::down-arrow { image: none; width: 0; height: 0; margin-right: 10px;
                        border-left: 4px solid transparent; border-right: 4px solid transparent;
                        border-top: 5px solid %muted%; }
QComboBox::down-arrow:hover { border-top-color: %text%; }
QComboBox QAbstractItemView { background: %surface%; border: 1px solid %bd%; border-radius: 10px;
                              color: %text%; outline: none; padding: 4px;
                              selection-background-color: %sel%; selection-color: %ACCENT%; }
QComboBox QAbstractItemView::item { padding: 7px 9px; border-radius: 7px; min-height: 18px; }
QComboBox QAbstractItemView::item:hover { background: %hover%; }
QPlainTextEdit { background: %input%; border: 1px solid %bd%; border-radius: 10px; color: %dim%; }
QCheckBox { spacing: 8px; background: transparent; }
QScrollArea { border: none; background: transparent; }
QScrollBar:vertical { background: transparent; width: 10px; margin: 2px 0; }
QScrollBar::handle:vertical { background: %sb%; border-radius: 5px; min-height: 28px; }
QScrollBar::handle:vertical:hover { background: %sb_hi%; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
QScrollBar:horizontal { background: transparent; height: 10px; margin: 0 2px; }
QScrollBar::handle:horizontal { background: %sb%; border-radius: 5px; min-width: 28px; }
QScrollBar::handle:horizontal:hover { background: %sb_hi%; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
"""


def build_qss(name="dark"):
    t = dict(THEMES.get(name, THEMES["dark"]))
    t["ACCENT"] = ACCENT
    t["ACCENT_HI"] = ACCENT_HI
    s = _QSS_TMPL
    for k, v in t.items():
        s = s.replace("%" + k + "%", v)
    return s


QSS = build_qss("dark")    # défaut ; remplacé au démarrage par le thème enregistré


# --------------------------------------------------------------------------
#  Overlay in-game
# --------------------------------------------------------------------------


class Overlay(QWidget):
    def __init__(self):
        super().__init__(None, Qt.FramelessWindowHint | Qt.Tool | Qt.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)   # ne prend jamais le focus Windows
        self._topmost = None
        self.scale = 1.0                 # facteur de taille de l'overlay (réglable)
        self._last_items = []            # mémorise les lignes pour rebâtir lors d'un changement d'échelle
        box = QVBoxLayout(self)
        box.setContentsMargins(0, 0, 0, 0)
        panel = QWidget()
        panel.setStyleSheet("background: rgba(16,20,27,0.92); border: 1px solid #2f3947;"
                            "border-radius: 12px;")
        self.pl = QVBoxLayout(panel)
        self.pl.setContentsMargins(self._s(10), self._s(8), self._s(10), self._s(8))
        self.pl.setSpacing(self._s(4))
        self._top = QHBoxLayout(); self._top.setSpacing(self._s(8))
        top = self._top
        self.title = QPushButton("DPF")
        self.title.setCursor(Qt.PointingHandCursor)
        self.title.setToolTip("Afficher / masquer la fenêtre DPF")
        self._style_title()
        self.title.clicked.connect(lambda: self.on_toggle_window() if self.on_toggle_window else None)
        top.addWidget(self.title)
        top.addStretch()
        self.btn_autofocus = QPushButton("A-Switch ON")
        self.btn_autofocus.setCursor(Qt.PointingHandCursor)
        self.btn_autofocus.clicked.connect(lambda: self.on_autofocus() if self.on_autofocus else None)
        top.addWidget(self.btn_autofocus)
        self.btn_autoskip = QPushButton("A-Skip OFF")
        self.btn_autoskip.setCursor(Qt.PointingHandCursor)
        self.btn_autoskip.clicked.connect(lambda: self.on_autoskip() if self.on_autoskip else None)
        top.addWidget(self.btn_autoskip)
        self.btn_autotrade = QPushButton("A-Trade OFF")
        self.btn_autotrade.setCursor(Qt.PointingHandCursor)
        self.btn_autotrade.clicked.connect(lambda: self.on_toggle_trade() if self.on_toggle_trade else None)
        top.addWidget(self.btn_autotrade)
        self.pl.addLayout(top)
        self.rows = QVBoxLayout()
        self.rows.setSpacing(self._s(3))
        self.pl.addLayout(self.rows)
        box.addWidget(panel)
        self.move(24, 24)
        self._rows = []        # dict par perso
        self._active = None
        self._autoskip = False
        self._autofocus = True
        self._autotrade = False
        self._drag = None
        self._last_title = None
        # callbacks (definis par MainWindow)
        self.on_autoskip = None       # ()
        self.on_autofocus = None      # ()
        self.on_toggle_trade = None   # () : clic sur "A-Trade"
        self.on_toggle_skip = None    # (hwnd)
        self.on_toggle_enable = None  # (hwnd)
        self.on_toggle_combat = None  # (hwnd)
        self.on_toggle_echange = None # (hwnd)  (non utilise sur l'overlay)
        self.on_moved = None          # (x, y)
        self.on_focus = None          # (hwnd) : clic sur le pseudo -> ouvre la fenetre
        self.on_toggle_window = None   # () : clic sur "DPF" -> affiche/masque la fenetre principale

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag = e.globalPosition().toPoint() - self.frameGeometry().topLeft()
            e.accept()

    def mouseMoveEvent(self, e):
        if self._drag is not None and (e.buttons() & Qt.LeftButton):
            self.move(e.globalPosition().toPoint() - self._drag)
            e.accept()

    def mouseReleaseEvent(self, e):
        if self._drag is not None and self.on_moved:
            p = self.pos()
            try:
                self.on_moved(p.x(), p.y())   # sauvegarde la position
            except Exception:
                pass
        self._drag = None

    def set_topmost(self, on):
        # au-dessus de Dofus uniquement : topmost quand on est sur Dofus, z normal sinon
        # (l'overlay reste VISIBLE dans les deux cas, mais ne couvre pas les autres apps)
        on = bool(on)
        if on == self._topmost:
            return
        self._topmost = on
        try:
            hwnd = int(self.winId())
            HWND_TOPMOST, HWND_NOTOPMOST = -1, -2
            SWP_NOSIZE, SWP_NOMOVE, SWP_NOACTIVATE = 0x0001, 0x0002, 0x0010
            win32gui.SetWindowPos(hwnd, HWND_TOPMOST if on else HWND_NOTOPMOST,
                                  0, 0, 0, 0, SWP_NOSIZE | SWP_NOMOVE | SWP_NOACTIVATE)
        except Exception:
            pass

    def _refit(self):
        # recolle la fenetre a son contenu (grandit ET retrecit). Appele en DIFFERE
        # (apres que les labels aient recalcule leur taille) -> le retrecissement
        # marche vraiment, et seulement au changement de contenu (drag reste fluide).
        try:
            self.layout().activate()
            self.resize(self.sizeHint())
        except Exception:
            pass

    def set_chrono(self, txt):
        if txt == self._last_title:
            return
        shorter = bool(self._last_title) and len(txt) < len(self._last_title)
        self._last_title = txt
        self.title.setText(txt)
        if shorter:
            QTimer.singleShot(0, self._refit)   # retrecissement (chrono coupe) : rare
        else:
            self.adjustSize()                    # croissance/meme taille : leger, fluide

    def _s(self, v):
        return max(1, int(round(v * self.scale)))

    def _style_title(self):
        self.title.setStyleSheet("QPushButton { color: %s; font-weight: 700; font-size: %dpx;"
                                 " background: transparent; border: none; padding: 0 %dpx; }"
                                 "QPushButton:hover { color: #ffffff; }"
                                 % (ACCENT, self._s(13), self._s(3)))

    def set_scale(self, s):
        try:
            self.scale = max(0.7, min(1.8, float(s)))
        except Exception:
            self.scale = 1.0
        self.pl.setContentsMargins(self._s(10), self._s(8), self._s(10), self._s(8))
        self.pl.setSpacing(self._s(4))
        self._top.setSpacing(self._s(8))
        self.rows.setSpacing(self._s(3))
        self._style_title()
        self.set_autofocus(self._autofocus)
        self.set_autoskip(self._autoskip)
        self.set_autotrade(self._autotrade)
        self.set_chars(self._last_items)
        QTimer.singleShot(0, self._refit)

    def set_autoskip(self, on):
        self._autoskip = bool(on)
        self.btn_autoskip.setText("A-Skip ON" if on else "A-Skip OFF")
        fs, pv, ph, br = self._s(13), self._s(5), self._s(10), self._s(7)
        self.btn_autoskip.setStyleSheet(
            ("background:%s; color:#12161c; font-weight:600; border-radius:%dpx; padding:%dpx %dpx; font-size:%dpx;"
             % (ACCENT, br, pv, ph, fs)) if on
            else "background:#1a1f26; color:#8a93a3; border-radius:%dpx; padding:%dpx %dpx; font-size:%dpx;"
                 % (br, pv, ph, fs))
        self._restyle()

    def set_autofocus(self, on):
        self._autofocus = bool(on)
        self.btn_autofocus.setText("A-Switch ON" if on else "A-Switch OFF")
        fs, pv, ph, br = self._s(13), self._s(5), self._s(10), self._s(7)
        self.btn_autofocus.setStyleSheet(
            ("background:%s; color:#fff; font-weight:600; border-radius:%dpx; padding:%dpx %dpx; font-size:%dpx;"
             % (BLUE, br, pv, ph, fs)) if on
            else "background:#1a1f26; color:#8a93a3; border-radius:%dpx; padding:%dpx %dpx; font-size:%dpx;"
                 % (br, pv, ph, fs))
        self._restyle()

    def set_autotrade(self, on):
        self._autotrade = bool(on)
        if not hasattr(self, "btn_autotrade"):
            return
        self.btn_autotrade.setText("A-Trade ON" if on else "A-Trade OFF")
        fs, pv, ph, br = self._s(13), self._s(5), self._s(10), self._s(7)
        self.btn_autotrade.setStyleSheet(
            ("background:#3fb37f; color:#0f1410; font-weight:600; border-radius:%dpx; padding:%dpx %dpx; font-size:%dpx;"
             % (br, pv, ph, fs)) if on
            else "background:#1a1f26; color:#8a93a3; border-radius:%dpx; padding:%dpx %dpx; font-size:%dpx;"
                 % (br, pv, ph, fs))

    def set_chars(self, items):
        # items = [(name, hwnd, disabled, skip, fcombat)]
        self._last_items = list(items)
        while self.rows.count():
            it = self.rows.takeAt(0)
            lay = it.layout()
            if lay:
                while lay.count():
                    sub = lay.takeAt(0)
                    if sub.widget():
                        sub.widget().deleteLater()
            elif it.widget():
                it.widget().deleteLater()
        self._rows = []
        for name, hwnd, disabled, skip, fcombat in items:
            row = QHBoxLayout(); row.setSpacing(self._s(5))
            b_en = QPushButton()                 # ✓ / ✕ (defini dans _restyle)
            b_sk = QPushButton("\u23ed")         # ⏭ AutoSkip
            b_co = QPushButton("\u2694")         # ⚔ AutoFocus combat
            for b in (b_en, b_sk, b_co):
                b.setFixedSize(self._s(26), self._s(21))
                b.setCursor(Qt.PointingHandCursor)
            b_en.clicked.connect(lambda _=False, h=hwnd: self.on_toggle_enable(h) if self.on_toggle_enable else None)
            b_sk.clicked.connect(lambda _=False, h=hwnd: self.on_toggle_skip(h) if self.on_toggle_skip else None)
            b_co.clicked.connect(lambda _=False, h=hwnd: self.on_toggle_combat(h) if self.on_toggle_combat else None)
            b_en.setToolTip("Activer / désactiver"); b_sk.setToolTip("AutoSkip")
            b_co.setToolTip("AutoFocus combat")
            lbl = QPushButton(name)
            lbl.setFlat(True)
            lbl.setCursor(Qt.PointingHandCursor)
            lbl.setToolTip("%s\n%s  ·  AutoSkip %s  ·  Combat %s\nClic = activer cette fenêtre" % (
                name,
                "Désactivé" if disabled else "Activé",
                "ON" if skip else "OFF",
                "ON" if fcombat else "OFF"))
            lbl.clicked.connect(lambda _=False, h=hwnd: self.on_focus(h) if self.on_focus else None)
            for wdg in (b_en, b_sk, b_co, lbl):
                row.addWidget(wdg)
            row.addStretch()
            self.rows.addLayout(row)
            self._rows.append({"hwnd": hwnd, "disabled": disabled, "skip": skip,
                               "fcombat": fcombat,
                               "lbl": lbl, "b_en": b_en, "b_sk": b_sk, "b_co": b_co})
        self._active = None
        self._restyle()
        self.adjustSize()

    def set_active(self, hwnd):
        if hwnd == self._active:
            return
        self._active = hwnd
        self._restyle()

    def _restyle(self):
        rad = self._s(6)
        fs_lbl = self._s(13)
        fs_en = self._s(12)
        fs_sm = self._s(11)
        pad = "%dpx %dpx" % (self._s(1), self._s(6))
        for r in self._rows:
            hwnd, disabled, skip, lbl = r["hwnd"], r["disabled"], r["skip"], r["lbl"]
            base = "text-align:left; border:none; padding:%s; font-size:%dpx;" % (pad, fs_lbl)
            if disabled:
                lbl.setStyleSheet(base + "color:#6b7280; text-decoration: line-through; background: transparent;")
            elif hwnd == self._active:
                lbl.setStyleSheet(base + "color:#12161c; background:%s; border-radius:%dpx; font-weight:600;" % (ACCENT, rad))
            else:
                lbl.setStyleSheet(base + "color:#cfcabb; background: transparent;")
            if disabled:
                r["b_en"].setText("\u2715")
                r["b_en"].setStyleSheet("border-radius:%dpx; font-size:%dpx; font-weight:700;"
                                        "color:#ffffff; background:#b04848;" % (rad, fs_en))
            else:
                r["b_en"].setText("\u2713")
                r["b_en"].setStyleSheet("border-radius:%dpx; font-size:%dpx; font-weight:700;"
                                        "color:#ffffff; background:#4aa460;" % (rad, fs_en))
            on = skip and self._autoskip
            r["b_sk"].setStyleSheet(
                ("border-radius:%dpx; font-size:%dpx; font-weight:700; color:#12161c; background:%s;" % (rad, fs_sm, ACCENT)) if on
                else ("border-radius:%dpx; font-size:%dpx; color:#9ad0a8; background:rgba(154,208,168,0.14);" % (rad, fs_sm) if skip
                      else "border-radius:%dpx; font-size:%dpx; color:#5b6675; background:#161b22;" % (rad, fs_sm)))
            # ⚔ AutoFocus combat : bleu plein si actif ET AutoFocus global ON ; bleu mat si actif seul
            con = r["fcombat"] and self._autofocus
            r["b_co"].setStyleSheet(
                ("border-radius:%dpx; font-size:%dpx; font-weight:700; color:#fff; background:%s;" % (rad, fs_sm, BLUE)) if con
                else ("border-radius:%dpx; font-size:%dpx; color:#9cc1ee; background:rgba(61,123,214,0.16);" % (rad, fs_sm) if r["fcombat"]
                      else "border-radius:%dpx; font-size:%dpx; color:#5b6675; background:#161b22;" % (rad, fs_sm)))


class HelpDot(QLabel):
    def __init__(self, text):
        super().__init__("?")
        self._tip = "<div style='max-width:320px'>%s</div>" % text
        self.setFixedSize(18, 18)
        self.setAlignment(Qt.AlignCenter)
        self.setCursor(Qt.WhatsThisCursor)
        self.setObjectName("helpdot")

    def enterEvent(self, e):
        from PySide6.QtWidgets import QToolTip
        from PySide6.QtGui import QCursor
        QToolTip.showText(QCursor.pos(), self._tip, self)   # affichage immediat
        super().enterEvent(e)

    def leaveEvent(self, e):
        from PySide6.QtWidgets import QToolTip
        QToolTip.hideText()
        super().leaveEvent(e)


class HotkeyButton(QPushButton):
    def __init__(self, value="", on_change=None, on_begin=None, on_end=None):
        super().__init__()
        self._value = (value or "").lower()
        self._capturing = False
        self._on_change = on_change
        self._on_begin = on_begin
        self._on_end = on_end
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.StrongFocus)
        self.clicked.connect(self._begin)
        self._render()

    def value(self):
        return self._value

    def setValue(self, v):
        self._value = (v or "").lower()
        self._render()

    def _pretty(self):
        labels = {"souris:molette": "Clic molette",
                  "souris:lateral1": "Souris latéral 1",
                  "souris:lateral2": "Souris latéral 2"}
        if self._value in labels:
            return labels[self._value]
        return self._value.upper().replace("+", " + ") if self._value else "(aucune)"

    def _render(self):
        self.setText(self._pretty())

    def enterEvent(self, e):
        if not self._capturing:
            self.setText("Cliquer pour ajouter/modifier")
        super().enterEvent(e)

    def leaveEvent(self, e):
        if not self._capturing:
            self._render()
        super().leaveEvent(e)

    def _begin(self):
        if self._capturing:
            return
        self._capturing = True
        self.setText("Touche, molette ou bouton latéral…")
        self.setFocus(Qt.OtherFocusReason)
        try:
            self.grabKeyboard()
        except Exception:
            pass
        if self._on_begin:
            try:
                self._on_begin()      # suspend les raccourcis globaux pendant la capture
            except Exception:
                pass

    def mousePressEvent(self, e):
        # En capture : molette / boutons latéraux = raccourci. Jamais gauche/droite.
        if self._capturing:
            b = e.button()
            if b == Qt.MiddleButton:
                e.accept(); self._finish("souris:molette"); return
            if b == Qt.BackButton:        # bouton latéral arrière (X1)
                e.accept(); self._finish("souris:lateral1"); return
            if b == Qt.ForwardButton:     # bouton latéral avant (X2)
                e.accept(); self._finish("souris:lateral2"); return
            e.accept(); return            # gauche/droite ignorés (Échap ou clic ailleurs annule)
        return super().mousePressEvent(e)

    def _stop_capture(self):
        self._capturing = False
        try:
            self.releaseKeyboard()
        except Exception:
            pass

    def _finish(self, combo):
        self._stop_capture()
        self.setValue(combo)
        if self._on_change:
            try:
                self._on_change(self)
            except Exception:
                pass
        elif self._on_end:
            try:
                self._on_end()
            except Exception:
                pass

    def focusOutEvent(self, e):
        if self._capturing:
            self._stop_capture()
            self._render()
            if self._on_end:
                try:
                    self._on_end()
                except Exception:
                    pass
        super().focusOutEvent(e)

    def keyPressEvent(self, e):
        if not self._capturing:
            return super().keyPressEvent(e)
        k = e.key()
        if k in (Qt.Key_Control, Qt.Key_Shift, Qt.Key_Alt, Qt.Key_Meta):
            return                                  # attendre une vraie touche
        if k in (Qt.Key_Escape, Qt.Key_Delete, Qt.Key_Backspace):
            self._finish("")                        # Echap / Suppr / Retour = efface
            return
        mods = e.modifiers()
        parts = []
        if mods & Qt.ControlModifier:
            parts.append("ctrl")
        if mods & Qt.AltModifier:
            parts.append("alt")
        if mods & Qt.ShiftModifier:
            parts.append("shift")
        if mods & Qt.MetaModifier:
            parts.append("windows")
        name = self._key_name(k, e.text())
        if not name:
            return
        parts.append(name)
        self._finish("+".join(parts))

    @staticmethod
    def _key_name(k, text):
        if Qt.Key_F1 <= k <= Qt.Key_F35:
            return "f%d" % (k - Qt.Key_F1 + 1)
        if Qt.Key_A <= k <= Qt.Key_Z:
            return chr(k).lower()
        if Qt.Key_0 <= k <= Qt.Key_9:
            return chr(k)
        named = {
            Qt.Key_Space: "space", Qt.Key_Return: "enter", Qt.Key_Enter: "enter",
            Qt.Key_Tab: "tab", Qt.Key_Backspace: "backspace", Qt.Key_Delete: "delete",
            Qt.Key_Home: "home", Qt.Key_End: "end", Qt.Key_PageUp: "page up",
            Qt.Key_PageDown: "page down", Qt.Key_Up: "up", Qt.Key_Down: "down",
            Qt.Key_Left: "left", Qt.Key_Right: "right", Qt.Key_Insert: "insert",
        }
        if k in named:
            return named[k]
        if text and text.isprintable() and text != " ":
            return text.lower()
        return ""


class ReorderListWidget(QListWidget):
    """Réordonnancement par GLISSER avec effet flottant : la ligne se soulève,
    suit le curseur, et les autres laissent la place en temps réel."""
    orderChanged = Signal()

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setDragDropMode(QAbstractItemView.NoDragDrop)   # on gère tout nous-mêmes
        self.viewport().setCursor(Qt.OpenHandCursor)
        self._press_pt = None
        self._drag_row = -1
        self._lifted = False
        self._float = None
        self._grab_dy = 0
        self._orig_text = None

    def _pt(self, e):
        try:
            return e.position().toPoint()
        except Exception:
            return e.pos()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            it = self.itemAt(self._pt(e))
            self._drag_row = self.row(it) if it is not None else -1
            self._press_pt = self._pt(e)
            self._lifted = False
            if self._drag_row >= 0:
                self.setCurrentRow(self._drag_row)
        super().mousePressEvent(e)

    def _lift(self):
        from PySide6.QtCore import QPoint
        from PySide6.QtGui import QRegion, QColor, QPixmap
        from PySide6.QtWidgets import QGraphicsDropShadowEffect
        it = self.item(self._drag_row)
        if it is None:
            return
        rect = self.visualItemRect(it)
        pix = QPixmap(rect.size())
        pix.fill(Qt.transparent)
        self.viewport().render(pix, QPoint(0, 0), QRegion(rect))   # capture la ligne
        self._float = QLabel(self.viewport())
        self._float.setPixmap(pix)
        self._float.setGeometry(rect)
        eff = QGraphicsDropShadowEffect(self._float)
        eff.setBlurRadius(20); eff.setOffset(0, 4); eff.setColor(QColor(0, 0, 0, 170))
        self._float.setGraphicsEffect(eff)
        self._float.show()
        self._grab_dy = self._press_pt.y() - rect.y()
        self._orig_text = it.text()
        it.setText("")             # la ligne d'origine devient un "trou" qui se déplace
        self._lifted = True

    def mouseMoveEvent(self, e):
        if self._drag_row >= 0 and (e.buttons() & Qt.LeftButton):
            pos = self._pt(e)
            if not self._lifted:
                if (pos - self._press_pt).manhattanLength() < 5:
                    return super().mouseMoveEvent(e)   # simple clic, pas encore un glisser
                self.viewport().setCursor(Qt.ClosedHandCursor)
                self._lift()
            if self._float is not None:                # la ligne flottante suit le curseur
                y = max(0, min(pos.y() - self._grab_dy,
                               self.viewport().height() - self._float.height()))
                self._float.move(self._float.x(), y)
            it = self.itemAt(pos)                      # réordonne en direct (les autres glissent)
            target = self.row(it) if it is not None else (self.count() - 1 if pos.y() > 0 else 0)
            if 0 <= target < self.count() and target != self._drag_row:
                item = self.takeItem(self._drag_row)
                self.insertItem(target, item)
                self.setCurrentRow(target)
                self._drag_row = target
            return
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        self.viewport().setCursor(Qt.OpenHandCursor)
        lifted = self._lifted
        if lifted:
            it = self.item(self._drag_row)
            if it is not None and self._orig_text is not None:
                it.setText(self._orig_text)            # repose la ligne à sa place finale
            if self._float is not None:
                self._float.deleteLater()
                self._float = None
        self._drag_row = -1
        self._lifted = False
        self._orig_text = None
        super().mouseReleaseEvent(e)
        if lifted:
            self.orderChanged.emit()


class RegionSelector(QWidget):
    """Sélecteur de zone façon « capture d'écran » : overlay translucide plein écran,
    on maintient le clic et on glisse pour entourer une zone. Échap annule.
    Appelle on_done(x1, y1, x2, y2) en coordonnées ÉCRAN au relâchement."""

    def __init__(self, on_done):
        super().__init__()
        self.on_done = on_done
        self._origin = None
        self._cur = None
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.setCursor(Qt.CrossCursor)
        self.showFullScreen()
        self.raise_()
        self.activateWindow()

    def _pt(self, e):
        try:
            return e.position().toPoint()
        except Exception:
            return e.pos()

    def mousePressEvent(self, e):
        self._origin = self._pt(e)
        self._cur = self._origin
        self.update()

    def mouseMoveEvent(self, e):
        if self._origin is not None:
            self._cur = self._pt(e)
            self.update()

    def mouseReleaseEvent(self, e):
        if self._origin is None:
            self.close()
            return
        r = QRect(self._origin, self._pt(e)).normalized()
        tl = self.mapToGlobal(r.topLeft())
        br = self.mapToGlobal(r.bottomRight())
        cb = self.on_done
        self.close()
        if r.width() >= 4 and r.height() >= 4 and cb:
            cb(tl.x(), tl.y(), br.x(), br.y())

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.on_done = None
            self.close()

    def paintEvent(self, e):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(0, 0, 0, 110))
        # bandeau d'aide en haut
        p.setPen(QColor("#ffffff"))
        p.drawText(self.rect().adjusted(0, 24, 0, 0), Qt.AlignHCenter | Qt.AlignTop,
                   "Glisse pour entourer la zone du nom   ·   Échap pour annuler")
        if self._origin is not None and self._cur is not None:
            r = QRect(self._origin, self._cur).normalized()
            p.setCompositionMode(QPainter.CompositionMode_Clear)   # « trou » net dans le voile
            p.fillRect(r, Qt.transparent)
            p.setCompositionMode(QPainter.CompositionMode_SourceOver)
            p.setPen(QPen(QColor(ACCENT), 2))
            p.drawRect(r)
            p.setPen(QColor("#ffffff"))
            p.drawText(r.x(), max(12, r.y() - 6), "%d x %d" % (r.width(), r.height()))
