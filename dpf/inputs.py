"""
Entrees globales : raccourcis CLAVIER (lib keyboard) + SOURIS (lib mouse : molette,
boutons lateraux X1/X2), exposes en signaux Qt. Les clics gauche/droit ne sont jamais captes.
"""
from PySide6.QtCore import QObject, Signal

try:
    import keyboard
except Exception:
    keyboard = None

try:
    import mouse as mouselib
except Exception:
    mouselib = None

# Valeurs stockees pour la souris -> bouton de la lib 'mouse'
_MOUSE_BTN = {"souris:molette": "middle", "souris:lateral1": "x", "souris:lateral2": "x2"}


class Inputs(QObject):
    nextSig = Signal()
    prevSig = Signal()
    switchSig = Signal()
    backSig = Signal()
    mainSig = Signal()
    validateSig = Signal()
    actionSig = Signal(int)
    messageSig = Signal(int)
    moveModeSig = Signal()
    joinSig = Signal()
    customJoinSig = Signal()
    autoskipSig = Signal()
    autofocusSig = Signal()
    presetSig = Signal(str)
    inviteSig = Signal()
    timerSig = Signal()
    timerResetSig = Signal()
    ctrlShiftSig = Signal()
    overlaySig = Signal()
    tradeSig = Signal()

    def apply_all(self, cfg):
        """Enregistre TOUS les raccourcis (clavier + souris)."""
        if keyboard is None and mouselib is None:
            return
        if keyboard is not None:
            try:
                keyboard.clear_all_hotkeys()
            except Exception:
                pass
        if mouselib is not None:
            try:
                mouselib.unhook_all()
            except Exception:
                pass

        used = set()

        def reg(combo, fn):
            if not combo or combo in used:
                return
            used.add(combo)
            if combo.startswith("souris:"):           # raccourci souris
                btn = _MOUSE_BTN.get(combo)
                if btn and mouselib is not None:
                    try:
                        mouselib.on_button(fn, buttons=(btn,), types=("down",))
                    except Exception as e:
                        print("[mouse]", combo, ":", e)
                return
            if keyboard is None:
                return
            try:
                keyboard.add_hotkey(combo, fn)
            except Exception as e:
                print("[hotkey]", combo, ":", e)

        reg(cfg.get("hotkey_next"), lambda: self.nextSig.emit())
        reg(cfg.get("hotkey_prev"), lambda: self.prevSig.emit())
        reg(cfg.get("hotkey_back"), lambda: self.backSig.emit())
        reg(cfg.get("hotkey_main"), lambda: self.mainSig.emit())
        reg(cfg.get("hotkey_custom_join"), lambda: self.customJoinSig.emit())
        reg(cfg.get("hotkey_validate"), lambda: self.validateSig.emit())
        reg(cfg.get("hotkey_move_mode"), lambda: self.moveModeSig.emit())
        reg(cfg.get("hotkey_join"), lambda: self.joinSig.emit())
        reg(cfg.get("hotkey_invite"), lambda: self.inviteSig.emit())
        reg(cfg.get("hotkey_timer"), lambda: self.timerSig.emit())
        reg(cfg.get("hotkey_timer_reset"), lambda: self.timerResetSig.emit())
        reg(cfg.get("hotkey_autoskip"), lambda: self.autoskipSig.emit())
        reg(cfg.get("hotkey_autofocus"), lambda: self.autofocusSig.emit())
        reg(cfg.get("hotkey_ctrlshift"), lambda: self.ctrlShiftSig.emit())
        reg(cfg.get("hotkey_overlay"), lambda: self.overlaySig.emit())
        reg(cfg.get("autotrade_hotkey"), lambda: self.tradeSig.emit())
        ph = cfg.get("preset_hotkeys", {})
        if isinstance(ph, dict):
            for name, combo in ph.items():
                reg(combo, lambda n=name: self.presetSig.emit(n))

        for i, act in enumerate(cfg.get("actions", [])):
            reg(act.get("hotkey"), lambda idx=i: self.actionSig.emit(idx))
        for i, m in enumerate(cfg.get("messages", [])):
            reg(m.get("hotkey"), lambda idx=i: self.messageSig.emit(idx))

    def stop(self):
        if keyboard is not None:
            try:
                keyboard.clear_all_hotkeys()
            except Exception:
                pass
        if mouselib is not None:
            try:
                mouselib.unhook_all()
            except Exception:
                pass
