"""Réglages persistants (JSON, à côté du script). Aucune notion de licence/SWP."""
import json
import os
import sys

if getattr(sys, "frozen", False):
    # .exe PyInstaller : config / logs vivent À CÔTÉ de l'exe (persistants, inscriptibles)
    APP_DIR = os.path.dirname(sys.executable)
    # ...mais les ressources EMBARQUÉES (icône, bannière) sont dans le dossier interne
    RES_DIR = getattr(sys, "_MEIPASS", APP_DIR)
else:
    APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    RES_DIR = APP_DIR
CONFIG_PATH = os.path.join(APP_DIR, "dpf_config.json")

# Version courante de DPF (affichée dans le titre / pied de page).
VERSION = "3.0.3"
# URL de l'API GitHub renvoyant la DERNIÈRE release publiée (champ "tag_name").
# DPF compare ce tag à VERSION pour signaler une mise à jour. Vide ("") = désactivé.
UPDATE_URL = "https://api.github.com/repos/scaryztw/DofusPouletFlemmards/releases/latest"

DEFAULTS = {
    "hotkey_next": "f2",
    "hotkey_prev": "f3",
    "hotkey_back": "f5",            # retour direct (dernière fenêtre)
    "hotkey_main": "f6",            # personnage principal (favori)
    "hotkey_validate": "f4",
    "hotkey_move_mode": "ctrl+z",   # Mode déplacement (toggle)
    "move_delay_ms": 95,            # délai (ms) avant de passer au perso suivant après un clic
    "hotkey_join": "ctrl+j",
    "hotkey_custom_join": "",       # Custom Join (3 positions)
    "custom_join_delay_ms": 100,
    "cj_x1": 0, "cj_y1": 0,         # Rejoindre
    "cj_x2": 0, "cj_y2": 0,         # Prêt (optionnel)
    "cj_x3": 0, "cj_y3": 0,         # Placement lanceur (optionnel)        # Join : Shift+clic DEFILANT (one-shot)
    "join_delay_ms": 100,           # délai (ms) entre chaque fenêtre pour le Join
    "hotkey_invite": "ctrl+i",      # Invite : /invite à tout le groupe
    "invite_accept_x": 0,           # position du bouton Accepter l'invitation
    "invite_accept_y": 0,
    "invite_delay_ms": 120,         # délai entre les frappes /invite
    "invite_accept_delay_ms": 450,  # délai avant de cliquer Accepter
    "hotkey_timer": "",             # overlay : start/pause chrono
    "hotkey_timer_reset": "",       # overlay : reset chrono
    "hotkey_autoskip": "",          # toggle global AutoSkip
    "autoskip": False,              # AutoSkip global ON/OFF
    "hotkey_autofocus": "",         # toggle global AutoFocus
    "hotkey_ctrlshift": "",         # ON/OFF : maintient Ctrl+Shift (selection rapide 1 main)
    "hotkey_overlay": "",           # afficher / masquer l'overlay
    "autofocus": True,              # AutoFocus global ON/OFF (switch auto en combat/échange)
    "skip_key": "s",                # touche envoyée pour passer le tour
    "skip_delay_ms": 120,           # délai avant d'envoyer la touche skip
    "preset_hotkeys": {},           # nom de preset -> raccourci
    "remove_banner": True,          # supprimer la bannière/notif Windows dès son apparition
    "accept_only_mine": True,       # n'accepter echange/invite que si l'emetteur est un de mes persos (OCR)
    "maximize_on_launch": False,    # agrandir les fenêtres Dofus au lancement
    "trade_popup_x": 0,         # position du bouton « Oui » (popup d'acceptation de la demande)
    "trade_popup_y": 0,
    "trade_accept_x": 0,        # position du bouton « Accepter » (validation finale de l'échange)
    "trade_accept_y": 0,
    "auto_validate": True,      # valide B quand tu valides A (miroir de clic)
    "trade_switch_accept": True,  # accepte l'échange en basculant sur le perso (comme l'invite)
    # --- AutoTrade par image (independant des notifications, calque sur l'AHK) ---
    "autotrade": False,             # A-Trade ON/OFF
    "autotrade_hotkey": "",         # raccourci optionnel pour basculer A-Trade
    "at_name_x1": 690, "at_name_y1": 395,    # zone du nom dans la pop-up (coords ecran)
    "at_name_x2": 1240, "at_name_y2": 435,
    "at_accept_x": 1413, "at_accept_y": 751,  # bouton Accepter (coords ecran)
    "at_accept_r": 0, "at_accept_g": 97, "at_accept_b": 255,  # couleur du bouton (gate)
    "at_tol": 20,                   # seuil de match du pseudo (plus petit = plus strict)
    "at_interval_ms": 500,          # cadence du verrou quand A-Trade est ON
    "always_on_top": True,      # garder la fenêtre DPF au-dessus (pratique pour régler les positions)
    "close_to_tray": False,     # croix -> réduire dans le tray au lieu de quitter
    "minimize_to_tray": False,  # réduire -> aller dans le tray au lieu de la barre des tâches
    "overlay": True,
    "overlay_scale": 1.0,           # taille de l'overlay (1.0 = normal ; réglable)
    "theme": "dark",                # thème de l'interface : "dark" ou "light"
    "debug": False,                 # journal de debug des notifications (onglet Debug)
    "welcome_shown": False,         # popup de bienvenue deja affiche ?
    "overlay_x": None,              # position sauvegardee de l'overlay
    "overlay_y": None,
    "messages": [               # messages de chat (cible reglable par message)
        {"text": "", "hotkey": "", "auto": False, "interval": 30, "target": "active"},
        {"text": "", "hotkey": "", "auto": False, "interval": 30, "target": "active"},
        {"text": "", "hotkey": "", "auto": False, "interval": 30, "target": "active"},
    ],
    "msg_return": True,         # revenir a la fenetre d'origine apres l'envoi d'un message
    "order": [],                # liste de "clés perso" (titre de fenêtre) dans l'ordre
    "presets": {},              # nom -> [titres dans l'ordre] (ex. "Team Cra")
    "chars": {},                # clé perso -> {"name", "focus_combat", "focus_trade", "favori"}
    "actions": [],              # [{"name","positions":[[x,y],..],"clicks","delay_ms","hotkey","target","auto","interval_s"}]
}


