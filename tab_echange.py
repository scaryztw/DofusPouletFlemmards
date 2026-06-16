"""Application principale DPF (PySide6) — fenetre + cablage.
Les onglets sont definis dans les mixins tab_*.py (style modulaire).
"""
from .ui_base import *
from .ui_base import _tray_log
from ._credit import credit as _credit


from .tab_fenetres import TabFenetresMixin
from .tab_comptes import TabComptesMixin
from .tab_presets import TabPresetsMixin
from .tab_echange import TabEchangeMixin
from .tab_actions import TabActionsMixin
from .tab_messages import TabMessagesMixin
from .tab_raccourcis import TabRaccourcisMixin
from .tab_debug import TabDebugMixin
from .tab_parametres import TabParametresMixin

from . import trade_detect
from . import ocr_util
try:
    import keyboard
except Exception:
    keyboard = None


class MainWindow(TabFenetresMixin, TabComptesMixin, TabPresetsMixin, TabEchangeMixin, TabActionsMixin, TabMessagesMixin, TabRaccourcisMixin, TabDebugMixin, TabParametresMixin, QWidget):
    # remonte n'importe quel probleme detecte (thread-safe) vers l'onglet Debug
    problemSig = Signal(str, str)
    # met à jour la barre de statut du bas depuis n'importe quel thread
    statusSig = Signal(str)

    def __init__(self):
        super().__init__()
        win32util.disable_foreground_lock()   # active -> switch combat fiable (pas 1/2)
        self.cfg = config.load()
        # Pré-crée 3 macros prêtes à remplir (une seule fois) : elles apparaissent
        # dans l'onglet Actions, il ne reste qu'à capturer les positions + la touche.
        if not self.cfg.get("_seeded_actions"):
            self.cfg.setdefault("actions", [])
            existing = {a.get("name") for a in self.cfg["actions"]}
            seeds = [
                {"name": "Prêt (combat)",   "clicks": 1, "delay_ms": 120},
                {"name": "Potion de rappel", "clicks": 2, "delay_ms": 120},
                {"name": "Reconnexion",     "clicks": 1, "delay_ms": 150},
            ]
            for s in seeds:
                if s["name"] not in existing:
                    self.cfg["actions"].append(
                        {"name": s["name"], "positions": [], "clicks": s["clicks"],
                         "delay_ms": s["delay_ms"], "hotkey": "", "target": "all",
                         "bg": True, "auto": False, "interval_s": 30})
            self.cfg["_seeded_actions"] = True
            config.save(self.cfg)
        self.windows = []          # liste ordonnee de {hwnd,title,pid,exe}
        self.idx = -1
        self.last_trade_hwnd = 0
        self.last_trade_tick = 0.0
        self._capture_target = None
        self.prev_hwnd = 0
        self._cur_fg = 0
        self._accept_lock = threading.Lock()
        self._notif_cooldown = {}
        self.move_mode = False
        self._trade_scanning = False
        self._poll_pause_until = 0.0
        self._last_move_ts = 0.0
        self._ov_char = ""
        self._timer_running = False
        self._timer_elapsed = 0.0
        self._timer_start = 0.0
        self._hk_buttons = []

        self.setObjectName("root")
        self.setWindowTitle("DofusPouletFlemmards v%s" % config.VERSION)
        try:
            self.setWindowIcon(QIcon(ICON_PATH))
        except Exception:
            pass
        self.resize(880, 720)
        self.setMinimumSize(820, 600)

        self.inputs = Inputs(self)
        self.notifier = Notifier(self)
        self.overlay = Overlay()
        self.overlay.on_autoskip = self.toggle_autoskip
        self.overlay.on_autofocus = self.toggle_autofocus
        self.overlay.on_toggle_skip = self._overlay_toggle_skip
        self.overlay.on_toggle_enable = self._overlay_toggle_enable
        self.overlay.on_toggle_combat = self._overlay_toggle_combat
        self.overlay.on_toggle_echange = self._overlay_toggle_echange
        self.overlay.on_moved = self._overlay_moved
        self.overlay.on_focus = self._overlay_focus
        self.overlay.on_toggle_window = self._toggle_window_visibility
        self.overlay.on_toggle_trade = self.toggle_autotrade
        try:
            self.overlay.set_scale(self.cfg.get("overlay_scale", 1.0))
        except Exception:
            import traceback
            traceback.print_exc()
        ox, oy = self.cfg.get("overlay_x"), self.cfg.get("overlay_y")
        if isinstance(ox, int) and isinstance(oy, int):
            self.overlay.move(ox, oy)

        self._build_ui()
        self.detect()

        # câblage entrees
        self.inputs.nextSig.connect(self.go_next)
        self.inputs.prevSig.connect(self.go_prev)
        self.inputs.backSig.connect(self.go_back)
        self.inputs.mainSig.connect(self.go_main)
        self.inputs.validateSig.connect(self.validate_trade)
        self.inputs.actionSig.connect(self.run_action)
        self.inputs.messageSig.connect(self.send_message)
        self.inputs.moveModeSig.connect(self.toggle_move_mode)
        self.inputs.joinSig.connect(self.do_join)
        self.inputs.customJoinSig.connect(self.do_custom_join)
        self.inputs.autoskipSig.connect(self.toggle_autoskip)
        self.inputs.autofocusSig.connect(self.toggle_autofocus)
        self.inputs.presetSig.connect(self.load_preset_by_name)
        self.inputs.inviteSig.connect(self.do_invite)
        self.inputs.timerSig.connect(self.timer_toggle)
        self.inputs.timerResetSig.connect(self.timer_reset)
        self.inputs.ctrlShiftSig.connect(self.do_ctrlshift_toggle)
        self.inputs.overlaySig.connect(self.toggle_overlay)
        self.inputs.tradeSig.connect(self.toggle_autotrade)
        self._ctrlshift_held = False
        self.notifier.event.connect(self.on_notif)
        # remontee des problemes vers l'onglet Debug (thread-safe via signaux)
        self.problemSig.connect(self._on_problem)
        self.statusSig.connect(lambda m: self.status.setText(m[:140]))
        self.notifier.problem.connect(self._on_problem)
        self._install_excepthooks()

        self.apply_hotkeys()
        self.notifier.start(self.cfg.get("remove_banner", True))

        # détection globale des clics gauche (capture de position + validation auto)
        self._lbtn = False
        self._click_timer = QTimer(self)
        self._click_timer.timeout.connect(self._poll_click)
        self._click_timer.start(40)

        # mise a jour du chrono overlay
        self._ov_timer = QTimer(self)
        self._ov_timer.timeout.connect(self._refresh_overlay)
        self._ov_timer.start(150)
        if self.cfg.get("overlay"):
            self.overlay.show()

        # rafraichissement doux
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.detect)
        self._timer.start(2500)

        # AutoTrade par image (~0 % CPU) : gate couleur + match numpy en thread
        self._init_autotrade()

        # AutoTrade par DETECTION PIXEL (capture arriere-plan + clic Accepter).
        # Remplace l'acceptation via notification (contourne le dedup Windows des toasts).
        self._trade_timer = QTimer(self)
        self._trade_timer.timeout.connect(self._poll_trades)
        self._trade_last_seen = 0.0          # cadence adaptative du sweep
        # SWEEP ORANGE DÉSACTIVÉ : l'échange est désormais déclenché par NOTIFICATION
        # (on_notif -> clic sur la position enregistrée). Plus de scan pixel des boutons
        # orange -> plus de faux clic sur « Prêt » en combat. (Timer volontairement non démarré.)
        # self._trade_timer.start(1000)

        self._force_quit = False
        self._setup_tray()
        self._dpf_topmost = None   # état topmost dynamique de la fenêtre DPF (suit Dofus)

        # auto-envoi des messages (case "Auto" dans l'onglet Messages)
        self._msg_last = [0.0, 0.0, 0.0]
        self._act_last = {}                  # repetition auto des macros (onglet Actions)
        self._act_auto_on = set()            # indices des macros dont la repetition est ACTIVE
        # récap de session (onglet Debug)
        self._stats = {"turns": 0, "combats": 0, "session_start": time.time(),
                       "last_turn": 0.0, "per_char": {}}
        self._msg_timer = QTimer(self)
        self._msg_timer.timeout.connect(self._auto_messages_tick)
        self._msg_timer.timeout.connect(self._auto_actions_tick)
        self._msg_timer.start(1000)

        # Popup de bienvenue au premier lancement
        if not self.cfg.get("welcome_shown", False):
            QTimer.singleShot(350, self._show_welcome)

        # Vérif de mise à jour au démarrage (silencieuse ; ne dit rien si DPF est à jour)
        QTimer.singleShot(2500, lambda: self.check_update(manual=False))

        # Corrige le bug d'affichage au lancement (fenêtre rendue trop petite / champs non
        # peints tant qu'on ne l'a pas bougée).
        QTimer.singleShot(0, self._fix_startup_geometry)
        QTimer.singleShot(150, self._repaint_all)

    def _repaint_all(self):
        try:
            self.update()
            cw = self.centralWidget()
            if cw is not None:
                cw.update()
        except Exception:
            pass

    def _fix_startup_geometry(self):
        # Au lancement, Qt rendait parfois la fenêtre à une mauvaise taille AVEC les
        # champs/boutons non peints (corrigé seulement par un déplacement). On force ici
        # un vrai relayout + repaint via un léger « wiggle » de géométrie.
        try:
            hint = self.sizeHint()
            w = max(880, hint.width())
            h = max(720, hint.height())        # jamais sous la taille reelle du contenu
            scr = QGuiApplication.primaryScreen().availableGeometry()
            x = scr.x() + max(0, (scr.width() - w) // 2)
            y = scr.y() + max(0, (scr.height() - h) // 2)
            self.setGeometry(x, y, w, h + 1)   # taille volontairement différente...
            self.setGeometry(x, y, w, h)       # ...puis la bonne -> force un resize event
            lay = self.layout()
            if lay is not None:
                lay.activate()
            self.update()
        except Exception:
            try:
                self.resize(880, 760)
            except Exception:
                pass

    def _setup_tray(self):
        from PySide6.QtWidgets import QSystemTrayIcon, QMenu
        from PySide6.QtGui import QPixmap
        self.tray = None
        try:
            if not QSystemTrayIcon.isSystemTrayAvailable():
                _tray_log("Barre système indisponible.")
                return
            ico = QIcon(ICON_PATH) if os.path.exists(ICON_PATH) else self.windowIcon()
            if ico is None or ico.isNull():
                pm = QPixmap(32, 32)
                pm.fill(Qt.transparent)
                from PySide6.QtGui import QPainter, QColor as _QC
                p = QPainter(pm)
                p.setBrush(_QC(ACCENT)); p.setPen(Qt.NoPen)
                p.drawEllipse(4, 4, 24, 24); p.end()
                ico = QIcon(pm)
            self.setWindowIcon(ico)
            tray = QSystemTrayIcon(ico, self)
            tray.setToolTip("DofusPouletFlemmards")
            menu = QMenu()
            menu.addAction("Afficher DPF", self._tray_show)
            menu.addSeparator()
            menu.addAction("Quitter DPF", self._tray_quit)
            tray.setContextMenu(menu)
            tray.activated.connect(self._tray_activated)
            tray.show()
            self.tray = tray
            _tray_log("Tray OK.")
        except Exception as e:
            self.tray = None
            _tray_log("Tray erreur : %r" % e)

    def _tray_activated(self, reason):
        from PySide6.QtWidgets import QSystemTrayIcon
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick, QSystemTrayIcon.MiddleClick):
            self._tray_show()

    def _tray_show(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _tray_quit(self):
        self._force_quit = True
        self.close()

    def set_always_on_top(self, on):
        self.cfg["always_on_top"] = bool(on)
        config.save(self.cfg)
        if not on:
            self._set_dpf_topmost(False)
        self._refresh_overlay()   # application immédiate (le timer entretient ensuite)

    def _set_dpf_topmost(self, on):
        # au-dessus de Dofus UNIQUEMENT : topmost quand Dofus/DPF est devant, z normal sinon
        # (exactement comme l'overlay -> ne couvre pas tes autres applis)
        on = bool(on)
        if on == getattr(self, "_dpf_topmost", None):
            return
        self._dpf_topmost = on
        try:
            hwnd = int(self.winId())
            HWND_TOPMOST, HWND_NOTOPMOST = -1, -2
            SWP_NOSIZE, SWP_NOMOVE, SWP_NOACTIVATE = 0x0001, 0x0002, 0x0010
            win32gui.SetWindowPos(hwnd, HWND_TOPMOST if on else HWND_NOTOPMOST,
                                  0, 0, 0, 0, SWP_NOSIZE | SWP_NOMOVE | SWP_NOACTIVATE)
        except Exception:
            pass

    def set_theme(self, name):
        name = "light" if name == "light" else "dark"
        self.cfg["theme"] = name
        config.save(self.cfg)
        try:
            QApplication.instance().setStyleSheet(build_qss(name))
        except Exception:
            pass
        if hasattr(self, "_sync_theme_buttons"):
            self._sync_theme_buttons()

    def _toggle_theme(self):
        self.set_theme("light" if self.cfg.get("theme", "dark") == "dark" else "dark")

    def _apply_banner(self):
        # bannière adaptée au thème (sombre/clair), avec repli sur l'ancienne
        path = BANNER_DARK if self.cfg.get("theme", "dark") != "light" else BANNER_LIGHT
        pix = QPixmap(path)
        if pix.isNull():
            pix = QPixmap(BANNER_DARK)
        if pix.isNull():
            return False
        self.banner.setPixmap(pix.scaledToHeight(78, Qt.SmoothTransformation))
        return True

    def _sync_theme_buttons(self):
        dark = self.cfg.get("theme", "dark") != "light"
        if hasattr(self, "banner"):
            self._apply_banner()
        if hasattr(self, "btn_theme"):
            self.btn_theme.setText("\u2600\ufe0f  Clair" if dark else "\U0001f319  Sombre")

    def _save_flag(self, key, val):
        self.cfg[key] = bool(val)
        config.save(self.cfg)

    # ---- Sauvegarde / restauration de la config ----
    def export_config(self):
        import json
        from PySide6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(self, "Exporter la configuration DPF",
                                              "dpf_config_backup.json", "JSON (*.json)")
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.cfg, f, ensure_ascii=False, indent=2)
            self.status.setText("Config exportée : %s" % path)
        except Exception as e:
            self.status.setText("Échec de l'export : %s" % e)

    def import_config(self):
        import json
        from PySide6.QtWidgets import QFileDialog, QMessageBox
        path, _ = QFileDialog.getOpenFileName(self, "Importer une configuration DPF",
                                              "", "JSON (*.json)")
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                raise ValueError("fichier invalide")
        except Exception as e:
            self.status.setText("Échec de l'import : %s" % e)
            return
        self.cfg.update(data)
        config.save(self.cfg)
        self.status.setText("Config importée. Redémarre DPF pour tout appliquer.")
        try:
            QMessageBox.information(self, "Configuration importée",
                "La configuration a bien été importée.\n\n"
                "Redémarre DPF pour que tous les réglages (positions, macros, presets, "
                "raccourcis) soient pris en compte.")
        except Exception:
            pass

    # ---- Vérification de mise à jour (via l'API des releases GitHub) ----
    def check_update(self, manual=False):
        url = (getattr(config, "UPDATE_URL", "") or "").strip()
        if not url:
            if manual:
                self.status.setText("Vérif. MAJ : aucune URL configurée (config.py → UPDATE_URL).")
            return
        threading.Thread(target=self._update_worker, args=(url, manual), daemon=True).start()

    def _update_worker(self, url, manual):
        import json
        import ssl
        import urllib.request
        import urllib.error
        req = urllib.request.Request(url, headers={
            "User-Agent": "DPF-update-check",
            "Accept": "application/vnd.github+json"})
        # contexte non vérifié pour le 2e essai (souvent nécessaire depuis un .exe Windows)
        loose = ssl.create_default_context()
        loose.check_hostname = False
        loose.verify_mode = ssl.CERT_NONE
        data = None
        last_err = None
        for ctx in (None, loose):
            try:
                kw = {"timeout": 8}
                if ctx is not None:
                    kw["context"] = ctx
                with urllib.request.urlopen(req, **kw) as r:
                    data = json.loads(r.read().decode("utf-8", "ignore"))
                break
            except urllib.error.HTTPError as e:
                self._dbg("MAJ : HTTPError %s" % e.code, "warn")
                if manual:
                    if e.code == 404:
                        self.problemSig.emit("Vérif. MAJ : aucune release publiée (ou repo en privé).", "warn")
                    else:
                        self.problemSig.emit("Vérif. MAJ : erreur GitHub (code %s)." % e.code, "warn")
                return
            except Exception as e:
                last_err = e
                continue
        if data is None:
            self._dbg("MAJ : échec réseau -> %r" % last_err, "warn")
            if manual:
                self.problemSig.emit("Vérif. MAJ : réseau indisponible (%s)." % type(last_err).__name__, "warn")
            return
        latest = str(data.get("tag_name") or "").strip()
        if not latest:
            if manual:
                self.problemSig.emit("Vérif. MAJ : aucune release publiée pour le moment.", "warn")
            return

        def parse(v):
            out = []
            for p in v.lower().replace("v", "").split("."):
                digits = "".join(ch for ch in p if ch.isdigit())
                out.append(int(digits) if digits else 0)
            return tuple(out)

        try:
            newer = parse(latest) > parse(config.VERSION)
        except Exception:
            newer = False
        if newer:
            msg = ("\U0001f514 Nouvelle version dispo : %s (tu as v%s) — "
                   "télécharge-la sur GitHub." % (latest, config.VERSION))
            self.problemSig.emit(msg, "ok")     # Debug
            self.statusSig.emit(msg)            # barre de statut du bas
        elif manual:
            msg = "DPF est à jour (v%s)." % config.VERSION
            self.problemSig.emit(msg, "ok")     # Debug
            self.statusSig.emit(msg)            # barre de statut du bas

    def changeEvent(self, event):
        from PySide6.QtCore import QEvent
        if event.type() == QEvent.WindowStateChange and (self.windowState() & Qt.WindowMinimized):
            if self.cfg.get("minimize_to_tray", False) and getattr(self, "tray", None):
                # réduire -> cacher dans la barre système (sinon réduction normale)
                QTimer.singleShot(0, self.hide)
        super().changeEvent(event)

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 14, 18, 16)
        root.setSpacing(12)

        # --- En-tete : banniere logo (repli sur texte si l'image manque) ---
        header = QWidget()
        header.setObjectName("header")
        hb = QVBoxLayout(header)
        hb.setContentsMargins(0, 2, 0, 2)
        hb.setSpacing(2)
        topbar = QHBoxLayout(); topbar.setContentsMargins(0, 0, 0, 0); topbar.addStretch()
        self.btn_theme = QPushButton("\u2600\ufe0f  Clair")
        self.btn_theme.setCursor(Qt.PointingHandCursor)
        self.btn_theme.setMinimumWidth(112)
        self.btn_theme.setMinimumHeight(32)
        self.btn_theme.setToolTip("Basculer entre thème clair et sombre")
        self.btn_theme.clicked.connect(self._toggle_theme)
        topbar.addWidget(self.btn_theme)
        hb.addLayout(topbar)
        self.banner = QLabel()
        self.banner.setAlignment(Qt.AlignCenter)
        self.banner.setStyleSheet("background: transparent;")
        if self._apply_banner():
            hb.addWidget(self.banner)
        else:
            title = QLabel("DofusPouletFlemmards")
            title.setObjectName("title")
            title.setAlignment(Qt.AlignCenter)
            hb.addWidget(title)
        sub = QLabel("Le tool des flemmards, pour les flemmards.")
        sub.setObjectName("sub")
        sub.setAlignment(Qt.AlignCenter)
        hb.addWidget(sub)
        root.addWidget(header)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._tab_windows(), "Fenêtres")
        self.tabs.addTab(self._tab_comptes(), "Comptes")
        self.tabs.addTab(self._tab_presets(), "Presets")
        self.tabs.addTab(self._tab_trade(), "Échange")
        self.tabs.addTab(self._tab_actions(), "Actions")
        self.tabs.addTab(self._tab_messages(), "Messages")
        self.tabs.addTab(self._tab_raccourcis(), "Raccourcis")
        self.tabs.addTab(self._tab_debug(), "Debug")
        self.tabs.addTab(self._tab_parametres(), "Paramètres")
        root.addWidget(self.tabs, 1)

        statusrow = QHBoxLayout()
        statusrow.setContentsMargins(0, 0, 0, 0)
        self.status = QLabel("Prêt.")
        self.status.setObjectName("status")
        statusrow.addWidget(self.status, 1)
        self.credit = QLabel(_credit())
        self.credit.setObjectName("credit")
        self.credit.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.credit.setStyleSheet("color:#7a8294; font-size:11px;")
        self.credit.setWordWrap(False)
        statusrow.addWidget(self.credit, 0)
        root.addLayout(statusrow)
        self._sync_theme_buttons()

        # Permet de redimensionner librement : aucun libellé ne force une largeur mini enorme
        for lbl in self.findChildren(QLabel):
            lbl.setWordWrap(True)
        self.credit.setWordWrap(False)      # le crédit reste sur une seule ligne
        self.setMinimumSize(380, 420)

    def _show_welcome(self):
        from PySide6.QtGui import QFont, QCursor
        import subprocess

        dlg = QDialog(self)
        dlg.setWindowTitle("Bienvenue dans DofusPouletFlemmards")
        dlg.setMinimumSize(560, 560)
        dlg.setWindowModality(Qt.ApplicationModal)
        root = QVBoxLayout(dlg)
        root.setContentsMargins(22, 18, 22, 16); root.setSpacing(8)

        title = QLabel("Bienvenue ! 🐔")
        title.setStyleSheet("color:%s; background:transparent;" % ACCENT)
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        root.addWidget(title)
        sub = QLabel("DPF gère tes fenêtres Dofus Retro (rotation, échanges, AutoFocus, macros). "
                     "Pour que l'AutoFocus marche, quelques réglages de notifications sont nécessaires.")
        sub.setWordWrap(True); sub.setObjectName("muted")
        root.addWidget(sub)

        def card(titre, color):
            f = QFrame(); f.setObjectName("card")
            v = QVBoxLayout(f); v.setContentsMargins(14, 10, 14, 12); v.setSpacing(8)
            tt = QLabel(titre); tt.setStyleSheet("color:%s; background:transparent; font-weight:700;" % color)
            v.addWidget(tt)
            root.addWidget(f)
            return v

        def item(parent, icon, titre, texte, uri=None):
            row = QFrame(); row.setObjectName("inforow")
            rl = QHBoxLayout(row); rl.setContentsMargins(12, 8, 12, 8); rl.setSpacing(10)
            ic = QLabel(icon); ic.setFixedWidth(22); ic.setStyleSheet("background:transparent;")
            rl.addWidget(ic)
            col = QVBoxLayout(); col.setSpacing(1)
            lt = QLabel(titre); lt.setStyleSheet("background:transparent; font-weight:600;")
            ls = QLabel(texte); ls.setWordWrap(True); ls.setObjectName("muted")
            col.addWidget(lt); col.addWidget(ls)
            rl.addLayout(col, 1)
            if uri:
                b = QPushButton("Ouvrir"); b.setObjectName("linkbtn"); b.setCursor(QCursor(Qt.PointingHandCursor))
                def _open(_=False, u=uri, bb=b):
                    try:
                        subprocess.run(["start", "", u], shell=True)
                        bb.setText("Ouvert ✓")
                        bb.setStyleSheet("background:transparent; color:#5fb96a; border:1px solid #5fb96a;"
                                         "border-radius:8px; padding:6px 10px;")
                    except Exception:
                        pass
                b.clicked.connect(_open)
                rl.addWidget(b)
            parent.addWidget(row)

        cl = card("PRÉREQUIS", ACCENT)
        item(cl, "🔔", "Autoriser l'accès aux notifications",
             "Paramètres > Confidentialité > Notifications > activer.", "ms-settings:privacy-notifications")
        item(cl, "🔔", "Activer les notifications Windows",
             "Paramètres > Système > Notifications > activer (+ autoriser les bannières).", "ms-settings:notifications")
        item(cl, "🎮", "Activer les notifications en arrière-plan dans Dofus",
             "Dans le jeu : Options > Général > « Notifications en arrière-plan ».")

        cl2 = card("RECOMMANDÉ", GREEN)
        item(cl2, "🔇", "Couper le son des notifications de Dofus",
             "Paramètres > Système > Notifications > Dofus 1 : désactiver le son (et la bannière).",
             "ms-settings:notifications")
        item(cl2, "🧹", "Supprimer la bannière dès son apparition",
             "Déjà activé par défaut dans DPF (Paramètres > Affichage).")

        cl3 = card("BON À SAVOIR", ACCENT)
        note = QLabel("DPF est un outil de gestion de fenêtres. Garde un usage raisonnable et légit. "
                      "Tu pourras revoir ce guide via le bouton « Revoir le guide » dans Paramètres.")
        note.setWordWrap(True); note.setObjectName("dim")
        cl3.addWidget(note)

        root.addStretch()
        chk = QCheckBox("Ne plus afficher au démarrage")
        chk.setObjectName("muted")
        root.addWidget(chk)
        b_ok = QPushButton("J'ai compris"); b_ok.setObjectName("accent")
        b_ok.clicked.connect(dlg.accept)
        root.addWidget(b_ok)

        dlg.exec()
        if chk.isChecked():
            self.cfg["welcome_shown"] = True
            config.save(self.cfg)

    def _dofus_foreground(self):
        try:
            fg = win32gui.GetForegroundWindow()
        except Exception:
            return False
        return any(w["hwnd"] == fg for w in self.windows)

    def go_back(self):
        if self.prev_hwnd and win32util.window_alive(self.prev_hwnd):
            win32util.activate(self.prev_hwnd)
            for i, win in enumerate(self.windows):
                if win["hwnd"] == self.prev_hwnd:
                    self.idx = i
                    self.list.setCurrentRow(i)
                    self._ov_char = self.name_of(win)
                    break
            self.status.setText("Retour direct.")
            self._refresh_overlay()
        else:
            self.go_prev()

    def go_main(self):
        for i, win in enumerate(self.windows):
            if self.cfg["chars"].get(win["title"], {}).get("favori"):
                self.idx = i
                self._activate_idx()
                return
        self.status.setText("Aucun perso principal (mets une etoile Favori).")

    def toggle_move_mode(self):
        self.move_mode = not self.move_mode
        self.status.setText("Mode déplacement : %s" % ("ON" if self.move_mode else "OFF"))
        self._refresh_overlay()

    def do_join(self):
        if not self.windows:
            return
        try:
            x, y = win32api.GetCursorPos()
        except Exception:
            return
        origin = win32gui.GetForegroundWindow()
        hwnds = [win["hwnd"] for win in self.windows if not self._is_disabled(win)]
        delay = max(0, int(self.cfg.get("join_delay_ms", 100))) / 1000.0
        self.status.setText("Join : defilement sur %d fenêtres..." % len(hwnds))
        threading.Thread(target=self._join_worker, args=(hwnds, origin, x, y, delay),
                         daemon=True).start()

    def _wait_foreground(self, hwnd, timeout=1.0):
        """Attend que la fenêtre soit REELLEMENT au premier plan (comme WinWaitActive)."""
        end = time.time() + timeout
        while time.time() < end:
            try:
                if win32gui.GetForegroundWindow() == hwnd:
                    return True
            except Exception:
                pass
            time.sleep(0.008)
        return False

    def _join_worker(self, hwnds, origin, x, y, delay):
        self._poll_pause_until = time.time() + 3.0   # coupe le poll pixel pendant le defilement
        # CIRCUIT circulaire : on démarre sur la fenêtre courante et on continue dans
        # l'ordre de l'overlay en bouclant (ex. Cinglante -> Punitive -> Abso -> Winter -> ...).
        if origin in hwnds:
            s = hwnds.index(origin)
            ordered = hwnds[s:] + hwnds[:s]
        else:
            ordered = list(hwnds)
        for h in ordered:
            self._poll_pause_until = time.time() + 2.0   # rafraichi -> reste en pause tout le temps
            try:
                win32util.activate(h)
                if not self._wait_foreground(h, 1.0):
                    continue
                win32api.SetCursorPos((x, y))
                time.sleep(0.01)
                self._shift_click()
            except Exception:
                pass
            time.sleep(delay)
        self._poll_pause_until = time.time() + 0.6       # petit buffer apres la fin
        try:
            if origin:
                win32util.activate(origin)
        except Exception:
            pass

    def _shift_click(self):
        # Win32 BRUT (ne touche pas la lib keyboard) -> raccourcis preserves
        MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP = 0x0002, 0x0004
        KEYUP = 0x0002
        VK_SHIFT = 0x10
        mods = (0x11, 0x12, 0xA2, 0xA3, 0xA4, 0xA5)  # CTRL, ALT, LCTRL, RCTRL, LALT, RALT
        try:
            for vk in mods:
                try:
                    win32api.keybd_event(vk, 0, KEYUP, 0)
                except Exception:
                    pass
            win32api.keybd_event(VK_SHIFT, 0, 0, 0)
            time.sleep(0.025)
            win32api.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            time.sleep(0.02)
            win32api.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            time.sleep(0.015)
        finally:
            try:
                win32api.keybd_event(VK_SHIFT, 0, KEYUP, 0)
            except Exception:
                pass

    def _shift_click_at(self, x, y):
        try:
            win32api.SetCursorPos((int(x), int(y)))
            time.sleep(0.01)
            self._shift_click()
        except Exception:
            pass

    def do_custom_join(self):
        if not self.windows:
            return
        leader = win32gui.GetForegroundWindow()
        ours = {win["hwnd"] for win in self.windows}
        if leader not in ours:
            leader = (self.windows[self.idx]["hwnd"] if 0 <= self.idx < len(self.windows)
                      else self.windows[0]["hwnd"])
        self.status.setText("Custom Join...")
        threading.Thread(target=self._custom_join_worker, args=(leader,), daemon=True).start()

    def _custom_join_worker(self, leader):
        delay = max(0, int(self.cfg.get("custom_join_delay_ms", 100))) / 1000.0
        self._poll_pause_until = time.time() + 4.0   # coupe le poll pixel pendant la sequence
        x1, y1 = self.cfg.get("cj_x1", 0), self.cfg.get("cj_y1", 0)   # Rejoindre
        x2, y2 = self.cfg.get("cj_x2", 0), self.cfg.get("cj_y2", 0)   # Prêt
        x3, y3 = self.cfg.get("cj_x3", 0), self.cfg.get("cj_y3", 0)   # Placement lanceur
        if not (x1 or y1):
            return
        has_ready = bool(x2 or y2)
        has_place = bool(x3 or y3)
        others = [w for w in self.windows
                  if w["hwnd"] != leader and not self._is_disabled(w)]
        # 1) PLACEMENT : le meneur se place EN PREMIER (clic NORMAL)
        if has_place:
            self._poll_pause_until = time.time() + 2.0
            if self._activate_confirm(leader):
                self._real_click(x3, y3, clicks=1)
                time.sleep(delay)
        # 2) REJOINDRE : SHIFT+clic (comme Join) sur chaque perso
        for w in others:
            self._poll_pause_until = time.time() + 2.0
            if self._activate_confirm(w["hwnd"]):
                self._shift_click_at(x1, y1)
                time.sleep(delay)
        # 3) PRET : clic NORMAL sur chaque perso, PUIS sur le meneur EN DERNIER
        if has_ready:
            for w in others:
                self._poll_pause_until = time.time() + 2.0
                if self._activate_confirm(w["hwnd"]):
                    self._real_click(x2, y2, clicks=1)
                    time.sleep(delay)
            if self._activate_confirm(leader):
                self._real_click(x2, y2, clicks=1)
                time.sleep(delay)
        self._poll_pause_until = time.time() + 0.6
        # retour lanceur
        try:
            win32util.activate(leader)
        except Exception:
            pass

    def _ingame_name(self, win):
        # le titre est "Pseudo - Dofus Retro vX.XX.XX" -> on prend le pseudo (regex robuste)
        t = win.get("title", "")
        m = re.match(r"^(.+?)\s*-\s*Dofus", t, re.IGNORECASE)
        if m:
            return m.group(1).strip()
        if " - " in t:
            return t.split(" - ")[0].strip()
        return self.name_of(win)

    def do_invite(self):
        if keyboard is None or not self.windows:
            return
        leader = win32gui.GetForegroundWindow()
        ours = {win["hwnd"] for win in self.windows}
        if leader not in ours:
            leader = (self.windows[self.idx]["hwnd"] if 0 <= self.idx < len(self.windows)
                      else self.windows[0]["hwnd"])
        self.status.setText("Invite : envoi des /invite...")
        threading.Thread(target=self._invite_worker, args=(leader,), daemon=True).start()

    def _invite_worker(self, leader):
        d = max(0, int(self.cfg.get("invite_delay_ms", 120))) / 1000.0
        da = max(0, int(self.cfg.get("invite_accept_delay_ms", 450))) / 1000.0
        others = [w for w in self.windows
                  if w["hwnd"] != leader and not self._is_disabled(w)]
        for win in others:
            name = self._ingame_name(win)
            if not name:
                continue
            self._poll_pause_until = time.time() + 8.0   # poll de fond muet toute la sequence
            # 1) LANCEUR : /invite pseudo (on confirme qu'il est au 1er plan)
            if not self._activate_confirm(leader):
                continue
            time.sleep(0.18)                      # laisser le meneur PRET a recevoir les touches
            try:
                keyboard.send("enter"); time.sleep(d)
                keyboard.write("/invite " + name); time.sleep(d)
                keyboard.send("enter")
            except Exception:
                pass
            # 2) laisser le popup apparaitre, BASCULER sur le membre, puis cliquer
            #    TA position « Accepter invitation » enregistrée (plus de détection pixel).
            time.sleep(da)
            if not self._activate_confirm(win["hwnd"]):
                continue
            time.sleep(0.08)
            ax = int(self.cfg.get("invite_accept_x", 0))
            ay = int(self.cfg.get("invite_accept_y", 0))
            if ax or ay:
                self._real_click(ax, ay, clicks=1)   # membre au 1er plan -> vrai clic sur TA position
                try:
                    self.problemSig.emit("Invitation acceptée : %s" % self.name_of(win), "ok")
                except Exception:
                    pass
            else:
                try:
                    self.problemSig.emit("Invitation : aucune position « Accepter » enregistrée "
                                         "(Paramètres → Invite de groupe → Capturer).", "warn")
                except Exception:
                    pass
            time.sleep(d)
        # 3) retour sur le MENEUR
        self._poll_pause_until = time.time() + 0.6
        try:
            win32util.activate(leader)
        except Exception:
            pass

    def _real_click(self, x, y, clicks=2):
        """Vrai clic gauche au premier plan (la fenêtre cible doit être active)."""
        MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP = 0x0002, 0x0004
        try:
            win32api.SetCursorPos((int(x), int(y)))
            time.sleep(0.03)
            for _ in range(max(1, clicks)):
                win32api.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                time.sleep(0.02)
                win32api.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                time.sleep(0.06)
        except Exception:
            pass

    def do_reload(self):
        # Relance COMPLETE de DPF (nouveau processus, etat propre)
        import sys, subprocess
        try:
            self.inputs.stop()
        except Exception:
            pass
        try:
            self.notifier.stop()
        except Exception:
            pass
        try:
            subprocess.Popen([sys.executable] + sys.argv)   # nouvelle instance
        except Exception:
            pass
        self._force_quit = True
        self.close()                                         # nettoie hooks/tray/overlay puis quitte

    def do_exit(self):
        self._force_quit = True
        self.close()

    def do_ctrlshift_toggle(self):
        # raccourci ON/OFF : simule le maintien de Ctrl + Shift (selection rapide a une
        # seule main). Méthode Dracoon : keyboard.press/release (la lib gere ses propres
        # injections, donc le 2e appui pour DESACTIVER est bien reconnu, contrairement a
        # keybd_event qui bloquait le hook).
        if keyboard is None:
            return
        try:
            if not self._ctrlshift_held:
                keyboard.press('ctrl')
                keyboard.press('shift')
                self._ctrlshift_held = True
                self.status.setText("Ctrl + Shift : MAINTENU (ON)")
            else:
                keyboard.release('shift')
                keyboard.release('ctrl')
                self._ctrlshift_held = False
                self.status.setText("Ctrl + Shift : relâché (OFF)")
        except Exception:
            pass

    def _release_ctrlshift(self):
        # securite : relache Ctrl+Shift s'ils sont maintenus (evite touches bloquees)
        if getattr(self, "_ctrlshift_held", False):
            try:
                if keyboard is not None:
                    keyboard.release('shift')
                    keyboard.release('ctrl')
            except Exception:
                pass
            self._ctrlshift_held = False

    def timer_toggle(self):
        if self._timer_running:
            self._timer_elapsed += time.time() - self._timer_start
            self._timer_running = False
        else:
            self._timer_start = time.time()
            self._timer_running = True
        self._refresh_overlay()

    def timer_reset(self):
        self._timer_running = False
        self._timer_elapsed = 0.0
        self._timer_start = time.time()
        self._refresh_overlay()

    def _refresh_overlay(self):
        title = "DPF"
        if self.move_mode:
            title += "   \u00b7   DEPL"
        if self._timer_running or self._timer_elapsed > 0:
            el = self._timer_elapsed + (time.time() - self._timer_start if self._timer_running else 0)
            title += "   \u00b7   %02d:%02d:%02d" % (int(el // 3600), int((el % 3600) // 60), int(el % 60))
        self.overlay.set_chrono(title)
        try:
            fg = win32gui.GetForegroundWindow()
        except Exception:
            fg = 0
        # suivi continu pour le Retour direct : la fenêtre Dofus qu'on quitte devient "précédente"
        ours = {w["hwnd"] for w in self.windows}
        if fg in ours and fg != self._cur_fg:
            if self._cur_fg in ours:
                self.prev_hwnd = self._cur_fg
            self._cur_fg = fg
        # « Garder DPF au-dessus » = au-dessus de DOFUS (et de l'overlay/DPF), pas des autres applis.
        # Période de grâce : on garde le « au-dessus » ~1,5 s après avoir quitté Dofus/DPF, ce qui
        # évite tout clignotement de l'overlay pendant les bascules de l'autoclic (focus transitoire).
        try:
            ov_hwnd = int(self.overlay.winId()); dpf_hwnd = int(self.winId())
        except Exception:
            ov_hwnd = dpf_hwnd = 0
        on_ours = (fg in ours or fg == ov_hwnd or fg == dpf_hwnd)
        if on_ours:
            self._last_ours_ts = time.time()
        want_topmost = on_ours or (time.time() - getattr(self, "_last_ours_ts", 0.0) < 1.5)
        if self.cfg.get("always_on_top", True):
            self._set_dpf_topmost(want_topmost)
        else:
            self._set_dpf_topmost(False)
        show = bool(self.cfg.get("overlay"))
        if self.overlay.isVisible() != show:
            self.overlay.setVisible(show)
        if not show:
            return
        self.overlay.set_topmost(want_topmost)
        items = [(self._overlay_label(w), w["hwnd"], self._is_disabled(w), self._is_skip(w),
                  bool(self.cfg["chars"].get(w["title"], {}).get("focus_combat", 1)))
                 for w in self.windows]
        if items != getattr(self, "_ov_items", None):
            self._ov_items = items
            self.overlay.set_chars(items)
        self.overlay.set_autoskip(bool(self.cfg.get("autoskip")))
        self.overlay.set_autofocus(bool(self.cfg.get("autofocus", True)))
        self.overlay.set_active(fg)

    def _mk_hotkey(self, value=""):
        b = HotkeyButton(value, on_change=self._hotkey_captured,
                         on_begin=self.inputs.stop, on_end=self.apply_hotkeys)
        self._hk_buttons.append(b)
        return b

    def _hotkey_captured(self, btn):
        combo = btn.value()
        alive = []
        for b in self._hk_buttons:
            try:
                b.value()                 # détecte les boutons detruits
                alive.append(b)
            except Exception:
                pass
        self._hk_buttons = alive
        if combo:                                   # un raccourci ne peut être que sur UN champ
            for other in self._hk_buttons:
                if other is not btn and other.value() == combo:
                    other.setValue("")
        # sauvegarde des raccourcis de presets (boutons marques _preset_name)
        ph = self.cfg.setdefault("preset_hotkeys", {})
        for b in self._hk_buttons:
            pn = getattr(b, "_preset_name", None)
            if pn is not None:
                if b.value():
                    ph[pn] = b.value()
                else:
                    ph.pop(pn, None)
        # raccourci A-Trade (bouton placé dans l'onglet Échange)
        if hasattr(self, "hk_autotrade"):
            try:
                self.cfg["autotrade_hotkey"] = self.hk_autotrade.value()
            except Exception:
                pass
        self.apply_raccourcis()
        self.apply_params()

    def _help(self, text):
        """Petit cercle '?' avec explication instantanee au survol."""
        return HelpDot(text)

    def _field_label(self, text, help_text=None):
        box = QWidget(); h = QHBoxLayout(box)
        h.setContentsMargins(0, 0, 0, 0); h.setSpacing(5)
        h.addWidget(QLabel(text))
        if help_text:
            h.addWidget(self._help(help_text))
        h.addStretch()
        return box

    def _card(self, title, help_text=None):
        from PySide6.QtWidgets import QFrame
        frame = QFrame(); frame.setObjectName("card")
        v = QVBoxLayout(frame)
        v.setContentsMargins(14, 12, 14, 14); v.setSpacing(10)
        head = QHBoxLayout(); head.setSpacing(6)
        t = QLabel(title); t.setObjectName("cardtitle"); t.setWordWrap(False)
        head.addWidget(t)
        if help_text:
            head.addWidget(self._help(help_text))
        head.addStretch()
        v.addLayout(head)
        return frame, v

    def detect(self):
        found = win32util.dofus_windows()
        found_by_hwnd = {w["hwnd"]: w for w in found}
        # agrandir les NOUVELLES fenêtres si l'option est active
        if self.cfg.get("maximize_on_launch"):
            if not hasattr(self, "_seen_hwnds"):
                self._seen_hwnds = set()
            for win in found:
                if win["hwnd"] not in self._seen_hwnds:
                    self._seen_hwnds.add(win["hwnd"])
                    try:
                        win32util.maximize(win["hwnd"])
                    except Exception:
                        pass
        # IDENTITÉ = HWND (les titres peuvent être identiques a l'écran de connexion)
        existing = [found_by_hwnd[w["hwnd"]] for w in self.windows if w["hwnd"] in found_by_hwnd]
        existing_hwnds = {w["hwnd"] for w in existing}
        new = [w for w in found if w["hwnd"] not in existing_hwnds]
        # au démarrage : applique l'ordre sauvegarde (par titre) aux nouvelles
        if not self.windows and self.cfg.get("order"):
            order = self.cfg["order"]
            new.sort(key=lambda w: order.index(w["title"]) if w["title"] in order else len(order))
        ordered = existing + new
        changed = False
        for win in ordered:
            e = self.cfg["chars"].setdefault(win["title"],
                                             {"name": win["title"], "favori": 0, "disabled": 0})
            # Synchro JSON <-> GUI : on ECRIT physiquement les valeurs par defaut si
            # elles manquent, pour que le moteur de combat (qui lit le JSON) ne traite
            # plus une cle absente comme "0/desactive".
            for k, dv in (("focus_combat", 1), ("focus_echange", 1), ("skip", 0)):
                if k not in e:
                    e[k] = dv
                    changed = True
        self.windows = ordered
        if changed:
            config.save(self.cfg)
        sig = [(w["hwnd"], w["title"]) for w in ordered]
        if sig != getattr(self, "_last_sig", None):
            self._last_sig = sig
            self._save_order()
            self.refresh_views()
            self._refresh_overlay()

    def name_of(self, win):
        return self.cfg["chars"].get(win["title"], {}).get("name", win["title"])

    # ---- Tout réduire / Tout restaurer (onglet Fenêtres) ----
    def minimize_all(self):
        n = 0
        for w in list(self.windows):
            try:
                win32util.minimize(w["hwnd"]); n += 1
            except Exception:
                pass
        self.status.setText("Réduit %d fenêtre(s)." % n)

    def restore_all(self):
        n = 0
        for w in list(self.windows):
            try:
                win32util.restore(w["hwnd"]); n += 1
            except Exception:
                pass
        self.status.setText("Restauré %d fenêtre(s)." % n)

    # ---- Diagnostic (onglet Debug) ----
    def run_diagnostic(self):
        d = lambda m, t="info": self._dbg_write(m, t, force=True)
        d("──────── DIAGNOSTIC ────────", "ok")
        # 1) winsdk / accès notifications / mode
        try:
            from . import notifier as _nf
            d("winsdk (lecture notifs) : %s" % ("disponible ✓" if _nf.WINSDK_OK else "ABSENT ✗"),
              "ok" if _nf.WINSDK_OK else "error")
        except Exception:
            pass
        nt = getattr(self, "notifier", None)
        if nt is not None:
            acc = getattr(nt, "access_ok", None)
            d("Accès aux notifications : %s" % (
                "accordé ✓" if acc is True else ("REFUSÉ ✗ (Paramètres > Confidentialité > Notifications)"
                                                 if acc is False else "inconnu (lance/relance l'écoute)")),
              "ok" if acc is True else ("error" if acc is False else "warn"))
            d("Mode d'écoute : %s" % getattr(nt, "mode", "?"),
              "warn" if getattr(nt, "mode", "?") == "polling" else "ok")
            alive = bool(getattr(nt, "_running", False))
            d("Écouteur actif : %s" % ("oui ✓" if alive else "NON ✗"), "ok" if alive else "error")
        # 2) verrou de premier plan
        try:
            t = win32util.get_foreground_lock_timeout()
            if t == 0:
                d("Verrou de premier plan : désactivé ✓ (switch fiable)", "ok")
            elif t is None:
                d("Verrou de premier plan : illisible", "warn")
            else:
                d("Verrou de premier plan : %d ms ✗ (devrait être 0 — relance DPF)" % t, "error")
        except Exception:
            pass
        # 3) fenêtres détectées
        wins = list(self.windows)
        d("Fenêtres Dofus détectées : %d" % len(wins), "ok" if wins else "error")
        if not wins:
            d("  ✗ Aucune fenêtre. Dofus est-il lancé et connecté ?", "error")
        for w in wins:
            e = self.cfg["chars"].get(w["title"], {})
            flags = []
            if e.get("disabled"): flags.append("désactivé")
            if not e.get("focus_combat", 1): flags.append("focus combat OFF")
            if e.get("skip"): flags.append("skip")
            extra = (" — " + ", ".join(flags)) if flags else ""
            d("  • %s  [exe=%s]%s" % (self._ingame_name(w), w.get("exe", "?"), extra), "info")
        # 4) hotkeys clavier
        d("Module clavier (hotkeys) : %s" % ("OK ✓" if keyboard is not None else "ABSENT ✗"),
          "ok" if keyboard is not None else "error")
        d("──────── FIN DIAGNOSTIC ────────", "ok")

    def _overlay_name(self, win):
        # overlay = pseudo seul (jamais "- Dofus Retro vX")
        nm = self.cfg["chars"].get(win["title"], {}).get("name")
        if nm and "dofus" not in nm.lower():
            return nm                       # vrai renommage court choisi par l'utilisateur
        return self._ingame_name(win)

    def _overlay_label(self, win):
        # nom affiché dans l'overlay, préfixé de ⭐ si le perso est en favori
        nm = self._overlay_name(win)
        if self.cfg["chars"].get(win["title"], {}).get("favori"):
            nm = "\u2b50 " + nm
        return nm

    def _is_disabled(self, win):
        return bool(self.cfg["chars"].get(win["title"], {}).get("disabled"))

    def _is_skip(self, win):
        return bool(self.cfg["chars"].get(win["title"], {}).get("skip"))

    def _win_by_hwnd(self, hwnd):
        for w in self.windows:
            if w["hwnd"] == hwnd:
                return w
        return None

    def toggle_autoskip(self):
        self.cfg["autoskip"] = not bool(self.cfg.get("autoskip"))
        config.save(self.cfg)
        self.status.setText("AutoSkip %s" % ("ON" if self.cfg["autoskip"] else "OFF"))
        self.overlay.set_autoskip(self.cfg["autoskip"])

    def toggle_autofocus(self):
        self.cfg["autofocus"] = not bool(self.cfg.get("autofocus", True))
        config.save(self.cfg)
        self.status.setText("AutoFocus %s" % ("ON" if self.cfg["autofocus"] else "OFF"))
        self.overlay.set_autofocus(self.cfg["autofocus"])

    def _toggle_window_visibility(self):
        # clic sur « DPF » dans l'overlay -> affiche ou masque la fenêtre principale
        if self.isVisible() and not self.isMinimized():
            self.hide()
        else:
            self.showNormal()
            self.raise_()
            self.activateWindow()

    def toggle_overlay(self):
        self.cfg["overlay"] = not bool(self.cfg.get("overlay", True))
        config.save(self.cfg)
        self._refresh_overlay()                       # applique l'affichage/masquage
        self.status.setText("Overlay %s" % ("affiché" if self.cfg["overlay"] else "masqué"))
        if hasattr(self, "chk_overlay"):              # garde la case Paramètres synchro
            self.chk_overlay.setChecked(self.cfg["overlay"])

    def _overlay_toggle_skip(self, hwnd):
        w = self._win_by_hwnd(hwnd)
        if not w:
            return
        e = self.cfg["chars"].setdefault(w["title"], {})
        e["skip"] = 0 if e.get("skip") else 1
        config.save(self.cfg)
        self._ov_items = None        # force la reconstruction de l'overlay
        self._refresh_overlay()

    def _overlay_toggle_enable(self, hwnd):
        w = self._win_by_hwnd(hwnd)
        if not w:
            return
        e = self.cfg["chars"].setdefault(w["title"], {})
        e["disabled"] = 0 if e.get("disabled") else 1
        config.save(self.cfg)
        self._ov_items = None
        self.refresh_views()
        self._refresh_overlay()

    def _overlay_toggle_combat(self, hwnd):
        w = self._win_by_hwnd(hwnd)
        if not w:
            return
        e = self.cfg["chars"].setdefault(w["title"], {})
        e["focus_combat"] = 0 if e.get("focus_combat", 1) else 1
        config.save(self.cfg)
        self._ov_items = None
        self.refresh_views()
        self._refresh_overlay()

    def _overlay_toggle_echange(self, hwnd):
        w = self._win_by_hwnd(hwnd)
        if not w:
            return
        e = self.cfg["chars"].setdefault(w["title"], {})
        e["focus_echange"] = 0 if e.get("focus_echange", 1) else 1
        config.save(self.cfg)
        self._ov_items = None
        self.refresh_views()
        self._refresh_overlay()

    def _overlay_moved(self, x, y):
        self.cfg["overlay_x"] = int(x)
        self.cfg["overlay_y"] = int(y)
        config.save(self.cfg)

    def _overlay_focus(self, hwnd):
        # clic sur un pseudo de l'overlay -> on amene cette fenetre au premier plan
        try:
            win32util.activate(hwnd)
        except Exception:
            pass
        self._refresh_overlay()

    def _send_key_raw(self, key):
        """Envoie une touche simple via Win32 (ne corrompt pas le hook keyboard-lib)."""
        try:
            key = (key or "").strip()
            if not key:
                return
            specials = {"space": 0x20, "enter": 0x0D, "tab": 0x09, "esc": 0x1B, "escape": 0x1B}
            if len(key) == 1:
                vk = win32api.VkKeyScan(key) & 0xFF
            else:
                vk = specials.get(key.lower())
            if not vk or vk == 0xFF:
                return
            win32api.keybd_event(vk, 0, 0, 0)
            time.sleep(0.03)
            win32api.keybd_event(vk, 0, 0x0002, 0)
        except Exception:
            pass

    def _skip_worker(self, hwnd):
        # Le perso vient d'être focus. On attend le délai, puis on passe son tour.
        # On ne RE-ACTIVE JAMAIS la fenêtre : si la notif suivante a déjà activé un
        # autre perso, le ré-activer volerait le focus ET skiperait le mauvais perso.
        # Dofus n'acceptant le clavier qu'au PREMIER PLAN, on n'envoie le skip que si
        # CE perso est toujours devant ; sinon on abandonne proprement (son tour est
        # de toute façon déjà terminé puisque le focus a changé).
        time.sleep(max(0, int(self.cfg.get("skip_delay_ms", 120))) / 1000.0)
        try:
            if win32gui.GetForegroundWindow() != hwnd:
                return
        except Exception:
            return
        self._send_key_raw(self.cfg.get("skip_key", "s"))

    def _stats_bump(self, pseudo):
        # un tour de combat traité ; nouveau combat si > 45 s depuis le dernier tour
        s = self._stats
        now = time.time()
        if now - s.get("last_turn", 0.0) > 45:
            s["combats"] = s.get("combats", 0) + 1
        s["last_turn"] = now
        s["turns"] = s.get("turns", 0) + 1
        if pseudo:
            s["per_char"][pseudo] = s["per_char"].get(pseudo, 0) + 1
        try:
            self._stats_refresh()
        except Exception:
            pass

    def refresh_views(self):
        from PySide6.QtGui import QFont, QColor
        cur = self.list.currentRow()
        self.list.blockSignals(True)
        self.list.clear()
        for i, win in enumerate(self.windows):
            title = win["title"]
            entry = self.cfg["chars"].get(title, {})
            fav = entry.get("favori")
            disabled = entry.get("disabled")
            star = "\U0001f31f " if fav else ""
            it = QListWidgetItem("\u2807\u2807   %d.   %s%s" % (i + 1, star, self.name_of(win)))
            it.setToolTip("Glisse pour réordonner")
            it.setData(Qt.UserRole, win["hwnd"])
            if disabled:
                f = QFont(self.list.font()); f.setStrikeOut(True); it.setFont(f)
                it.setForeground(QColor("#6b7280"))
            self.list.addItem(it)
        self.list.blockSignals(False)
        if 0 <= cur < self.list.count():
            self.list.setCurrentRow(cur)
        try:
            self._refresh_comptes()
        except Exception:
            pass
        try:
            self._populate_msg_targets()
        except Exception:
            pass

    def _cycle_list(self):
        """(idx, win) des fenêtres ACTIVES (non désactivées), sinon toutes."""
        items = [(i, w) for i, w in enumerate(self.windows) if not self._is_disabled(w)]
        return items or list(enumerate(self.windows))

    def _cycle(self, direction):
        if not self.windows:
            return
        cyc = self._cycle_list()
        if not cyc:
            return
        try:
            fg = win32gui.GetForegroundWindow()
        except Exception:
            fg = 0
        pos = next((p for p, (i, w) in enumerate(cyc) if w["hwnd"] == fg), None)
        newp = 0 if pos is None else (pos + direction) % len(cyc)
        self.idx = cyc[newp][0]
        self._activate_idx()

    def go_next(self):
        self._cycle(+1)

    def go_prev(self):
        self._cycle(-1)

    def _activate_idx(self):
        win = self.windows[self.idx]
        win32util.activate(win["hwnd"])
        self.list.setCurrentRow(self.idx)
        self.status.setText("Actif : %s" % self.name_of(win))
        self._refresh_overlay()

    def _match_pseudo(self, pseudo):
        p = (pseudo or "").strip().lower()
        if not p:
            return None
        norm = lambda s: re.sub(r"[^a-z0-9]", "", (s or "").lower())
        pn = norm(pseudo)
        # 1) match exact sur le pseudo extrait du titre
        for win in self.windows:
            if self._ingame_name(win).strip().lower() == p:
                return win
        # 2) match NORMALISE (ignore espaces/tirets/accents/casse) -> robuste
        if pn:
            for win in self.windows:
                if norm(self._ingame_name(win)) == pn:
                    return win
        # 3) repli : contenu dans le titre complet
        for win in self.windows:
            if p in win["title"].lower():
                return win
        return None

    def on_notif(self, pseudo, body, ntype):
        self._dbg("NOTIF [%s] %s — %s" % ((ntype or "?").upper(), pseudo or "?", body or ""), "info")
        win = self._match_pseudo(pseudo)
        if not win:
            self._dbg("  ✗ aucun perso détecté ne correspond à « %s »" % (pseudo or ""), "error")
            return
        # anti-doublon court : évite de traiter 2x le MÊME événement (Windows envoie
        # parfois le toast en double dans la même fraction de seconde). La dédup par
        # nid (listener) attrape déjà ça ; ce filet n'a besoin que de ~0.3 s, ce qui
        # NE jette pas un tour légitime rapproché (ex. nouveau tour juste après un skip).
        key = (pseudo, ntype)
        now = time.time()
        if now - self._notif_cooldown.get(key, 0.0) < 0.3:
            self._dbg("  · ignoré (anti-doublon < 0.3 s)", "dim")
            return
        self._notif_cooldown[key] = now
        entry = self.cfg["chars"].get(win["title"], {})
        if not self.cfg.get("autofocus", True):
            self._dbg("  ✗ AutoFocus global OFF", "warn")
            return                              # AutoFocus global OFF -> aucun switch auto
        # NB : l'echange n'est plus gere ici (notifications) mais par detection pixel
        # (_poll_trades) -> contourne la suppression Windows des toasts identiques.
        if ntype == "combat":
            self.last_trade_hwnd = 0      # combat -> coupe l'auto-validation (zéro faux clic sur Prêt)
            # 1) Le FOCUS dépend UNIQUEMENT de focus_combat (jamais du skip individuel)
            if not entry.get("focus_combat", 1):
                self._dbg("  ✗ Focus Combat désactivé pour %s" % self.name_of(win), "warn")
                return
            win32util.activate(win["hwnd"])      # focus TOUJOURS : le skip ne court-circuite jamais
            self._dbg("  ✓ Combat : focus %s" % self.name_of(win), "ok")
            self._stats_bump(pseudo)
            self.status.setText("Combat : focus %s" % self.name_of(win))
            self._refresh_overlay()
            # 2) Le passage de tour (skip) n'a lieu QUE si l'Auto-Skip GLOBAL est ON
            #    ET que ce perso a skip=1. Si le global est OFF, skip individuel ignoré.
            global_autoskip = bool(self.cfg.get("autoskip"))
            indiv_skip = bool(entry.get("skip", 0))
            if global_autoskip and indiv_skip:
                self._dbg("  ⏭ AutoSkip : passage du tour de %s" % self.name_of(win), "ok")
                threading.Thread(target=self._skip_worker, args=(win["hwnd"],), daemon=True).start()

        # NB : les échanges ne passent PLUS par les notifications (elles sont bugguées sur les
        # demandes répétées). C'est l'AutoTrade par IMAGE (A-Trade) qui s'en occupe désormais.

    def _echange_accept_worker(self, hwnd, leader, ax, ay, name):
        # bascule sur le receveur -> clic sur la position enregistrée -> retour meneur
        self._poll_pause_until = time.time() + 5.0
        if not self._activate_confirm(hwnd):
            return
        time.sleep(0.18)
        self._real_click(ax, ay, clicks=1)        # receveur au 1er plan -> vrai clic sur TA position
        self.last_trade_hwnd = hwnd
        self.last_trade_tick = time.time()
        try:
            self.problemSig.emit("Échange accepté : %s" % name, "ok")
        except Exception:
            pass
        if leader and leader != hwnd:             # retour sur le meneur
            time.sleep(0.10)
            self._poll_pause_until = time.time() + 0.6
            try:
                win32util.activate(leader)
            except Exception:
                pass

    def _activate_confirm(self, hwnd, timeout=0.8):
        """Activé la fenêtre et CONFIRME qu'elle est au premier plan (2e essai si besoin)."""
        win32util.activate(hwnd)
        if self._wait_foreground(hwnd, timeout):
            return True
        win32util.activate(hwnd)                 # 2e tentative (repli musclé inclus)
        return self._wait_foreground(hwnd, timeout)

    def _accept_trade_worker(self, target, launcher, px, py):
        # un seul accept à la fois (évite que des echanges rapides se chevauchent)
        with self._accept_lock:
            try:
                if not self._activate_confirm(target):
                    return                       # on NE clique PAS si le switch a échoué
                time.sleep(0.06)
                self._real_click(px, py, clicks=1)
                time.sleep(0.06)
                if launcher and launcher != target:
                    win32util.activate(launcher)
            except Exception:
                pass

    # ----- (RETIRÉ) AutoTrade par détection pixel : remplacé par l'acceptation via notification.
    #        Conservé inerte par sécurité — ne scanne plus jamais, ne clique plus jamais. -----
    def _poll_trades(self):
        return    # détection orange définitivement désactivée (zéro risque de faux clic sur Prêt)

    def _trade_scan_worker(self):
        try:
            self._accept_sweep()
        except Exception:
            self._dbg_exc("sweep échange")
        finally:
            self._trade_scanning = False

    def _emitter_is_mine(self, hwnd):
        """True si l'emetteur du dialogue (echange/invite) est un de TES persos.
        Lit le pseudo via l'OCR Windows (2 tentatives espacees, le popup Dofus fait un
        fondu) et le compare a tes fenetres. Defensif : OCR indispo ou jamais lisible
        => True (on ne casse pas l'auto-accept) ; texte LU sans aucun de tes pseudos
        => False (emetteur externe)."""
        if not self.cfg.get("accept_only_mine", True):
            return True
        if not ocr_util.available():
            if not getattr(self, "_ocr_warned", False):
                self._ocr_warned = True
                try:
                    self.problemSig.emit("OCR Windows indisponible — la restriction « mes persos » "
                                         "est inactive (j'accepte tout). Réinstalle les dépendances.", "warn")
                except Exception:
                    pass
            return True
        norm = lambda s: re.sub(r"[^a-z0-9]", "", s.lower())
        mine = [norm(self._ingame_name(w)) for w in list(self.windows)]
        mine = [m for m in mine if m]
        got_text = False
        # Le popup Dofus fait un FONDU : la 1re lecture peut tomber trop tot (texte
        # vide/partiel) -> petit delai initial puis jusqu'a 3 lectures espacees, le
        # temps que le pseudo de l'emetteur soit net. (corrige "accepte a la 2e notif")
        time.sleep(0.15)
        for attempt in range(3):
            try:
                text = ocr_util.read_text(hwnd)
            except Exception:
                text = None
            if text:
                got_text = True
                nt = norm(text)
                if any(m in nt for m in mine):
                    return True               # un de tes persos reconnu -> on accepte
            if attempt < 2:
                time.sleep(0.20)              # stabilisation avant la lecture suivante
        # jamais rien lu -> on ne bloque pas (defensif) ; texte lu sans match -> externe
        return not got_text

    def _accept_sweep(self):
        """Une passe : detecte et accepte les dialogues a 2 boutons (echange OU
        invitation Oui/Accepter a gauche) sur les fenetres eligibles, en arriere-plan.

        Restriction "mes persos" SANS OCR : on n'accepte que si une de TES fenetres
        affiche le dialogue REQUESTEUR « En attente de la reponse de X » (1 bouton
        orange). C'est la preuve qu'un de tes persos a lance la demande -> interne.
        Sinon (aucune fenetre en attente) -> la demande vient d'un joueur externe."""
        now = time.time()
        eligible = []
        for win in list(self.windows):          # snapshot (detect() peut reassigner)
            if self._is_disabled(win):
                continue
            entry = self.cfg["chars"].get(win["title"], {})
            if not entry.get("focus_echange", 1):
                continue
            eligible.append(win)

        # passe 1 : qui affiche un dialogue Oui/Accepter (2 boutons) ?
        candidates = []
        for win in eligible:
            key = ("pixel_trade", win["hwnd"])
            if now - self._notif_cooldown.get(key, 0.0) < 4.0:
                continue
            try:
                xy = trade_detect.detect_accept(win["hwnd"])
            except Exception:
                xy = None
            if xy:
                candidates.append((win, xy))
        if not candidates:
            return
        self._trade_last_seen = now      # dialogue vu -> garde la cadence rapide (1 s)

        # passe 2 : un de mes persos attend-il une reponse ? (-> demande interne)
        internal = True
        if self.cfg.get("accept_only_mine", True):
            internal = False
            for win in eligible:
                try:
                    if trade_detect.detect_waiting(win["hwnd"]):
                        internal = True
                        break
                except Exception:
                    pass

        # meneur = la fenêtre active au moment de la détection (celle d'où TU as lancé
        # l'échange) -> on y reviendra à la fin, comme pour l'invitation de groupe.
        leader = win32gui.GetForegroundWindow()
        acted = False
        for win, xy in candidates:
            hwnd = win["hwnd"]
            key = ("pixel_trade", hwnd)
            with self._accept_lock:               # reservation atomique anti double-clic
                if now - self._notif_cooldown.get(key, 0.0) < 4.0:
                    continue
                self._notif_cooldown[key] = now   # reserve (interne ou pas) -> pas de re-scan 4s
            if not internal:
                try:
                    self.problemSig.emit("Demande ignorée — externe (aucun de tes persos "
                                         "n'attend de réponse) : %s" % self.name_of(win), "dim")
                except Exception:
                    pass
                continue
            # --- façon invitation : SWITCH sur le receveur -> ACCEPTE (vrai clic) ---
            self._poll_pause_until = time.time() + 8.0     # poll de fond muet pendant la séquence
            if not self._activate_confirm(hwnd):
                continue
            time.sleep(0.06)
            axy = None
            end = time.time() + 1.5                          # le dialogue est déjà là -> court
            while time.time() < end:
                try:
                    axy = trade_detect.detect_accept(hwnd)
                except Exception:
                    axy = None
                if axy:
                    break
                time.sleep(0.10)
            if not axy:
                axy = xy                                     # repli : coords vues en arrière-plan
            try:
                sx, sy = win32gui.ClientToScreen(hwnd, (int(axy[0]), int(axy[1])))
                self._real_click(sx, sy, clicks=1)           # receveur au 1er plan -> vrai clic
            except Exception:
                pass
            self.last_trade_hwnd = hwnd
            self.last_trade_tick = time.time()
            acted = True
            try:
                self.problemSig.emit("Échange accepté : %s" % self.name_of(win), "ok")
            except Exception:
                pass
        # --- retour sur le MENEUR ---
        if acted and leader:
            self._poll_pause_until = time.time() + 0.6
            try:
                win32util.activate(leader)
            except Exception:
                pass

    def _accept_one(self, hwnd, timeout):
        """Attend l'apparition du dialogue Oui/Accepter sur CETTE fenetre et le clique
        (bouton gauche) en arriere-plan des qu'il est detecte. Bloque jusqu'au clic ou
        l'expiration -> permet la sequence stricte invite/accepte/invite/accepte."""
        key = ("pixel_trade", hwnd)
        end = time.time() + max(0.5, timeout)
        while time.time() < end:
            try:
                xy = trade_detect.detect_accept(hwnd)
            except Exception:
                xy = None
            if xy:
                with self._accept_lock:        # reservation atomique (anti double-clic)
                    if time.time() - self._notif_cooldown.get(key, 0.0) < 4.0:
                        return True             # deja accepte (poll de fond)
                    self._notif_cooldown[key] = time.time()
                win32util.background_click(hwnd, xy[0], xy[1])
                self.last_trade_hwnd = hwnd
                self.last_trade_tick = time.time()
                w = self._win_by_hwnd(hwnd)
                try:
                    self.problemSig.emit("Invitation acceptée : %s" % (self.name_of(w) if w else ""), "ok")
                except Exception:
                    pass
                return True
            time.sleep(0.15)
        return False

    def on_global_click(self, x, y):
        # validation AUTO par miroir : tu cliques Accepter sur A -> on clique sur B
        if not self.chk_auto.isChecked():
            return
        if not self.last_trade_hwnd or not win32util.window_alive(self.last_trade_hwnd):
            return
        if time.time() - self.last_trade_tick > 20:
            return
        ax, ay = self.cfg["trade_accept_x"], self.cfg["trade_accept_y"]
        if abs(x - ax) > 40 or abs(y - ay) > 40:
            return
        # ne pas double-cliquer si on est déjà sur la fenêtre cible
        try:
            fg = win32gui.GetForegroundWindow()
            fg_pid = win32process.GetWindowThreadProcessId(fg)[1]
            tgt_pid = win32process.GetWindowThreadProcessId(self.last_trade_hwnd)[1]
            if fg_pid == tgt_pid:
                return
        except Exception:
            pass
        try:                                   # ECRAN -> CLIENT (cf. background_click)
            cx, cy = win32gui.ScreenToClient(self.last_trade_hwnd, (int(ax), int(ay)))
        except Exception:
            cx, cy = ax, ay
        win32util.background_click(self.last_trade_hwnd, cx, cy)
        self.status.setText("Échange valide (auto).")

    def capture(self, target):
        self._capture_target = target
        self._lbtn = True   # avale le clic en cours (celui sur le bouton Capturer)
        self.status.setText("Survole la position et CLIQUE pour la capturer...")

    def _poll_click(self):
        try:
            down = bool(ctypes.windll.user32.GetAsyncKeyState(0x01) & 0x8000)
        except Exception:
            return
        if down and not self._lbtn:
            try:
                x, y = win32api.GetCursorPos()
            except Exception:
                x, y = 0, 0
            if self._capture_target:
                self.on_captured(x, y)
            elif self.move_mode:
                self._move_mode_click()
            else:
                self.on_global_click(x, y)
        self._lbtn = down

    def _move_mode_click(self):
        # clic sur une fenêtre Dofus -> on passe au perso suivant après le délai
        try:
            fg = win32gui.GetForegroundWindow()
        except Exception:
            return
        if fg not in {win["hwnd"] for win in self.windows}:
            return
        now = time.time()
        if now - self._last_move_ts < 0.20:   # anti-rebond
            return
        self._last_move_ts = now
        delay = max(0, int(self.cfg.get("move_delay_ms", 95)))
        QTimer.singleShot(delay, self.go_next)

    def on_captured(self, x, y):
        if self._capture_target == "accept":
            self.acc_x.setText(str(x)); self.acc_y.setText(str(y)); self.save_trade()
        elif self._capture_target == "oui":
            self.oui_x.setText(str(x)); self.oui_y.setText(str(y)); self.save_trade()
        elif self._capture_target and self._capture_target.startswith("actpos:"):
            try:
                n = int(self._capture_target.split(":", 1)[1])
                if 0 <= n < len(self._act_positions):
                    self._act_positions[n] = [x, y]
                    self._act_rebuild_positions()
            except Exception:
                pass
        elif self._capture_target in ("cj1", "cj2", "cj3"):
            n = self._capture_target[-1]
            self.cfg["cj_x" + n] = x
            self.cfg["cj_y" + n] = y
            config.save(self.cfg)
            if hasattr(self, "cj_lbl"):
                self.cj_lbl.setText(self._cj_pos_text())
        elif self._capture_target == "invite_accept":
            self.cfg["invite_accept_x"] = x
            self.cfg["invite_accept_y"] = y
            config.save(self.cfg)
            if hasattr(self, "invite_accept_lbl"):
                self.invite_accept_lbl.setText(self._invite_pos_text())
        elif self._capture_target == "at_name1":
            self.cfg["at_name_x1"] = x; self.cfg["at_name_y1"] = y
            config.save(self.cfg); self._sync_autotrade_ui()
        elif self._capture_target == "at_name2":
            self.cfg["at_name_x2"] = x; self.cfg["at_name_y2"] = y
            config.save(self.cfg); self._sync_autotrade_ui()
        elif self._capture_target == "at_accept":
            self.cfg["at_accept_x"] = x; self.cfg["at_accept_y"] = y
            config.save(self.cfg); self._sync_autotrade_ui()
        self._capture_target = None
        self.status.setText("Position capturée : (%d, %d)" % (x, y))

    # ===================== AutoTrade par image (~0 % CPU) =====================
    def _init_autotrade(self):
        self._at_templates = {}
        self._at_busy = False
        self._at_cooldown = {}     # pseudo -> dernier clic (anti-spam + retry si clic raté)
        self._at_timer = QTimer(self)
        self._at_timer.timeout.connect(self._autotrade_tick)
        try:
            self.overlay.set_autotrade(bool(self.cfg.get("autotrade")))
        except Exception:
            pass
        if self.cfg.get("autotrade"):
            self._start_autotrade()

    def _autotrade_dir(self):
        d = os.path.join(os.path.expanduser("~"), "Documents",
                         "DofusPouletFlemmards", "SCREENSHOT-ECHANGE")
        try:
            os.makedirs(d, exist_ok=True)
        except Exception:
            pass
        return d

    def _load_at_templates(self):
        from . import trade_img
        self._at_templates = {}
        d = self._autotrade_dir()
        try:
            files = [f for f in os.listdir(d) if f.lower().endswith(".png")]
        except Exception:
            files = []
        for f in files:
            arr = trade_img.load_template(os.path.join(d, f))
            if arr is not None:
                self._at_templates[os.path.splitext(f)[0]] = arr
        return len(self._at_templates)

    def toggle_autotrade(self):
        on = not bool(self.cfg.get("autotrade"))
        self.cfg["autotrade"] = on
        config.save(self.cfg)
        if on:
            self._start_autotrade()
        else:
            self._stop_autotrade()

    def _start_autotrade(self):
        from . import trade_img
        if not trade_img.available():
            self.cfg["autotrade"] = False
            config.save(self.cfg)
            try:
                self.overlay.set_autotrade(False)
            except Exception:
                pass
            self._sync_autotrade_ui()
            self.problemSig.emit("warn", "AutoTrade indisponible : numpy manquant. Relance 1-Installer-dependances.bat.")
            return
        n = self._load_at_templates()
        try:
            self.overlay.set_autotrade(True)
        except Exception:
            pass
        self._sync_autotrade_ui()
        interval = max(400, int(self.cfg.get("at_interval_ms", 500)))
        self._at_timer.start(interval)
        if n == 0:
            self.problemSig.emit("warn", "A-Trade ON mais aucun pseudo dans SCREENSHOT-ECHANGE (ajoute des <pseudo>.png).")
        else:
            self.statusSig.emit("A-Trade ON (%d pseudo(s))." % n)

    def _stop_autotrade(self):
        try:
            self._at_timer.stop()
        except Exception:
            pass
        try:
            self.overlay.set_autotrade(False)
        except Exception:
            pass
        self._sync_autotrade_ui()
        self.statusSig.emit("A-Trade OFF.")

    def _autotrade_tick(self):
        """GUI thread : grab de la zone du nom + fenêtre au premier plan.
        Tout le reste (verrou popup + match + bascule) part en thread."""
        if getattr(self, "_at_busy", False):
            return
        from . import trade_img
        fg = win32util.foreground()
        if fg not in {w["hwnd"] for w in self.windows}:
            return                     # premier plan pas une fenêtre Dofus -> rien à faire
        region = trade_img.grab_region(int(self.cfg.get("at_name_x1", 0)), int(self.cfg.get("at_name_y1", 0)),
                                       int(self.cfg.get("at_name_x2", 0)), int(self.cfg.get("at_name_y2", 0)))
        if region is None:
            return
        self._at_busy = True
        threading.Thread(target=self._autotrade_match, args=(region, fg), daemon=True).start()

    def _autotrade_match(self, region, fg):
        """Thread : 1) VERROU — n'agit que si la fenêtre au 1er plan affiche
        « En attente de la réponse de X » (popup côté LANCEUR, spécifique à une demande
        d'échange que TU as lancée). 2) lit le pseudo du receveur. 3) bascule + clic « Oui » + retour.
        Le verrou évite de réagir quand tu passes manuellement sur un receveur (ex. invitation groupe)."""
        from . import trade_img, trade_detect
        try:
            if not trade_detect.detect_waiting(fg):
                return                 # pas le popup « En attente de la réponse de … » -> on ignore
            tol = int(self.cfg.get("at_tol", 20))
            # On évalue TOUS les pseudos (sauf le lanceur) et on garde le MEILLEUR score.
            # Indispensable : avec le fond beige du popup, plusieurs templates passent sous le
            # seuil ; le bon (dont le texte s'aligne) a un score nettement plus bas.
            best_sc, matched, win = 999.0, None, None
            for name, tmpl in list(self._at_templates.items()):
                w = self._match_pseudo(name)
                if not w or w["hwnd"] == fg:
                    continue           # pseudo introuvable, ou c'est le lanceur -> on saute
                sc = trade_img.match_score(region, tmpl)
                if sc is not None and sc < best_sc:
                    best_sc, matched, win = sc, name, w
            if matched is None or best_sc > tol:
                return
            now = time.time()
            if now - self._at_cooldown.get(matched, 0.0) < 2.5:
                return
            ox = int(self.cfg.get("trade_popup_x", 0)); oy = int(self.cfg.get("trade_popup_y", 0))
            if not (ox or oy):
                self.statusSig.emit("A-Trade : position « Oui » non définie (en haut de l'onglet).")
                return
            self._at_cooldown[matched] = now
            self.statusSig.emit("A-Trade : %s -> bascule + clic « Oui »." % matched)
            self._echange_accept_worker(win["hwnd"], fg, ox, oy, self.name_of(win))
        except Exception:
            try:
                self._dbg_exc("autotrade")
            except Exception:
                pass
        finally:
            self._at_busy = False

    def _at_reload_templates(self):
        n = self._load_at_templates()
        self.status.setText("%d pseudo(s) rechargé(s) depuis SCREENSHOT-ECHANGE." % n)
        self._sync_autotrade_ui()

    def _at_diagnose(self):
        """Diagnostic complet de la chaîne A-Trade -> écrit dans l'onglet Debug.
        À lancer PENDANT un échange (pop-up affichée)."""
        from . import trade_img
        self._dbg("=== Diagnostic A-Trade ===", "info")
        self._dbg("numpy dispo : %s" % trade_img.available(), "info")
        # verrou popup « En attente de la réponse de … » sur la fenêtre au premier plan
        try:
            from . import trade_detect
            fg = win32util.foreground()
            waiting = trade_detect.detect_waiting(fg) if fg else False
            self._dbg("Popup « En attente de la réponse de … » au 1er plan : %s%s"
                      % ("OUI ✓" if waiting else "NON",
                         "" if waiting else "  (A-Trade n'agira pas tant que ce popup n'est pas là)"),
                      "ok" if waiting else "warn")
        except Exception as e:
            self._dbg("Verrou popup : illisible (%s)" % e, "error")
        active = bool(self.cfg.get("autotrade"))
        running = bool(getattr(self, "_at_timer", None) and self._at_timer.isActive())
        self._dbg("A-Trade activé : %s  |  timer en marche : %s" % (active, running),
                  "ok" if (active and running) else "warn")
        try:
            from PySide6.QtGui import QGuiApplication
            scr = QGuiApplication.primaryScreen()
            g = scr.geometry()
            self._dbg("Écran : %dx%d  ratio Windows=%.2f  (si ≠ 1.00 -> mise à l'échelle, "
                      "cause probable d'un décalage)" % (g.width(), g.height(), scr.devicePixelRatio()),
                      "warn" if abs(scr.devicePixelRatio() - 1.0) > 0.01 else "info")
        except Exception as e:
            self._dbg("Écran : illisible (%s)" % e, "error")
        n = self._load_at_templates()
        self._dbg("Pseudos chargés : %d -> %s" % (n, ", ".join(self._at_templates.keys()) or "(aucun)"),
                  "ok" if n else "error")
        ox = int(self.cfg.get("trade_popup_x", 0)); oy = int(self.cfg.get("trade_popup_y", 0))
        self._dbg("Position « Oui » (cliquée après bascule) : (%d, %d)" % (ox, oy),
                  "info" if (ox or oy) else "error")
        x1 = int(self.cfg.get("at_name_x1", 0)); y1 = int(self.cfg.get("at_name_y1", 0))
        x2 = int(self.cfg.get("at_name_x2", 0)); y2 = int(self.cfg.get("at_name_y2", 0))
        region = trade_img.grab_region(x1, y1, x2, y2)
        if region is None:
            self._dbg("Zone du nom (%d,%d)->(%d,%d) : capture IMPOSSIBLE" % (x1, y1, x2, y2), "error")
        else:
            rw, rh = region.shape[1], region.shape[0]
            big = rw * rh > 90000   # ~ 300x300 ; au-delà le scan « rien trouvé » devient lourd
            self._dbg("Zone du nom : %dx%d px capturés%s"
                      % (rw, rh, "  ⚠ trop grande pour le CPU, resserre-la autour du pseudo" if big else ""),
                      "warn" if big else "info")
            tol = int(self.cfg.get("at_tol", 20))
            if not self._at_templates:
                self._dbg("  (aucun pseudo à comparer)", "warn")
            for name, tmpl in self._at_templates.items():
                sc = trade_img.match_score(region, tmpl)
                hit = (sc is not None and sc <= tol)
                self._dbg("  %s : template %dx%d  score=%s  (match si ≤ %d) %s"
                          % (name, tmpl.shape[1], tmpl.shape[0],
                             ("%.1f" % sc) if sc is not None else "?", tol,
                             "✓ TROUVÉ" if hit else ""),
                          "ok" if hit else "dim")
        self._dbg("=== fin diagnostic ===", "info")
        self.status.setText("Diagnostic A-Trade terminé -> onglet Debug.")

    def _sync_autotrade_ui(self):
        """Met à jour les libellés de l'onglet Échange si présents (no-op sinon)."""
        if hasattr(self, "_at_sync_labels"):
            try:
                self._at_sync_labels()
            except Exception:
                pass

    def _int(self, edit, default=0):
        try:
            return int(edit.text())
        except Exception:
            return default

    def apply_hotkeys(self):
        self.inputs.apply_all(self.cfg)
        if getattr(self.inputs, "mouse_needed_but_missing", False):
            try:
                self.statusSig.emit("Raccourci souris configuré mais la lib « mouse » est absente "
                                    "— relance 1-Installer-dependances.bat")
            except Exception:
                pass

    def closeEvent(self, event):
        # Croix : si « réduire au lieu de fermer » est coché -> tray. Sinon fermeture complète.
        if (self.cfg.get("close_to_tray", False) and not getattr(self, "_force_quit", False)
                and getattr(self, "tray", None)):
            event.ignore()
            self.hide()
            return
        try:
            self._release_ctrlshift()
            self.inputs.stop()
            self.notifier.stop()
            self.overlay.close()
            if getattr(self, "tray", None):
                self.tray.hide()
        except Exception:
            pass
        super().closeEvent(event)
        QApplication.quit()


def run():
    import sys
    app = QApplication(sys.argv)
    try:
        _theme = config.load().get("theme", "dark")
    except Exception:
        _theme = "dark"
    app.setStyleSheet(build_qss(_theme))
    app.setQuitOnLastWindowClosed(False)   # rester actif quand réduit dans le tray
    try:
        app.setWindowIcon(QIcon(ICON_PATH))
    except Exception:
        pass
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
