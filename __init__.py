from .ui_base import *
from .ui_base import _tray_log


class TabComptesMixin:
    def _tab_comptes(self):
        from PySide6.QtWidgets import QScrollArea
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(8)
        lay.addWidget(QLabel("Autofocus par compte : coche ce que DPF gère automatiquement pour chaque perso."))

        # en-tete de colonnes (aligne sur les memes facteurs d'etirement que les lignes)
        head = QHBoxLayout()
        head.setContentsMargins(12, 0, 12, 0)
        h_perso = QLabel("PERSO"); h_perso.setObjectName("colhead")
        head.addWidget(h_perso, 3)
        for t in ("ACTIVÉ", "FOCUS COMBAT", "FOCUS ÉCHANGE", "AUTO-SKIP"):
            l = QLabel(t); l.setObjectName("colhead"); l.setAlignment(Qt.AlignCenter)
            head.addWidget(l, 1)
        lay.addLayout(head)

        area = QScrollArea(); area.setWidgetResizable(True); area.setFrameShape(QScrollArea.NoFrame)
        area.setStyleSheet("QScrollArea{border:none; background:transparent;}"
                           "QScrollArea > QWidget > QWidget{background:transparent;}")
        inner = QWidget(); self.comptes_box = QVBoxLayout(inner)
        self.comptes_box.setContentsMargins(0, 0, 0, 0)
        self.comptes_box.setSpacing(6)
        area.setWidget(inner)
        lay.addWidget(area)
        self._refresh_comptes()
        return w

    def _refresh_comptes(self):
        if not hasattr(self, "comptes_box"):
            return
        # garantit que le JSON contient les cles par defaut (synchro avec l'affichage)
        _changed = False
        for win in self.windows:
            e = self.cfg["chars"].setdefault(win["title"], {})
            for k, dv in (("focus_combat", 1), ("focus_echange", 1), ("skip", 0)):
                if k not in e:
                    e[k] = dv
                    _changed = True
        if _changed:
            config.save(self.cfg)
        while self.comptes_box.count():
            it = self.comptes_box.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        for win in self.windows:
            title = win["title"]
            e = self.cfg["chars"].setdefault(title, {})
            disabled = bool(e.get("disabled"))

            row = QWidget(); row.setObjectName("acctrow")
            row.setAttribute(Qt.WA_StyledBackground, True)
            rl = QHBoxLayout(row); rl.setContentsMargins(12, 7, 12, 7); rl.setSpacing(0)

            name = QLabel(self._overlay_name(win))
            if disabled:
                name.setObjectName("strike")
            else:
                name.setStyleSheet("background:transparent; font-weight:500;")
            rl.addWidget(name, 3)

            def mk(flag, default=1):
                cb = QCheckBox()
                cb.setChecked(bool(e.get(flag, default)))
                cb.setCursor(Qt.PointingHandCursor)
                def on_state(_=None, t=title, f=flag, box=cb):
                    self.cfg["chars"].setdefault(t, {})[f] = 1 if box.isChecked() else 0
                    config.save(self.cfg)
                    self._ov_items = None
                    self.refresh_views()
                cb.stateChanged.connect(on_state)
                return cb

            c_active = QCheckBox(); c_active.setChecked(not disabled)
            c_active.setCursor(Qt.PointingHandCursor)
            def on_active(_=None, t=title, box=c_active):
                self.cfg["chars"].setdefault(t, {})["disabled"] = 0 if box.isChecked() else 1
                config.save(self.cfg); self._ov_items = None; self.refresh_views()
            c_active.stateChanged.connect(on_active)

            for cb in (c_active, mk("focus_combat"), mk("focus_echange"), mk("skip", 0)):
                holder = QWidget(); holder.setStyleSheet("background:transparent;")
                hl = QHBoxLayout(holder); hl.setContentsMargins(0, 0, 0, 0)
                hl.addStretch(); hl.addWidget(cb); hl.addStretch()   # centre la case dans sa colonne
                rl.addWidget(holder, 1)
            self.comptes_box.addWidget(row)
        self.comptes_box.addStretch()