def load():
    data = dict(DEFAULTS)
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        if isinstance(loaded, dict):
            data.update(loaded)
    except Exception:
        pass
    # garantit les sous-dictionnaires
    if not isinstance(data.get("chars"), dict):
        data["chars"] = {}
    if not isinstance(data.get("order"), list):
        data["order"] = []
    if not isinstance(data.get("presets"), dict):
        data["presets"] = {}
    if not isinstance(data.get("preset_hotkeys"), dict):
        data["preset_hotkeys"] = {}
    if not isinstance(data.get("actions"), list):
        data["actions"] = []
    # --- migration des actions vers le modele "macro" (positions multiples) ---
    fixed = []
    for a in data["actions"]:
        if not isinstance(a, dict):
            continue
        if not isinstance(a.get("positions"), list) or not a["positions"]:
            # ancien format {x, y} -> une seule position
            x, y = int(a.get("x", 0) or 0), int(a.get("y", 0) or 0)
            a["positions"] = [[x, y]] if (x or y) else []
        # normalise les positions en [x, y] entiers
        pos = []
        for p in a["positions"]:
            try:
                pos.append([int(p[0]), int(p[1])])
            except Exception:
                pass
        a["positions"] = pos
        a.setdefault("clicks", 1)             # 1 = simple, 2 = double
        a.setdefault("delay_ms", 120)         # delai entre clics/positions
        a.setdefault("target", "active")      # "active" | "all"
        a.setdefault("hotkey", "")
        a.setdefault("auto", False)           # repetition auto (optionnel)
        a.setdefault("interval_s", 30)        # intervalle si auto
        a.setdefault("name", "Action")
        a.pop("x", None); a.pop("y", None)
        fixed.append(a)
    data["actions"] = fixed
    if not isinstance(data.get("messages"), list):
        data["messages"] = [{"text": "", "hotkey": ""} for _ in range(3)]
    for m in data["messages"]:
        if isinstance(m, dict):
            m.setdefault("target", "active")
    return data


def save(data):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print("[config] sauvegarde impossible :", e)
