from .ui_base import *
from .ui_base import _tray_log


class TabPresetsMixin:
    def _tab_presets(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.addWidget(QLabel("Presets d'ordre des fenêtres. Crée un preset depuis l'onglet "
                             "Fenêtres, puis assigne-lui un raccourci ici pour le charger."))
        row = QHBoxLayout()
        row.addStretch()
        b_refresh = QPushButton("Rafraîchir")
        b_refresh.clicked.connect(self._refresh_presets_tab)
        row.addWidget(b_refresh)
        lay.addLayout(row)
        self.presets_box = QVBoxLayout()
        lay.addLayout(self.presets_box)
        lay.addStretch()
        self._refresh_presets_tab()
        return w

    def _refresh_presets_tab(self):
        if not hasattr(self, "presets_box"):
            return
        # retire les anciens boutons de raccourci de preset du registre (évite refs mortes)
        self._hk_buttons = [b for b in self._hk_buttons if not hasattr(b, "_preset_name")]
        while self.presets_box.count():
            it = self.presets_box.takeAt(0)
            lay = it.layout()
            if lay:
                while lay.count():
                    s = lay.takeAt(0)
                    if s.widget():
                        s.widget().deleteLater()
            elif it.widget():
                it.widget().deleteLater()
        for name in self.cfg.get("presets", {}):
            row = QHBoxLayout()
            lbl = QLabel(name); row.addWidget(lbl, 2)
            hk = self._mk_hotkey(self.cfg.get("preset_hotkeys", {}).get(name, ""))
            hk._preset_name = name
            row.addWidget(hk, 2)
            b_load = QPushButton("Charger"); b_load.clicked.connect(lambda _=False, n=name: self.load_preset_by_name(n))
            b_del = QPushButton("Supprimer"); b_del.clicked.connect(lambda _=False, n=name: self._preset_delete(n))
            row.addWidget(b_load); row.addWidget(b_del)
            self.presets_box.addLayout(row)

    def _preset_update(self, name):
        # ecrase le preset existant avec l'ordre actuel des fenetres
        self.cfg.setdefault("presets", {})[name] = [win["title"] for win in self.windows]
        config.save(self.cfg)
        self.status.setText("Preset '%s' mis à jour (%d persos)." % (name, len(self.windows)))

    def _preset_delete(self, name):
        self.cfg.get("presets", {}).pop(name, None)
        self.cfg.get("preset_hotkeys", {}).pop(name, None)
        config.save(self.cfg)
        if hasattr(self, "_refresh_presets"):
            self._refresh_presets()
        self._refresh_presets_tab()
        self.apply_hotkeys()
        self.status.setText("Preset '%s' supprimé." % name)
