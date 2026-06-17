from .ui_base import *
from .ui_base import _tray_log


class TabActionsMixin:
    def _tab_actions(self):
        from PySide6.QtWidgets import QScrollArea
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.addWidget(QLabel("Macros : une ou plusieurs positions cliquées dans l'ordre, "
                             "déclenchées par une touche (et en option, automatiquement)."))

        self.act_list = QListWidget()
        self.act_list.currentRowChanged.connect(self._action_select)
        self.act_list.setMaximumHeight(140)
        lay.addWidget(self.act_list)

        rowb = QHBoxLayout()
        b_add = QPushButton("Ajouter"); b_add.clicked.connect(self.action_add)
        b_del = QPushButton("Supprimer"); b_del.clicked.connect(self.action_delete)
        rowb.addWidget(b_add); rowb.addWidget(b_del); rowb.addStretch()
        lay.addLayout(rowb)

        area = QScrollArea(); area.setWidgetResizable(True); area.setFrameShape(QScrollArea.NoFrame)
        area.setStyleSheet("QScrollArea{border:none; background:transparent;}"
                           "QScrollArea > QWidget > QWidget{background:transparent;}")
        host = QWidget(); ed = QVBoxLayout(host); ed.setSpacing(10)
        area.setWidget(host)
        lay.addWidget(area, 1)

        # Nom
        g1 = QGridLayout(); g1.setHorizontalSpacing(8)
        g1.addWidget(self._field_label("Nom", "Nom de la macro (juste pour t'y retrouver)."), 0, 0)
        self.act_name = QLineEdit(); g1.addWidget(self.act_name, 0, 1, 1, 3)
        ed.addLayout(g1)

        # Positions (multiples)
        hp = QHBoxLayout()
        hp.addWidget(QLabel("Positions"))
        hp.addWidget(self._help("Une ou plusieurs positions. Elles sont cliquées DANS L'ORDRE : "
                                "Position 1 d'abord, puis Position 2, etc. (pratique pour les métiers). "
                                "Capture chaque position en cliquant à l'écran."))
        hp.addStretch()
        b_addpos = QPushButton("+ Ajouter une position"); b_addpos.clicked.connect(self._act_add_position)
        hp.addWidget(b_addpos)
        ed.addLayout(hp)
        self.act_pos_box = QVBoxLayout(); self.act_pos_box.setSpacing(4)
        ed.addLayout(self.act_pos_box)
        self._act_positions = []

        # Clic / delai / cible
        g2 = QGridLayout(); g2.setHorizontalSpacing(8); g2.setVerticalSpacing(8)
        g2.addWidget(self._field_label("Nombre de clic", "1 = simple clic, 2 = double clic (comme un humain)."), 0, 0)
        self.act_clicks = QComboBox(); self.act_clicks.addItems(["1 (simple)", "2 (double)"])
        g2.addWidget(self.act_clicks, 0, 1)
        g2.addWidget(self._field_label("Délai (ms)", "Temps d'attente entre chaque position (règle la vitesse des clics)."), 0, 2)
        self.act_delay = QLineEdit("120"); self.act_delay.setFixedWidth(80); g2.addWidget(self.act_delay, 0, 3)
        g2.addWidget(self._field_label("Cible", "Fenêtre active : clique seulement sur le perso au premier plan. "
                                       "Toutes les fenêtres : clique sur tous les persos (en simultané)."), 1, 0)
        self.act_target = QComboBox(); self.act_target.addItems(["Fenêtre active", "Toutes les fenêtres"])
        g2.addWidget(self.act_target, 1, 1, 1, 3)
        g2.addWidget(self._field_label("Raccourcis", "Touche qui déclenche la macro."), 2, 0)
        self.act_hotkey = self._mk_hotkey(""); g2.addWidget(self.act_hotkey, 2, 1, 1, 3)
        ed.addLayout(g2)

        # Clic en arrière-plan (sans switch) — recommandé pour Prêt / potions / reconnexion
        hb_bg = QHBoxLayout()
        self.act_bg = QCheckBox("Clic en arrière-plan (sans switch — instantané)")
        hb_bg.addWidget(self.act_bg)
        hb_bg.addWidget(self._help("Recommandé pour Prêt / potion de rappel / reconnexion : clique sur "
                                   "les fenêtres SANS les faire passer devant (la souris fonctionne en "
                                   "arrière-plan). Décoché = passe chaque fenêtre devant avant de cliquer."))
        hb_bg.addStretch(1)
        ed.addLayout(hb_bg)

        # Auto (optionnel)
        g3 = QGridLayout(); g3.setHorizontalSpacing(8)
        self.act_auto = QCheckBox("Répéter automatiquement")
        g3.addWidget(self.act_auto, 0, 0)
        g3.addWidget(self._help("Optionnel : rejoue la macro toute seule à intervalle régulier "
                                "(comme les messages auto). Ne se déclenche que quand Dofus est au premier plan."), 0, 1)
        g3.addWidget(QLabel("Toutes les (s)"), 0, 2)
        self.act_interval = QLineEdit("30"); self.act_interval.setFixedWidth(70); g3.addWidget(self.act_interval, 0, 3)
        g3.setColumnStretch(1, 1)
        ed.addLayout(g3)
        ed.addStretch(1)        # colle tout en haut -> plus de trou quand il n'y a pas de position

        save = QPushButton("Enregistrer la macro"); save.setObjectName("accent")
        save.clicked.connect(self.action_save)
        lay.addWidget(save)

        self._refresh_actions()
        self._act_rebuild_positions()
        return w

    def _act_rebuild_positions(self):
        if not hasattr(self, "act_pos_box"):
            return
        while self.act_pos_box.count():
            it = self.act_pos_box.takeAt(0)
            lyt = it.layout()
            if lyt:
                while lyt.count():
                    s = lyt.takeAt(0)
                    if s.widget():
                        s.widget().deleteLater()
            elif it.widget():
                it.widget().deleteLater()
        if not self._act_positions:
            self.act_pos_box.addWidget(QLabel("Aucune position. Clique « + Ajouter une position »."))
            return
        for i, (x, y) in enumerate(self._act_positions):
            row = QHBoxLayout()
            row.addWidget(QLabel("Position %d : (%d, %d)" % (i + 1, x, y)))
            row.addStretch()
            b_cap = QPushButton("Capturer"); b_cap.clicked.connect(lambda _=False, n=i: self.capture("actpos:%d" % n))
            b_rm = QPushButton("Retirer"); b_rm.clicked.connect(lambda _=False, n=i: self._act_remove_position(n))
            row.addWidget(b_cap); row.addWidget(b_rm)
            self.act_pos_box.addLayout(row)

    def _act_add_position(self):
        self._act_positions.append([0, 0])
        self._act_rebuild_positions()

    def _act_remove_position(self, i):
        if 0 <= i < len(self._act_positions):
            self._act_positions.pop(i)
            self._act_rebuild_positions()

    def _refresh_actions(self):
        if not hasattr(self, "act_list"):
            return
        cur = self.act_list.currentRow()
        self.act_list.clear()
        for a in self.cfg.get("actions", []):
            tgt = "toutes" if a.get("target") == "all" else "active"
            n = len(a.get("positions", []))
            extra = " · auto" if a.get("auto") else ""
            self.act_list.addItem("%s   [%s]   %d pos -> %s%s"
                                  % (a.get("name", "?"), a.get("hotkey", ""), n, tgt, extra))
        if 0 <= cur < self.act_list.count():
            self.act_list.setCurrentRow(cur)

    def _action_select(self, row):
        acts = self.cfg.get("actions", [])
        if row < 0 or row >= len(acts):
            return
        a = acts[row]
        self.act_name.setText(a.get("name", ""))
        self._act_positions = [list(p) for p in a.get("positions", [])]
        self._act_rebuild_positions()
        self.act_clicks.setCurrentIndex(1 if int(a.get("clicks", 1)) >= 2 else 0)
        self.act_delay.setText(str(a.get("delay_ms", 120)))
        self.act_target.setCurrentIndex(1 if a.get("target") == "all" else 0)
        self.act_hotkey.setValue(a.get("hotkey", ""))
        self.act_auto.setChecked(bool(a.get("auto")))
        self.act_bg.setChecked(bool(a.get("bg")))
        self.act_interval.setText(str(a.get("interval_s", 30)))

    def action_add(self):
        self.cfg.setdefault("actions", []).append(
            {"name": "Nouvelle macro", "positions": [], "clicks": 1, "delay_ms": 120,
             "hotkey": "", "target": "all", "bg": True, "auto": False, "interval_s": 30})
        config.save(self.cfg)
        self._refresh_actions()
        self.act_list.setCurrentRow(len(self.cfg["actions"]) - 1)

    def action_delete(self):
        r = self.act_list.currentRow()
        acts = self.cfg.get("actions", [])
        if 0 <= r < len(acts):
            acts.pop(r)
            config.save(self.cfg)
            self._refresh_actions()
            self.apply_hotkeys()
            self._act_auto_on.clear()

    def action_save(self):
        r = self.act_list.currentRow()
        acts = self.cfg.get("actions", [])
        if r < 0 or r >= len(acts):
            self.status.setText("Sélectionne ou ajoute une macro d'abord.")
            return
        acts[r] = {
            "name": self.act_name.text().strip() or "Macro",
            "positions": [[int(x), int(y)] for x, y in self._act_positions],
            "clicks": 2 if self.act_clicks.currentIndex() == 1 else 1,
            "delay_ms": self._int(self.act_delay, 120),
            "hotkey": self.act_hotkey.value(),
            "target": "all" if self.act_target.currentIndex() == 1 else "active",
            "bg": bool(self.act_bg.isChecked()),
            "auto": bool(self.act_auto.isChecked()),
            "interval_s": max(1, self._int(self.act_interval, 30)),
        }
        config.save(self.cfg)
        self._refresh_actions()
        self.apply_hotkeys()
        self._act_auto_on.clear()            # stoppe toute repetition en cours (les index ont pu changer)
        self.status.setText("Macro enregistrée.")

    def run_action(self, idx):
        # Handler de la touche : si la macro est "auto", la touche DEMARRE/ARRETE la repetition.
        # Sinon, elle joue la macro une fois.
        acts = self.cfg.get("actions", [])
        if idx < 0 or idx >= len(acts):
            return
        a = acts[idx]
        if not a.get("positions"):
            self.status.setText("Macro '%s' : aucune position." % a.get("name", "?"))
            return
        if a.get("auto"):
            if idx in self._act_auto_on:
                self._act_auto_on.discard(idx)
                self.status.setText("Macro '%s' : répétition ARRÊTÉE." % a.get("name", "?"))
            else:
                self._act_auto_on.add(idx)
                self._act_last[idx] = 0.0       # declenche au prochain tick (immediat)
                self.status.setText("Macro '%s' : répétition DÉMARRÉE (toutes les %ss)."
                                    % (a.get("name", "?"), max(1, int(a.get("interval_s", 30)))))
            return
        self._action_fire(a)

    def _action_fire(self, a):
        threading.Thread(target=self._action_worker, args=(a,), daemon=True).start()

    def _action_worker(self, a):
      try:
        positions = [(int(p[0]), int(p[1])) for p in a.get("positions", [])]
        clicks = 2 if int(a.get("clicks", 1)) >= 2 else 1
        delay = max(0, int(a.get("delay_ms", 120))) / 1000.0
        wins = list(self.windows)            # snapshot (detect() peut reassigner)
        if a.get("target") == "all":
            targets = [win["hwnd"] for win in wins if not self._is_disabled(win)]
        else:
            fg = win32gui.GetForegroundWindow()
            ours = [win["hwnd"] for win in wins]
            if fg in ours:
                targets = [fg]
            elif 0 <= self.idx < len(wins):
                targets = [wins[self.idx]["hwnd"]]
            else:
                targets = []
        launcher = win32gui.GetForegroundWindow()
        # --- ARRIÈRE-PLAN : clique sans rien activer (instantané, aucune fenêtre qui saute) ---
        if a.get("bg"):
            for h in targets:
                for (x, y) in positions:
                    try:
                        win32util.background_click(h, x, y, clicks)
                    except Exception:
                        pass
                    if delay:
                        time.sleep(delay)
            self.status.setText("Macro '%s' (arrière-plan) -> %d fenêtre(s), %d position(s)"
                                % (a.get("name", "?"), len(targets), len(positions)))
            return
        # --- AVEC SWITCH : passe chaque fenêtre devant avant de cliquer (ancienne méthode) ---
        for h in targets:
            if not self._activate_confirm(h):
                continue
            for (x, y) in positions:
                self._real_click(x, y, clicks)
                time.sleep(delay)
        if len(targets) > 1 and win32gui.GetForegroundWindow() != launcher:
            try:
                win32util.activate(launcher)
            except Exception:
                pass
        self.status.setText("Macro '%s' -> %d fenêtre(s), %d position(s)"
                            % (a.get("name", "?"), len(targets), len(positions)))
      except Exception:
        self._dbg_exc("macro")

    def _auto_actions_tick(self):
        if not self._act_auto_on:
            return
        if not self._dofus_foreground():
            return
        now = time.time()
        acts = self.cfg.get("actions", [])
        for idx in list(self._act_auto_on):
            if idx < 0 or idx >= len(acts) or not acts[idx].get("auto"):
                self._act_auto_on.discard(idx)
                continue
            a = acts[idx]
            iv = max(1, int(a.get("interval_s", 30)))
            if now - self._act_last.get(idx, 0.0) >= iv:
                self._act_last[idx] = now
                self._action_fire(a)
