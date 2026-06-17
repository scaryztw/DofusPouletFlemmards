from .ui_base import *
from .ui_base import _tray_log


class TabRaccourcisMixin:
    def _tab_raccourcis(self):
        w = QWidget()
        lay = QGridLayout(w)
        lay.setVerticalSpacing(10)
        hint = QLabel("Astuce : tu peux aussi assigner la molette ou un bouton latéral "
                      "de la souris (pas le clic gauche/droit).")
        hint.setObjectName("muted"); hint.setWordWrap(True)
        lay.addWidget(hint, 0, 0, 1, 2)
        self.hk = {}
        rows = [("Fenêtre suivante", "hotkey_next", None),
                ("Fenêtre précédente", "hotkey_prev", None),
                ("Retour direct (dernière fenêtre)", "hotkey_back", None),
                ("Personnage principal (favori)", "hotkey_main", None),
                ("Valider échange", "hotkey_validate", None),
                ("Chrono start/pause", "hotkey_timer", None),
                ("Chrono reset", "hotkey_timer_reset", None),
                ("Ctrl + Shift maintenu (ON/OFF)", "hotkey_ctrlshift",
                 "Crée un raccourci ON/OFF qui simule un appui maintenu sur Ctrl + Shift. "
                 "Vous permet de profiter de la sélection rapide à une seule main."),
                ("Afficher / masquer l'overlay", "hotkey_overlay",
                 "Affiche ou masque le petit panneau flottant (overlay) d'une simple touche.")]
        for i, (label, key, tip) in enumerate(rows):
            r = i + 1
            lbl = QLabel(label)
            if tip:
                lbl.setToolTip(tip)
            lay.addWidget(lbl, r, 0)
            e = self._mk_hotkey(self.cfg.get(key, ""))
            if tip:
                e.setToolTip(tip)
            self.hk[key] = e
            lay.addWidget(e, r, 1)
        b_apply = QPushButton("Appliquer + Enregistrer"); b_apply.setObjectName("accent")
        b_apply.clicked.connect(self.apply_raccourcis)
        lay.addWidget(b_apply, len(rows) + 1, 0, 1, 2)
        lay.setRowStretch(len(rows) + 2, 1)
        return w
