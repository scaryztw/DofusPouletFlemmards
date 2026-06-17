from .ui_base import *
from .ui_base import _tray_log
from . import config


class TabParametresMixin:
    def _tab_parametres(self):
        from PySide6.QtWidgets import QScrollArea
        outer = QWidget()
        outer_lay = QVBoxLayout(outer); outer_lay.setContentsMargins(0, 0, 0, 0)
        area = QScrollArea(); area.setWidgetResizable(True); area.setFrameShape(QScrollArea.NoFrame)
        area.setStyleSheet("QScrollArea{border:none; background:transparent;}"
                           "QScrollArea > QWidget > QWidget{background:transparent;}")
        host = QWidget(); lay = QVBoxLayout(host); lay.setSpacing(12)
        area.setWidget(host)
        outer_lay.addWidget(area)

        # ---- Carte : Affichage / general ----
        c, v = self._card("Affichage", "Réglages generaux d'affichage et de comportement au lancement.")
        self.chk_banner = QCheckBox("Supprimer la bannière dès son apparition")
        self.chk_banner.setChecked(bool(self.cfg.get("remove_banner", True)))
        self.chk_banner.stateChanged.connect(self._apply_remove_banner)
        r1 = QHBoxLayout(); r1.setSpacing(5); r1.addWidget(self.chk_banner)
        r1.addWidget(self._help("Ferme immédiatement la notification Windows (toast) des qu'elle apparaît, "
                                "pour ne pas gener l'écran. DPF la lit avant de la supprimer.")); r1.addStretch()
        v.addLayout(r1)
        self.chk_maximize = QCheckBox("Agrandir les fenêtres de Dofus au lancement")
        self.chk_maximize.setChecked(bool(self.cfg.get("maximize_on_launch", False)))
        r2 = QHBoxLayout(); r2.setSpacing(5); r2.addWidget(self.chk_maximize)
        r2.addWidget(self._help("Met chaque nouvelle fenêtre Dofus détectée en plein écran automatiquement.")); r2.addStretch()
        v.addLayout(r2)
        self.chk_overlay = QCheckBox("Afficher l'overlay")
        self.chk_overlay.setChecked(bool(self.cfg.get("overlay", True)))
        r3 = QHBoxLayout(); r3.setSpacing(5); r3.addWidget(self.chk_overlay)
        r3.addWidget(self._help("Affiche le petit panneau flottant par-dessus Dofus (liste des persos, "
                                "AutoSkip, AutoFocus, chrono). Visible uniquement au-dessus de Dofus/DPF.")); r3.addStretch()
        v.addLayout(r3)
        # Garder DPF au-dessus (pratique pour régler les positions sur 1 écran / portable)
        self.chk_on_top = QCheckBox("Garder DPF au-dessus de Dofus")
        self.chk_on_top.setChecked(bool(self.cfg.get("always_on_top", True)))
        self.chk_on_top.stateChanged.connect(lambda s: self.set_always_on_top(bool(s)))
        r4 = QHBoxLayout(); r4.setSpacing(5); r4.addWidget(self.chk_on_top)
        r4.addWidget(self._help("DPF reste épinglé au-dessus de Dofus (comme l'overlay). "
                                "Pratique pour capturer les positions sur un seul écran ou un PC portable.")); r4.addStretch()
        v.addLayout(r4)
        # Croix -> tray au lieu de quitter
        self.chk_close_tray = QCheckBox("Réduire dans la zone de notification au lieu de fermer")
        self.chk_close_tray.setChecked(bool(self.cfg.get("close_to_tray", False)))
        self.chk_close_tray.stateChanged.connect(lambda s: self._save_flag("close_to_tray", bool(s)))
        r5 = QHBoxLayout(); r5.setSpacing(5); r5.addWidget(self.chk_close_tray)
        r5.addWidget(self._help("Si coché, cliquer sur la croix (X) ne ferme pas DPF : il se réduit dans "
                                "la zone de notification. Pour quitter vraiment : clic droit sur l'icône → Quitter.")); r5.addStretch()
        v.addLayout(r5)
        # Réduire -> tray au lieu de la barre des tâches
        self.chk_min_tray = QCheckBox("Réduire dans la zone de notification au lieu de minimiser")
        self.chk_min_tray.setChecked(bool(self.cfg.get("minimize_to_tray", False)))
        self.chk_min_tray.stateChanged.connect(lambda s: self._save_flag("minimize_to_tray", bool(s)))
        r6 = QHBoxLayout(); r6.setSpacing(5); r6.addWidget(self.chk_min_tray)
        r6.addWidget(self._help("Si coché, réduire DPF l'envoie dans la zone de notification. "
                                "Si décoché, il se réduit normalement dans la barre des tâches.")); r6.addStretch()
        v.addLayout(r6)
        # Taille de l'overlay (curseur)
        rsc = QHBoxLayout(); rsc.setSpacing(8)
        self.lbl_ovscale = QLabel()
        self.sld_ovscale = QSlider(Qt.Horizontal)
        self.sld_ovscale.setMinimum(70); self.sld_ovscale.setMaximum(180); self.sld_ovscale.setFixedWidth(180)
        self.sld_ovscale.setValue(int(round(float(self.cfg.get("overlay_scale", 1.0)) * 100)))
        self._update_ovscale_label(self.sld_ovscale.value())
        self.sld_ovscale.valueChanged.connect(self._on_overlay_scale_change)
        rsc.addWidget(QLabel("Taille de l'overlay")); rsc.addWidget(self.sld_ovscale); rsc.addWidget(self.lbl_ovscale)
        rsc.addWidget(self._help("Agrandit ou réduit le panneau flottant (l'overlay) par-dessus Dofus. "
                                 "70 % = compact, 180 % = grand. L'aperçu est en direct.")); rsc.addStretch()
        v.addLayout(rsc)
        lay.addWidget(c)
        c, v = self._card("Mode déplacement",
                          "Le mode déplacement permet de simuler le raccourci \"page suivante\" lors de chaque clic "
                          "gauche de votre souris. Ceci améliore votre accessibilité a déplacer votre team à une "
                          "seule main. Ce mode peut être activé grâce à un raccourci clavier (on/off) et dispose "
                          "d'un overlay pour vous avertir lorsque le mode est actif. Vous pouvez définir le nombre "
                          "de ms pour le changement de page. D'après mes tests, un ms de 90 est le minimum possible "
                          "pour éviter les bugs.")
        g = QGridLayout(); g.setHorizontalSpacing(8); g.setVerticalSpacing(8)
        g.addWidget(self._field_label("Raccourcis (toggle)"), 0, 0)
        self.move_key = self._mk_hotkey(self.cfg.get("hotkey_move_mode", "ctrl+z")); g.addWidget(self.move_key, 0, 1)
        g.addWidget(self._field_label("Délai (ms)", "Temps d'attente entre le clic et le passage au perso suivant (90 ms minimum conseillé)."), 0, 2)
        self.move_delay = QLineEdit(str(self.cfg.get("move_delay_ms", 95))); self.move_delay.setFixedWidth(80)
        g.addWidget(self.move_delay, 0, 3)
        v.addLayout(g); lay.addWidget(c)

        # ---- Carte : Auto Click ----
        c, v = self._card("Auto Click",
                          "Le mode Auto Click permet de faire déplacer tous tes personnages, rejoindre des combats, "
                          "parler aux PNJ pour rentrer dans les donjons.")
        g = QGridLayout(); g.setHorizontalSpacing(8); g.setVerticalSpacing(8)
        g.addWidget(self._field_label("Raccourcis"), 0, 0)
        self.join_key = self._mk_hotkey(self.cfg.get("hotkey_join", "ctrl+j")); g.addWidget(self.join_key, 0, 1)
        g.addWidget(self._field_label("Délai (ms)", "Temps d'attente entre chaque fenêtre."), 0, 2)
        self.join_delay = QLineEdit(str(self.cfg.get("join_delay_ms", 100))); self.join_delay.setFixedWidth(80)
        g.addWidget(self.join_delay, 0, 3)
        v.addLayout(g); lay.addWidget(c)

        # ---- Carte : Invite groupe ----
        c, v = self._card("Invite de groupe",
                          "Invite tous tes personnages avec une touche. L'acceptation du popup Oui/Non se fait "
                          "automatiquement par détection à l'écran (aucune position à régler). Règle les délais "
                          "si ça va trop vite ou trop lentement, mais reste le plus legit possible.")
        g = QGridLayout(); g.setHorizontalSpacing(8); g.setVerticalSpacing(8)
        g.addWidget(self._field_label("Raccourcis"), 0, 0)
        self.invite_key = self._mk_hotkey(self.cfg.get("hotkey_invite", "ctrl+i")); g.addWidget(self.invite_key, 0, 1)
        g.addWidget(self._field_label("Délai invite (ms)", "Pause entre chaque frappe (/invite, Entrée)."), 0, 2)
        self.invite_delay = QLineEdit(str(self.cfg.get("invite_delay_ms", 120))); self.invite_delay.setFixedWidth(80)
        g.addWidget(self.invite_delay, 0, 3)
        g.addWidget(self._field_label("Délai accept. (ms)",
                                      "Temps d'attente du popup Oui/Non sur un perso avant de passer au suivant. "
                                      "Augmente si les popups tardent à s'afficher."), 1, 2)
        self.invite_accept_delay = QLineEdit(str(self.cfg.get("invite_accept_delay_ms", 450))); self.invite_accept_delay.setFixedWidth(80)
        g.addWidget(self.invite_accept_delay, 1, 3)
        # Position du bouton « Accepter » de l'invitation (clic sur position enregistrée)
        g.addWidget(self._field_label("Position Accepter",
                                      "Position du bouton « Accepter » de l'invitation. Capture-la une fois "
                                      "(tes fenêtres doivent être empilées au même endroit à l'écran)."), 2, 0)
        self.invite_accept_lbl = QLabel(self._invite_pos_text())
        g.addWidget(self.invite_accept_lbl, 2, 1)
        b_iacap = QPushButton("Capturer"); b_iacap.clicked.connect(lambda: self.capture("invite_accept"))
        g.addWidget(b_iacap, 2, 2)
        v.addLayout(g); lay.addWidget(c)

        # ---- Carte : Farm Arene ----
        c, v = self._card("Farm Arène",
                          "Le mode Farm Arène permet de faire placer le personnage qui lance le combat, faire "
                          "rejoindre ensuite tes personnages, puis mettre Prêt sur tous tes comptes. "
                          "N'OUBLIE PAS DE REPLACER UNIQUEMENT LA POSITION REJOINDRE QUAND TU CHANGE DE PLACE DANS L'ARÈNE.")
        g = QGridLayout(); g.setHorizontalSpacing(8); g.setVerticalSpacing(8)
        g.addWidget(self._field_label("Raccourcis"), 0, 0)
        self.cj_key = self._mk_hotkey(self.cfg.get("hotkey_custom_join", "")); g.addWidget(self.cj_key, 0, 1)
        g.addWidget(self._field_label("Délai (ms)", "Pause entre chaque clic de la séquence."), 0, 2)
        self.cj_delay = QLineEdit(str(self.cfg.get("custom_join_delay_ms", 100))); self.cj_delay.setFixedWidth(80)
        g.addWidget(self.cj_delay, 0, 3)
        b_cj3 = QPushButton("Capturer Placement (étape 1, meneur)"); b_cj3.clicked.connect(lambda: self.capture("cj3"))
        b_cj1 = QPushButton("Capturer Rejoindre (étape 2)"); b_cj1.clicked.connect(lambda: self.capture("cj1"))
        b_cj2 = QPushButton("Capturer Prêt (étape 3, option)"); b_cj2.clicked.connect(lambda: self.capture("cj2"))
        g.addWidget(b_cj3, 1, 0, 1, 2); g.addWidget(b_cj1, 1, 2, 1, 2); g.addWidget(b_cj2, 2, 0, 1, 2)
        self.cj_lbl = QLabel(self._cj_pos_text()); self.cj_lbl.setObjectName("muted")
        g.addWidget(self.cj_lbl, 3, 0, 1, 4)
        v.addLayout(g); lay.addWidget(c)

        # ---- Carte : AutoSkip / AutoFocus ----
        c, v = self._card("AutoSkip / AutoFocus",
                          "AutoFocus (bleu) : DPF bascule tout seul sur le perso dont c'est le tour / qui reçoit un échange. "
                          "AutoSkip (jaune) : passe automatiquement le tour des persos cochés. Les bascules ON/OFF "
                          "et les choix par perso se font sur l'overlay.")
        g = QGridLayout(); g.setHorizontalSpacing(8); g.setVerticalSpacing(8)
        g.addWidget(self._field_label("AutoSkip ON/OFF (raccourci)", "Raccourci pour activer/couper l'AutoSkip global."), 0, 0)
        self.askip_key = self._mk_hotkey(self.cfg.get("hotkey_autoskip", "")); g.addWidget(self.askip_key, 0, 1)
        g.addWidget(self._field_label("AutoFocus ON/OFF (raccourci)", "Raccourci pour activer/couper l'AutoFocus global."), 0, 2)
        self.afocus_key = self._mk_hotkey(self.cfg.get("hotkey_autofocus", "")); g.addWidget(self.afocus_key, 0, 3)
        g.addWidget(self._field_label("Touche 'passer le tour'", "Touche envoyée au perso pour passer son tour (ex. 's')."), 1, 0)
        self.skip_key = QLineEdit(self.cfg.get("skip_key", "s")); self.skip_key.setFixedWidth(60); g.addWidget(self.skip_key, 1, 1)
        g.addWidget(self._field_label("Délai skip (ms)", "Pause après la bascule avant d'envoyer la touche de passage."), 1, 2)
        self.skip_delay = QLineEdit(str(self.cfg.get("skip_delay_ms", 120))); self.skip_delay.setFixedWidth(80); g.addWidget(self.skip_delay, 1, 3)
        v.addLayout(g); lay.addWidget(c)

        # ---- Carte : Configuration & mises à jour ----
        c, v = self._card("Configuration & mises à jour",
                          "Sauvegarde tes réglages, restaure-les, et vérifie si une nouvelle version existe.")
        rowc = QHBoxLayout(); rowc.setSpacing(8)
        b_exp = QPushButton("Exporter la config"); b_exp.clicked.connect(self.export_config)
        b_imp = QPushButton("Importer la config"); b_imp.clicked.connect(self.import_config)
        b_upd = QPushButton("Vérifier les mises à jour"); b_upd.clicked.connect(lambda: self.check_update(manual=True))
        rowc.addWidget(b_exp); rowc.addWidget(b_imp); rowc.addWidget(b_upd); rowc.addStretch()
        v.addLayout(rowc)
        rowv = QHBoxLayout(); rowv.setSpacing(5)
        ver = QLabel("Version installée : v%s" % config.VERSION); ver.setObjectName("muted"); ver.setWordWrap(False)
        rowv.addWidget(ver)
        rowv.addWidget(self._help("« Exporter » écrit tes réglages (positions, macros, presets, raccourcis) "
                                  "dans un fichier .json que tu peux sauvegarder ou partager. "
                                  "« Importer » les recharge (redémarre DPF ensuite).")); rowv.addStretch()
        v.addLayout(rowv)
        lay.addWidget(c)

        # ---- Actions ----
        b_apply = QPushButton("Appliquer + Enregistrer"); b_apply.setObjectName("accent")
        b_apply.clicked.connect(self.apply_params)
        lay.addWidget(b_apply)
        rowb = QHBoxLayout()
        b_reload = QPushButton("Recharger DPF"); b_reload.clicked.connect(self.do_reload)
        b_exit = QPushButton("Quitter totalement DPF"); b_exit.clicked.connect(self.do_exit)
        b_guide = QPushButton("Revoir le guide"); b_guide.clicked.connect(self._show_welcome)
        rowb.addWidget(b_reload); rowb.addWidget(b_exit); rowb.addWidget(b_guide); rowb.addStretch()
        lay.addLayout(rowb)
        log_lbl = QLabel("Log notifications : dpf_notif_log.txt (dans le dossier DPF)")
        log_lbl.setObjectName("muted")
        lay.addWidget(log_lbl)
        lay.addStretch()
        return outer

    def _update_ovscale_label(self, v):
        if hasattr(self, "lbl_ovscale"):
            self.lbl_ovscale.setText("%d %%" % int(v))

    def _on_overlay_scale_change(self, v):
        self._update_ovscale_label(v)
        if hasattr(self, "overlay"):
            self.overlay.set_scale(v / 100.0)
        self.cfg["overlay_scale"] = round(v / 100.0, 2)
        config.save(self.cfg)

    def apply_params(self):
        self.cfg["remove_banner"] = self.chk_banner.isChecked()
        self.cfg["maximize_on_launch"] = self.chk_maximize.isChecked()
        self.cfg["overlay"] = self.chk_overlay.isChecked()
        self.cfg["hotkey_move_mode"] = self.move_key.value()
        try:
            self.cfg["move_delay_ms"] = max(0, int(self.move_delay.text()))
        except Exception:
            pass
        self.cfg["hotkey_join"] = self.join_key.value()
        try:
            self.cfg["join_delay_ms"] = max(0, int(self.join_delay.text()))
        except Exception:
            pass
        self.cfg["hotkey_custom_join"] = self.cj_key.value()
        try:
            self.cfg["custom_join_delay_ms"] = max(0, int(self.cj_delay.text()))
        except Exception:
            pass
        if hasattr(self, "askip_key"):
            self.cfg["hotkey_autoskip"] = self.askip_key.value()
            self.cfg["hotkey_autofocus"] = self.afocus_key.value()
            self.cfg["skip_key"] = (self.skip_key.text().strip() or "s")
            try:
                self.cfg["skip_delay_ms"] = max(0, int(self.skip_delay.text()))
            except Exception:
                pass
        self.cfg["hotkey_invite"] = self.invite_key.value()
        try:
            self.cfg["invite_delay_ms"] = max(0, int(self.invite_delay.text()))
        except Exception:
            pass
        try:
            self.cfg["invite_accept_delay_ms"] = max(0, int(self.invite_accept_delay.text()))
        except Exception:
            pass
        config.save(self.cfg)
        self.apply_hotkeys()
        self.overlay.setVisible(self.cfg["overlay"])
        # met juste a jour le réglage de bannière (pas de redemarrage du listener)
        try:
            self.notifier.set_remove_banner(self.cfg["remove_banner"])
        except Exception:
            pass
        self.status.setText("Paramètres appliqués.")

    def _cj_pos_text(self):
        def f(x, y):
            return "(%d, %d)" % (x, y) if (x or y) else "non définie"
        return "1. Placement %s   ->   2. Rejoindre %s   ->   3. Prêt %s" % (
            f(self.cfg.get("cj_x3", 0), self.cfg.get("cj_y3", 0)),
            f(self.cfg.get("cj_x1", 0), self.cfg.get("cj_y1", 0)),
            f(self.cfg.get("cj_x2", 0), self.cfg.get("cj_y2", 0)))

    def _invite_pos_text(self):
        x = self.cfg.get("invite_accept_x", 0); y = self.cfg.get("invite_accept_y", 0)
        if x or y:
            return "Position bouton Accepter : (%d, %d)" % (x, y)
        return "Position bouton Accepter : non définie (clic d'acceptation désactive)"

    def _apply_remove_banner(self):
        # applique IMMEDIATEMENT le toggle "Supprimer la banniere" au notifier en cours
        self.cfg["remove_banner"] = self.chk_banner.isChecked()
        config.save(self.cfg)
        try:
            self.notifier.set_remove_banner(self.cfg["remove_banner"])
        except Exception:
            pass

    def apply_raccourcis(self):
        for key, edit in self.hk.items():
            self.cfg[key] = edit.value()
        config.save(self.cfg)
        self.apply_hotkeys()
        self.status.setText("Raccourcis appliqués.")
