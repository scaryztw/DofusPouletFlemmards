from .ui_base import *
from .ui_base import _tray_log


class TabDebugMixin:
    def _tab_debug(self):
        from PySide6.QtGui import QFont
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.addWidget(QLabel(
            "Debug : ici s'affichent les notifications détectées ET tous les problèmes que DPF "
            "rencontre (accès notifications, COM/STA, erreurs internes…). "
            "Coche « Tout afficher » pour voir aussi la trace des notifications. "
            "Les erreurs et avertissements s'affichent toujours, même décoché."))
        top = QHBoxLayout()
        self.dbg_on = QCheckBox("Tout afficher (notifications)")
        self.dbg_on.setChecked(bool(self.cfg.get("debug", False)))
        self.dbg_on.stateChanged.connect(self._dbg_toggle)
        b_clear = QPushButton("Effacer"); b_clear.clicked.connect(lambda: self.dbg_view.clear())
        b_log = QPushButton("Ouvrir le fichier log"); b_log.clicked.connect(self._open_notif_log)
        b_diag = QPushButton("Diagnostic"); b_diag.setObjectName("accent")
        b_diag.clicked.connect(self.run_diagnostic)
        top.addWidget(self.dbg_on); top.addStretch(); top.addWidget(b_diag); top.addWidget(b_clear); top.addWidget(b_log)
        lay.addLayout(top)

        self.dbg_view = QPlainTextEdit(); self.dbg_view.setReadOnly(True)
        self.dbg_view.setMaximumBlockCount(800)   # garde les 800 dernieres lignes
        self.dbg_view.setObjectName("dbgview")
        try:
            self.dbg_view.setFont(QFont("Consolas", 9))
        except Exception:
            pass
        lay.addWidget(self.dbg_view, 1)
        return w

    def _stats_refresh(self):
        if not hasattr(self, "stats_lbl"):
            return
        import time as _t
        s = getattr(self, "_stats", None)
        if not s:
            self.stats_lbl.setText("—")
            return
        dur = max(0, int(_t.time() - s.get("session_start", _t.time())))
        h, rem = divmod(dur, 3600); m, sec = divmod(rem, 60)
        durtxt = ("%dh%02dm" % (h, m)) if h else ("%dm%02ds" % (m, sec))
        self.stats_lbl.setText("%d combat(s)   ·   %s" % (s.get("combats", 0), durtxt))

    def _stats_reset(self):
        import time as _t
        self._stats = {"turns": 0, "combats": 0, "session_start": _t.time(),
                       "last_turn": 0.0, "per_char": {}}
        self._stats_refresh()

    def _dbg_exc(self, context=""):
        """À appeler DANS un bloc except : trace l'exception courante, mais
        uniquement quand « Tout afficher » est coché (sinon silencieux comme avant)."""
        if not (hasattr(self, "dbg_on") and self.dbg_on.isChecked()):
            return
        try:
            import traceback
            line = traceback.format_exc().strip().splitlines()[-1]
        except Exception:
            line = "?"
        self._dbg_write("⚠ exception (%s) : %s" % (context, line), "error", force=True)

    def _dbg_toggle(self):
        self.cfg["debug"] = bool(self.dbg_on.isChecked())
        config.save(self.cfg)
        if self.cfg["debug"]:
            self._dbg("Tout afficher activé — en attente de notifications…", "ok")

    def _open_notif_log(self):
        path = os.path.join(config.APP_DIR, "dpf_notif_log.txt")
        try:
            os.startfile(path)          # Windows
        except Exception:
            self.status.setText("Log : %s" % path)

    def _dbg_write(self, msg, tag="info", force=False):
        """Ecrit une ligne dans le journal Debug. force=True -> toujours (problemes)."""
        if not hasattr(self, "dbg_view"):
            return
        if not force and not (hasattr(self, "dbg_on") and self.dbg_on.isChecked()):
            return
        colors = {"info": "#cfcabb", "ok": "#7fd18a", "error": "#e06c6c",
                  "dim": "#7a8290", "warn": "#EF9F27"}
        col = colors.get(tag, "#cfcabb")
        ts = time.strftime("%H:%M:%S")
        safe = (msg or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        self.dbg_view.appendHtml(
            "<span style='color:#566'>%s</span> <span style='color:%s'>%s</span>" % (ts, col, safe))

    def _dbg(self, msg, tag="info"):
        """Trace de notification : visible seulement si « Tout afficher » est coché."""
        self._dbg_write(msg, tag, force=False)

    def _on_problem(self, msg, tag="error"):
        """Slot (thread GUI) : un probleme remonte -> toujours affiche + barre de statut."""
        self._dbg_write(msg, tag, force=True)
        if tag in ("error", "warn"):
            try:
                self.status.setText(msg[:140])
            except Exception:
                pass

    def _report(self, msg, tag="error"):
        """Signale un probleme depuis n'importe quel thread (thread-safe)."""
        try:
            self.problemSig.emit(msg, tag)
        except Exception:
            pass

    def _install_excepthooks(self):
        """Capture les erreurs non gérées (thread principal + threads) vers le Debug."""
        import sys
        import threading as _th
        _old_sys = sys.excepthook

        def _sys_hook(et, ev, tb):
            try:
                self._report("Erreur non gérée : %s: %s" % (et.__name__, ev), "error")
            except Exception:
                pass
            _old_sys(et, ev, tb)
        sys.excepthook = _sys_hook

        if hasattr(_th, "excepthook"):
            _old_th = _th.excepthook

            def _th_hook(args):
                try:
                    self._report("Erreur dans un thread (%s) : %s: %s"
                                 % (getattr(args.thread, "name", "?"),
                                    args.exc_type.__name__, args.exc_value), "error")
                except Exception:
                    pass
                _old_th(args)
            _th.excepthook = _th_hook
