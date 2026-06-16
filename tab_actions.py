from .ui_base import *
from .ui_base import _tray_log

# cibles speciales (les autres valeurs sont des pseudos de perso)
TARGET_ACTIVE = "active"
TARGET_ALL = "all"
_LBL_ACTIVE = "Fenêtre active"
_LBL_ALL = "Toutes les fenêtres"


class TabMessagesMixin:
    def _tab_messages(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.addWidget(QLabel("Messages de chat. Choisis la fenêtre cible par message. "
                             "Dofus bloquant le clavier en arrière-plan, DPF bascule sur la cible, "
                             "envoie, puis revient sur ta fenêtre (si l'option est cochée)."))
        self.msg_text = []
        self.msg_hot = []
        self.msg_auto = []
        self.msg_interval = []
        self.msg_target = []
        grid = QGridLayout(); grid.setHorizontalSpacing(8); grid.setVerticalSpacing(8)
        grid.addWidget(QLabel("Texte"), 0, 1)
        grid.addWidget(QLabel("Raccourcis"), 0, 2)
        grid.addWidget(QLabel("Cible"), 0, 3)
        grid.addWidget(QLabel("Auto"), 0, 4)
        grid.addWidget(QLabel("Toutes les (s)"), 0, 5)
        msgs = self.cfg.get("messages", [])
        for i in range(3):
            m = msgs[i] if i < len(msgs) else {"text": "", "hotkey": ""}
            grid.addWidget(QLabel("Message %d" % (i + 1)), i + 1, 0)
            t = QLineEdit(m.get("text", ""))
            h = self._mk_hotkey(m.get("hotkey", ""))
            cb = QComboBox()
            chk = QCheckBox(); chk.setChecked(bool(m.get("auto", False)))
            chk.stateChanged.connect(self.save_messages)
            iv = QLineEdit(str(m.get("interval", 30))); iv.setFixedWidth(70)
            iv.editingFinished.connect(self.save_messages)
            self.msg_text.append(t); self.msg_hot.append(h); self.msg_target.append(cb)
            self.msg_auto.append(chk); self.msg_interval.append(iv)
            grid.addWidget(t, i + 1, 1); grid.addWidget(h, i + 1, 2)
            grid.addWidget(cb, i + 1, 3); grid.addWidget(chk, i + 1, 4); grid.addWidget(iv, i + 1, 5)
        lay.addLayout(grid)

        self.chk_msg_return = QCheckBox("Revenir à la fenêtre d'origine après l'envoi")
        self.chk_msg_return.setChecked(bool(self.cfg.get("msg_return", True)))
        self.chk_msg_return.stateChanged.connect(self.save_messages)
        lay.addWidget(self.chk_msg_return)

        lay.addWidget(QLabel("Auto : le message part tout seul à l'intervalle, "
                             "uniquement si une fenêtre Dofus est au premier plan."))
        save = QPushButton("Enregistrer les messages"); save.setObjectName("accent")
        save.clicked.connect(self.save_messages)
        lay.addWidget(save)
        lay.addStretch()
        self._populate_msg_targets()
        return w

    def _populate_msg_targets(self):
        """Remplit les listes de cibles (active / toutes / chaque perso), en gardant le choix."""
        if not getattr(self, "msg_target", None):
            return
        pseudos = []
        for win in getattr(self, "windows", []):
            p = self._overlay_name(win)
            if p and p not in pseudos:
                pseudos.append(p)
        msgs = self.cfg.get("messages", [])
        for i, cb in enumerate(self.msg_target):
            saved = msgs[i].get("target", TARGET_ACTIVE) if i < len(msgs) else TARGET_ACTIVE
            cb.blockSignals(True)
            cb.clear()
            cb.addItem(_LBL_ACTIVE, TARGET_ACTIVE)
            cb.addItem(_LBL_ALL, TARGET_ALL)
            for p in pseudos:
                cb.addItem(p, p)
            # restaure la selection
            idx = cb.findData(saved)
            if idx < 0 and saved not in (TARGET_ACTIVE, TARGET_ALL):
                cb.addItem(saved + " (absent)", saved)   # perso pas detecte pour l'instant
                idx = cb.count() - 1
            cb.setCurrentIndex(max(0, idx))
            cb.blockSignals(False)
            if not getattr(cb, "_msg_wired", False):
                cb.currentIndexChanged.connect(self.save_messages)
                cb._msg_wired = True

    def save_messages(self):
        out = []
        for i in range(3):
            try:
                iv = max(1, int(self.msg_interval[i].text()))
            except Exception:
                iv = 30
            tgt = self.msg_target[i].currentData() if i < len(self.msg_target) else TARGET_ACTIVE
            out.append({"text": self.msg_text[i].text(),
                        "hotkey": self.msg_hot[i].value(),
                        "auto": self.msg_auto[i].isChecked(),
                        "interval": iv,
                        "target": tgt or TARGET_ACTIVE})
        self.cfg["messages"] = out
        if hasattr(self, "chk_msg_return"):
            self.cfg["msg_return"] = self.chk_msg_return.isChecked()
        config.save(self.cfg)
        self.apply_hotkeys()
        self.status.setText("Messages enregistrés.")

    def _auto_messages_tick(self):
        msgs = self.cfg.get("messages", [])
        if not self._dofus_foreground():
            return
        now = time.time()
        for i, m in enumerate(msgs[:3]):
            if not m.get("auto") or not m.get("text"):
                continue
            iv = max(1, int(m.get("interval", 30)))
            if now - self._msg_last[i] >= iv:
                self._msg_last[i] = now
                self.send_message(i)

    def _msg_targets_hwnds(self, target):
        """Retourne la liste de hwnд cibles selon le choix."""
        if target == TARGET_ALL:
            return [win["hwnd"] for win in self.windows if not self._is_disabled(win)]
        if target and target != TARGET_ACTIVE:
            for win in self.windows:                      # un pseudo precis
                if self._overlay_name(win) == target:
                    return [win["hwnd"]]
            return []                                     # perso introuvable
        # "active"
        fg = win32gui.GetForegroundWindow()
        ours = [win["hwnd"] for win in self.windows]
        return [fg] if fg in ours else []

    def send_message(self, i):
        msgs = self.cfg.get("messages", [])
        if i < 0 or i >= len(msgs):
            return
        text = msgs[i].get("text", "")
        if not text:
            return
        target = msgs[i].get("target", TARGET_ACTIVE)
        targets = self._msg_targets_hwnds(target)
        if not targets:
            self.status.setText("Message %d : aucune fenêtre cible trouvée." % (i + 1))
            return
        try:
            QApplication.clipboard().setText(text)     # presse-papier sur le thread GUI
        except Exception:
            pass
        launcher = win32gui.GetForegroundWindow()
        ret = bool(self.cfg.get("msg_return", True))
        threading.Thread(target=self._message_worker,
                         args=(i, targets, launcher, ret), daemon=True).start()

    def _kbd(self, vk, up=False):
        win32api.keybd_event(vk, 0, 0x0002 if up else 0, 0)

    def _type_chat_paste(self):
        """Ouvre le chat (Entrée), colle (Ctrl+V), envoie (Entrée) — clavier Win32 brut."""
        VK_RETURN, VK_CTRL, VK_V = 0x0D, 0x11, 0x56
        self._kbd(VK_RETURN); time.sleep(0.04); self._kbd(VK_RETURN, True)
        time.sleep(0.08)
        self._kbd(VK_CTRL); self._kbd(VK_V); time.sleep(0.04)
        self._kbd(VK_V, True); self._kbd(VK_CTRL, True)
        time.sleep(0.08)
        self._kbd(VK_RETURN); time.sleep(0.04); self._kbd(VK_RETURN, True)

    def _message_worker(self, i, targets, launcher, return_focus):
        sent = 0
        for h in targets:
            try:
                if win32gui.GetForegroundWindow() != h:
                    win32util.activate(h)
                    self._wait_foreground(h, 1.0)
                time.sleep(0.05)
                self._type_chat_paste()
                sent += 1
                time.sleep(0.05)
            except Exception as e:
                self._report("Message %d : échec sur une fenêtre (%r)" % (i + 1, e), "warn")
        if return_focus and launcher and win32gui.GetForegroundWindow() != launcher:
            try:
                win32util.activate(launcher)
            except Exception:
                pass
        self._report("Message %d envoyé sur %d fenêtre(s)." % (i + 1, sent), "info")
