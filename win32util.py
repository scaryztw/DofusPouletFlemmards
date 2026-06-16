from .ui_base import *
from .ui_base import _tray_log


class TabEchangeMixin:
    def _tab_trade(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        self.acc_x = QLineEdit(str(self.cfg["trade_accept_x"])); self.acc_x.setFixedWidth(70)
        self.acc_y = QLineEdit(str(self.cfg["trade_accept_y"])); self.acc_y.setFixedWidth(70)
        self.oui_x = QLineEdit(str(self.cfg.get("trade_popup_x", 0))); self.oui_x.setFixedWidth(70)
        self.oui_y = QLineEdit(str(self.cfg.get("trade_popup_y", 0))); self.oui_y.setFixedWidth(70)

        # Ligne 0 : popup « Oui » (acceptation de la DEMANDE d'échange)
        lbl_oui = QLabel("Position « Oui »")
        lbl_oui.setToolTip("Bouton « Oui » du popup « X te propose un échange. Acceptes-tu ? »,\n"
                           "tel qu'il apparaît sur la fenêtre du perso qui REÇOIT la demande.")
        grid.addWidget(lbl_oui, 0, 0)
        grid.addWidget(self.oui_x, 0, 1); grid.addWidget(self.oui_y, 0, 2)
        cap_oui = QPushButton("Capturer"); cap_oui.clicked.connect(lambda: self.capture("oui"))
        grid.addWidget(cap_oui, 0, 3)

        # Ligne 1 : bouton « Accepter » (VALIDATION finale, une fois les objets posés)
        lbl_acc = QLabel("Position « Accepter »")
        lbl_acc.setToolTip("Bouton « Accepter » qui VALIDE l'échange une fois les objets déposés.\n"
                           "Utilisé par la validation auto et la touche de validation.")
        grid.addWidget(lbl_acc, 1, 0)
        grid.addWidget(self.acc_x, 1, 1); grid.addWidget(self.acc_y, 1, 2)
        cap2 = QPushButton("Capturer"); cap2.clicked.connect(lambda: self.capture("accept"))
        grid.addWidget(cap2, 1, 3)
        lay.addLayout(grid)
        lay.addWidget(self._note(
            "• « Capturer » : survole le bouton dans le jeu, puis clique pour mémoriser sa position.\n"
            "• Les fenêtres doivent être empilées au même endroit (les positions sont partagées "
            "entre tous les persos)."))

        self.chk_auto = QCheckBox("Validation auto (valide B quand tu valides A)")
        self.chk_auto.setChecked(bool(self.cfg.get("auto_validate")))
        self.chk_auto.stateChanged.connect(self.save_trade)
        lay.addWidget(self.chk_auto)

        btn_test = QPushButton("Tester le clic sur la fenêtre sélectionnée (onglet Fenêtres)")
        btn_test.clicked.connect(self.test_click)
        lay.addWidget(btn_test)

        save = QPushButton("Enregistrer les positions"); save.setObjectName("accent")
        save.clicked.connect(self.save_trade)
        lay.addWidget(save)

        # ---------------- AutoTrade par image (~0 % CPU) ----------------
        sep = QLabel("AutoTrade par image")
        sep.setStyleSheet("font-weight:700; margin-top:10px;")
        lay.addWidget(sep)
        lay.addWidget(self._note(
            "• Surveille une petite zone de l'écran et se déclenche dès qu'un échange arrive — "
            "sans dépendre des notifications (plus de bug sur les échanges répétés).\n"
            "• Bascule sur la fenêtre du receveur, clique ta Position « Oui » ci-dessus, "
            "puis revient au lanceur."))

        self.at_chk = QCheckBox("Activer A-Trade")
        self.at_chk.setChecked(bool(self.cfg.get("autotrade")))
        self.at_chk.setToolTip("Identique au bouton A-Trade de l'overlay.")
        self.at_chk.stateChanged.connect(self._at_checkbox_changed)
        lay.addWidget(self.at_chk)

        hk = QHBoxLayout()
        hk.addWidget(QLabel("Raccourci A-Trade"))
        self.hk_autotrade = self._mk_hotkey(self.cfg.get("autotrade_hotkey", ""))
        self.hk_autotrade.setToolTip("Touche pour activer/couper A-Trade (comme le bouton de l'overlay).")
        hk.addWidget(self.hk_autotrade); hk.addStretch()
        lay.addLayout(hk)

        g = QGridLayout(); g.setHorizontalSpacing(8)
        self.at_name_lbl = QLabel()
        g.addWidget(QLabel("Zone du nom"), 0, 0)
        g.addWidget(self.at_name_lbl, 0, 1)
        b_sel = QPushButton("Sélectionner la zone (glisser)")
        b_sel.clicked.connect(self._at_select_zone)
        g.addWidget(b_sel, 0, 2, 1, 2)
        lay.addLayout(g)
        lay.addWidget(self._note(
            "• Clique « Sélectionner la zone », puis maintiens le clic et glisse pour entourer le "
            "texte du popup « En attente de la réponse de <pseudo> » (Échap pour annuler).\n"
            "• Tu peux entourer toute la ligne de texte : prends large, c'est plus fiable."))

        rt = QHBoxLayout()
        self.at_tmpl_lbl = QLabel()
        b_reload = QPushButton("Recharger les pseudos"); b_reload.clicked.connect(self._at_reload_templates)
        b_folder = QPushButton("Ouvrir le dossier"); b_folder.clicked.connect(self._at_open_folder)
        b_diag = QPushButton("Diagnostic A-Trade"); b_diag.clicked.connect(self._at_diagnose)
        b_diag.setToolTip("À cliquer PENDANT un échange (pop-up affichée) : écrit dans l'onglet "
                          "Debug ce que voit chaque étape (zone du nom, scores de match).")
        rt.addWidget(self.at_tmpl_lbl); rt.addWidget(b_reload); rt.addWidget(b_folder); rt.addWidget(b_diag); rt.addStretch()
        lay.addLayout(rt)
        lay.addWidget(self._note(
            "• Place un fichier <pseudo>.png par perso dans le dossier SCREENSHOT-ECHANGE.\n"
            "• « Recharger les pseudos » : relit les fichiers.\n"
            "• « Ouvrir le dossier » : ouvre SCREENSHOT-ECHANGE.\n"
            "• « Diagnostic A-Trade » : pendant un échange, écrit dans l'onglet Debug ce que DPF "
            "voit (zone du nom + score de chaque pseudo)."))

        self._at_sync_labels()
        lay.addStretch()
        return w

    def _note(self, text):
        l = QLabel(text)
        l.setWordWrap(True)
        l.setStyleSheet("color:#8a93a3; font-size:11px;")
        return l

    def _at_checkbox_changed(self, *_):
        want = self.at_chk.isChecked()
        if want != bool(self.cfg.get("autotrade")):
            self.toggle_autotrade()

    def _at_select_zone(self):
        def done(x1, y1, x2, y2):
            self.cfg["at_name_x1"] = x1; self.cfg["at_name_y1"] = y1
            self.cfg["at_name_x2"] = x2; self.cfg["at_name_y2"] = y2
            config.save(self.cfg)
            self._at_sync_labels()
            self.status.setText("Zone du nom : (%d,%d) → (%d,%d)" % (x1, y1, x2, y2))
        self._region_selector = RegionSelector(done)   # garde une réf (sinon GC)

    def _at_pos_count(self):
        import os
        d = self._autotrade_dir()
        try:
            return len([f for f in os.listdir(d) if f.lower().endswith(".png")])
        except Exception:
            return 0

    def _at_open_folder(self):
        d = self._autotrade_dir()
        try:
            os.startfile(d)   # Windows
        except Exception:
            self.status.setText("Dossier : %s" % d)

    def _at_sync_labels(self):
        if not hasattr(self, "at_name_lbl"):
            return
        c = self.cfg
        self.at_name_lbl.setText("(%d,%d) → (%d,%d)" % (c.get("at_name_x1", 0), c.get("at_name_y1", 0),
                                                        c.get("at_name_x2", 0), c.get("at_name_y2", 0)))
        self.at_tmpl_lbl.setText("%d pseudo(s) dans SCREENSHOT-ECHANGE" % self._at_pos_count())
        if hasattr(self, "at_chk"):
            self.at_chk.blockSignals(True)
            self.at_chk.setChecked(bool(c.get("autotrade")))
            self.at_chk.blockSignals(False)

    def test_click(self):
        r = self.list.currentRow()
        if r < 0 or r >= len(self.windows):
            self.status.setText("Sélectionne d'abord une fenêtre dans l'onglet Fenêtres.")
            return
        self.save_trade()
        win = self.windows[r]
        cx, cy = self._to_client(win["hwnd"], self.cfg["trade_accept_x"], self.cfg["trade_accept_y"])
        win32util.background_click(win["hwnd"], cx, cy)
        self.status.setText("Clic envoyé à %s en client (%d, %d) — sans changer de fenêtre."
                            % (self.name_of(win), cx, cy))

    def validate_trade(self):
        if not self.last_trade_hwnd or not win32util.window_alive(self.last_trade_hwnd):
            return
        cx, cy = self._to_client(self.last_trade_hwnd,
                                 self.cfg["trade_accept_x"], self.cfg["trade_accept_y"])
        win32util.background_click(self.last_trade_hwnd, cx, cy)
        self.status.setText("Échange validé (touche).")

    def _to_client(self, hwnd, sx, sy):
        # la position est capturee en coords ECRAN (GetCursorPos) ; background_click
        # (PostMessage) attend des coords CLIENT -> on convertit, sinon le clic tombe
        # a cote des que la fenetre n'est pas a l'origine de l'ecran.
        try:
            return win32gui.ScreenToClient(hwnd, (int(sx), int(sy)))
        except Exception:
            return int(sx), int(sy)

    def save_trade(self):
        self.cfg["trade_accept_x"] = self._int(self.acc_x)
        self.cfg["trade_accept_y"] = self._int(self.acc_y)
        if hasattr(self, "oui_x"):
            self.cfg["trade_popup_x"] = self._int(self.oui_x)
            self.cfg["trade_popup_y"] = self._int(self.oui_y)
        self.cfg["auto_validate"] = self.chk_auto.isChecked()
        if hasattr(self, "chk_only_mine"):
            self.cfg["accept_only_mine"] = self.chk_only_mine.isChecked()
        config.save(self.cfg)
        if hasattr(self, "status"):
            self.status.setText("Positions d'échange enregistrées.")
