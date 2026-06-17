from .ui_base import *
from .ui_base import _tray_log


class TabFenetresMixin:
    def _tab_windows(self):
        from PySide6.QtWidgets import QAbstractItemView
        w = QWidget()
        lay = QVBoxLayout(w)
        head = QHBoxLayout()
        head.addWidget(QLabel("Fenêtres Dofus — glisse à la souris pour réordonner"))
        head.addStretch()
        b_ref = QPushButton("Rafraichir"); b_ref.clicked.connect(self.detect)
        head.addWidget(b_ref)
        lay.addLayout(head)

        self.list = ReorderListWidget()
        self.list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.list.orderChanged.connect(self._on_rows_moved)
        lay.addWidget(self.list, 1)

        row = QHBoxLayout()
        b_fav = QPushButton("\U0001f31f Favori"); b_fav.clicked.connect(self.toggle_favori); row.addWidget(b_fav)
        b_dis = QPushButton("Activer / Desactiver"); b_dis.clicked.connect(self.toggle_disabled); row.addWidget(b_dis)
        b_ren = QPushButton("Renommer"); b_ren.clicked.connect(self.rename)
        b_ren.setToolTip("Change uniquement le NOM affiché (alias : « Eni soin », « Tank »…).\n"
                         "N'altère ni le pseudo ni le titre de la fenêtre, donc sans risque pour l'auto-focus.")
        row.addWidget(b_ren)
        b_min = QPushButton("Tout réduire"); b_min.clicked.connect(self.minimize_all); row.addWidget(b_min)
        b_res = QPushButton("Tout restaurer"); b_res.clicked.connect(self.restore_all); row.addWidget(b_res)
        row.addStretch()
        b_tb = QPushButton("Reorder taskbar"); b_tb.setObjectName("accent")
        b_tb.clicked.connect(self.reorder_taskbar); row.addWidget(b_tb)
        lay.addLayout(row)

        # --- Presets d'ordre (initiative) ---
        lay.addWidget(QLabel("Presets d'ordre (initiative)"))
        pr = QHBoxLayout()
        self.preset_name = QLineEdit(); self.preset_name.setPlaceholderText("Nom du preset (ex. Team Cra)")
        b_save = QPushButton("Enregistrer l'ordre"); b_save.setObjectName("accent")
        b_save.clicked.connect(self.save_preset)
        pr.addWidget(self.preset_name, 1); pr.addWidget(b_save)
        lay.addLayout(pr)

        pr2 = QHBoxLayout()
        self.preset_combo = QComboBox()
        b_load = QPushButton("Charger"); b_load.clicked.connect(self.load_preset)
        b_upd = QPushButton("Mettre à jour")
        b_upd.setToolTip("Écrase le preset sélectionné avec l'ordre actuel des fenêtres")
        b_upd.clicked.connect(self._preset_update_combo)
        b_del = QPushButton("Supprimer"); b_del.clicked.connect(self.delete_preset)
        pr2.addWidget(self.preset_combo, 1); pr2.addWidget(b_load); pr2.addWidget(b_upd); pr2.addWidget(b_del)
        lay.addLayout(pr2)
        self._refresh_presets()

        lay.addWidget(QLabel("Created by scaryztw // Discord : scaryztw"))
        return w

    def _on_rows_moved(self, *args):
        new_hwnds = [self.list.item(i).data(Qt.UserRole) for i in range(self.list.count())]
        by_hwnd = {win["hwnd"]: win for win in self.windows}
        self.windows = [by_hwnd[h] for h in new_hwnds if h in by_hwnd]
        self._save_order()
        QTimer.singleShot(0, self.refresh_views)

    def toggle_favori(self):
        r = self.list.currentRow()
        if r < 0 or r >= len(self.windows):
            return
        title = self.windows[r]["title"]
        e = self.cfg["chars"].setdefault(title, {"name": title, "favori": 0, "disabled": 0})
        new = 0 if e.get("favori") else 1
        if new:
            # un seul favori possible : on retire l'étoile de tous les autres persos
            for k, v in self.cfg["chars"].items():
                if isinstance(v, dict) and k != title:
                    v["favori"] = 0
        e["favori"] = new
        config.save(self.cfg)
        self.refresh_views()
        self._refresh_overlay()
        self.status.setText("%s %s"
                            % (self.name_of(self.windows[r]),
                               "est le favori (les autres étoiles ont été retirées)." if new
                               else "n'est plus favori."))

    def toggle_disabled(self):
        r = self.list.currentRow()
        if r < 0 or r >= len(self.windows):
            return
        title = self.windows[r]["title"]
        e = self.cfg["chars"].setdefault(title, {"name": title, "favori": 0, "disabled": 0})
        e["disabled"] = 0 if e.get("disabled") else 1
        config.save(self.cfg)
        self.refresh_views()
        self._refresh_overlay()
        self.status.setText("%s : %s" % (self.name_of(self.windows[r]),
                                         "désactive" if e["disabled"] else "active"))

    def rename(self):
        r = self.list.currentRow()
        if r < 0:
            return
        win = self.windows[r]
        new, ok = QInputDialog.getText(self, "Renommer", "Nom :", text=self.name_of(win))
        if ok and new.strip():
            self.cfg["chars"][win["title"]]["name"] = new.strip()
            config.save(self.cfg)
            self.refresh_views()

    def _save_order(self):
        self.cfg["order"] = [w["title"] for w in self.windows]
        config.save(self.cfg)

    def reorder_taskbar(self, focus_hwnd=0):
        hwnds = [w["hwnd"] for w in self.windows]
        win32util.reorder_taskbar(hwnds, focus_hwnd)
        self.status.setText("Réorganisation de la taskbar...")

    def _refresh_presets(self):
        if not hasattr(self, "preset_combo"):
            return
        self.preset_combo.clear()
        self.preset_combo.addItems(list(self.cfg.get("presets", {}).keys()))

    def save_preset(self):
        name = self.preset_name.text().strip()
        if not name:
            self.status.setText("Donne un nom au preset d'abord.")
            return
        self.cfg.setdefault("presets", {})[name] = [win["title"] for win in self.windows]
        config.save(self.cfg)
        self._refresh_presets()
        if hasattr(self, "presets_box"):
            self._refresh_presets_tab()
        self.preset_combo.setCurrentText(name)
        self.status.setText("Preset '%s' enregistré (%d persos)." % (name, len(self.windows)))

    def load_preset(self):
        self.load_preset_by_name(self.preset_combo.currentText())

    def load_preset_by_name(self, name):
        order = self.cfg.get("presets", {}).get(name)
        if not order:
            return
        # fenêtre sur laquelle l'utilisateur a lancé le raccourci -> on y reviendra
        fg = win32util.foreground()
        launcher = fg if any(w["hwnd"] == fg for w in self.windows) else 0
        if not launcher and 0 <= self.idx < len(self.windows):
            launcher = self.windows[self.idx]["hwnd"]   # repli : la fenêtre active suivie
        by_title = {win["title"]: win for win in self.windows}
        new = [by_title[t] for t in order if t in by_title]          # persos du preset, dans l'ordre
        new += [win for win in self.windows if win["title"] not in order]  # le reste à la suite
        self.windows = new
        self._save_order()
        self.refresh_views()
        self.reorder_taskbar(launcher)      # réorganise la taskbar (tente déjà de revenir dessus)
        # La ré-activation faite DANS le thread de reorder est peu fiable (SetForegroundWindow
        # hors thread GUI est soumis aux restrictions de premier plan de Windows). On re-focalise
        # donc le lanceur sur le thread GUI une fois la réorganisation terminée : ça « colle ».
        if launcher:
            delay = int((0.3 + max(0, len(self.windows) - 1) * 0.05 + 0.4) * 1000)
            QTimer.singleShot(delay, lambda h=launcher: self._post_reorder_focus(h))
        self.status.setText("Preset '%s' chargé (+ taskbar)." % name)

    def _post_reorder_focus(self, hwnd):
        """Revient fermement sur la fenêtre lanceuse après la réorganisation du Z-order."""
        if not hwnd or not win32util.window_alive(hwnd):
            return
        win32util.activate(hwnd)
        for i, win in enumerate(self.windows):
            if win["hwnd"] == hwnd:
                self.idx = i
                try:
                    self.list.setCurrentRow(i)
                except Exception:
                    pass
                break
        self._refresh_overlay()

    def delete_preset(self):
        name = self.preset_combo.currentText()
        if name in self.cfg.get("presets", {}):
            self.cfg["presets"].pop(name, None)
            self.cfg.get("preset_hotkeys", {}).pop(name, None)
            config.save(self.cfg)
            self._refresh_presets()
            if hasattr(self, "presets_box"):
                self._refresh_presets_tab()
            self.apply_hotkeys()
            self.status.setText("Preset '%s' supprimé." % name)

    def _preset_update_combo(self):
        name = self.preset_combo.currentText().strip()
        if not name:
            self.status.setText("Aucun preset sélectionné à mettre à jour.")
            return
        self._preset_update(name)
