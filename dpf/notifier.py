"""
Ecouteur de notifications Windows (autofocus combat / échange / groupe).

Approche IDENTIQUE a Dracoon :
  - winsdk (WinRT) en Python, IN-PROCESS (pas de PowerShell, pas de fenêtre cmd),
  - UserNotificationListener event-driven (détection instantanee) + repli polling,
  - dedup par seen_ids : chaque notification est traitee UNE seule fois par son id
    (pas de fenêtre de temps) -> fiable a l'infini,
  - suppression de la bannière via remove_notification(id).

Repli : si winsdk n'est pas installe, on retombe sur l'ancien ecouteur PowerShell.
Le signal emet (pseudo, body, ntype) avec ntype dans {combat, échange, groupe}.
"""
import os
import re
import asyncio
import threading
import subprocess

from PySide6.QtCore import QObject, Signal, QTimer

from . import config

try:
    # comme Dracoon (Python 3.11/3.12/3.13)
    import winsdk.windows.ui.notifications.management as winman
    import winsdk.windows.ui.notifications as winnot
    WINSDK_OK = True
except Exception:
    try:
        # variante moderne (wheels Python 3.14) — même API
        import winrt.windows.ui.notifications.management as winman
        import winrt.windows.ui.notifications as winnot
        WINSDK_OK = True
    except Exception:
        WINSDK_OK = False

APP_DIR = config.APP_DIR
TURN_FILE = os.path.join(APP_DIR, "dpf_turn.txt")
PS_FILE = os.path.join(APP_DIR, "dpf_notif.ps1")
LOG_FILE = os.path.join(APP_DIR, "dpf_notif_log.txt")

TITLE_PATTERN = re.compile(r"^(.+?)\s*-\s*Dofus", re.IGNORECASE)

NOTIF_TYPES = [
    ("combat", [
        re.compile(r"de jouer", re.IGNORECASE),
        re.compile(r"turn to play", re.IGNORECASE),
        re.compile(r"toca jugar", re.IGNORECASE),
    ]),
    ("groupe", [
        re.compile(r"invite .+rejoindre", re.IGNORECASE),
        re.compile(r"invites you to join", re.IGNORECASE),
        re.compile(r"invita a unirte", re.IGNORECASE),
    ]),
    # Échange : on RE-détecte par notification (l'acceptation clique une position
    # enregistrée par l'utilisateur, plus de recherche du bouton orange).
    # NB : Windows peut étouffer un 2e toast IDENTIQUE consécutif (même paire A->B) ;
    # dans ce cas rare l'échange ne sera pas auto-accepté.
    ("echange", [
        re.compile(r"propose.{0,30}change", re.IGNORECASE),   # "... te propose de faire un échange"
        re.compile(r"propose.{0,30}trade", re.IGNORECASE),    # EN
        re.compile(r"wants to trade", re.IGNORECASE),
        re.compile(r"offers .{0,6}trade", re.IGNORECASE),
    ]),
]


def _classify(body):
    for tk, pats in NOTIF_TYPES:
        if any(p.search(body or "") for p in pats):
            return tk
    return None


def extract_pseudo(title):
    m = TITLE_PATTERN.match(title or "")
    return m.group(1).strip() if m else (title or "").strip()


def _log(msg):
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(str(msg) + "\n")
    except Exception:
        pass


# ===========================================================================
#  Notifier winsdk (comme Dracoon)
# ===========================================================================
class Notifier(QObject):
    # (pseudo, body, ntype)  ntype = combat | échange | groupe
    event = Signal(str, str, str)
    # (message, niveau)  niveau = info | ok | warn | error  -> remonte vers l'onglet Debug
    problem = Signal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._remove = True
        self._running = False
        self._thread = None
        self._loop = None
        self._ps = _PSNotifier(self)   # repli
        # état exposé pour le Diagnostic
        self.access_ok = None          # True/False/None (inconnu)
        self.mode = "?"                # "event" | "polling" | "powershell" | "?"

    def _report(self, msg, level="info"):
        _log(msg)
        try:
            self.problem.emit(msg, level)
        except Exception:
            pass

    def start(self, remove_banner=True):
        self._remove = bool(remove_banner)
        if self._running:
            return
        self._running = True
        # winsdk IN-PROCESS en priorite : le log de l'utilisateur prouve qu'il capte
        # 100% des notifs de combat sur sa machine. (Repli PowerShell si winsdk absent.)
        if WINSDK_OK:
            try:
                open(LOG_FILE, "w", encoding="utf-8").write("STARTED winsdk listener\n")
            except Exception:
                pass
            self._thread = threading.Thread(target=self._run, daemon=True, name="DPFNotif")
            self._thread.start()
        elif self._ps.start(remove_banner):
            self.mode = "powershell"
            self._report("Auto-switch : écouteur PowerShell actif (repli).", "ok")
        else:
            self._report("Aucun écouteur de notifications disponible.", "error")

    def set_remove_banner(self, val):
        self._remove = bool(val)
        # si l'ecouteur PowerShell tourne, on le relance avec la nouvelle valeur
        if self._ps._proc is not None:
            self._ps.set_remove_banner(val)

    def stop(self):
        self._running = False
        try:
            if self._loop and self._loop.is_running():
                self._loop.call_soon_threadsafe(lambda: None)
        except Exception:
            pass
        self._ps.stop()

    # ---- thread asyncio ----
    def _run(self):
        import ctypes
        com_ok = False
        try:
            # Donne une IDENTITE au process (AppUserModelID). Sans identite de package,
            # listener.add_notification_changed() echoue avec ERROR_NOT_FOUND et on est
            # condamne au polling. Cet AUMI explicite peut debloquer l'event-driven
            # (detection instantanee -> plus aucune notif de combat ratee).
            try:
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                    ctypes.c_wchar_p("DofusPouletFlemmards.DPF"))
            except Exception:
                pass
            # Initialise le thread en STA (mode appartement) : sans ca, sur certaines
            # configs Windows 11, UserNotificationListener echoue silencieusement / leve
            # des erreurs COM. (Merci au retour de la communaute Dracoon/akididou.)
            try:
                hr = ctypes.windll.ole32.CoInitializeEx(None, 0x2)  # COINIT_APARTMENTTHREADED
                com_ok = True
                self._report("COM initialise en STA (CoInitializeEx hr=0x%X)." % (hr & 0xFFFFFFFF), "ok")
            except Exception as ce:
                self._report("CoInitializeEx a echoue : %r (le listener peut planter)." % ce, "warn")
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._loop.run_until_complete(self._listen())
        except Exception as e:
            self._report("Listener notifications plante : %r" % e, "error")
        finally:
            if com_ok:
                try:
                    ctypes.windll.ole32.CoUninitialize()
                except Exception:
                    pass

    async def _listen(self):
        listener = winman.UserNotificationListener.current
        access = await listener.request_access_async()
        if access != winman.UserNotificationListenerAccessStatus.ALLOWED:
            self.access_ok = False
            self._report("Acces aux notifications REFUSE. Active-les : Paramètres > Système > "
                         "Notifications, et Confidentialité > Notifications.", "error")
            return
        self.access_ok = True
        self._report("Acces aux notifications accorde.", "ok")

        seen_ids = set()
        seen_logged = set()   # diagnostic : nids deja traces en SEEN (jamais vide -> 1 ligne/nid)
        evt = asyncio.Event()
        use_events = False

        def on_changed(sender, args):
            try:
                if self._loop and self._loop.is_running():
                    self._loop.call_soon_threadsafe(evt.set)
            except Exception:
                pass

        try:
            listener.add_notification_changed(on_changed)
            use_events = True
            self.mode = "event"
            self._report("Mode event-driven actif (détection instantanée).", "ok")
        except Exception as e:
            self.mode = "polling"
            self._report("Mode polling actif (0.10 s) — event-driven indisponible : %r" % e, "warn")

        _acc_tick = 0
        while self._running:
            if use_events:
                try:
                    await asyncio.wait_for(evt.wait(), timeout=0.10)
                except asyncio.TimeoutError:
                    pass
                except asyncio.CancelledError:
                    break
                evt.clear()
            else:
                try:
                    await asyncio.sleep(0.10)
                except asyncio.CancelledError:
                    break

            # re-verifie l'acces aux notifications ~toutes les 2 s (l'utilisateur peut
            # le revoquer en cours de route -> le Diagnostic doit refleter l'etat REEL)
            _acc_tick += 1
            if _acc_tick >= 20:
                _acc_tick = 0
                try:
                    st = listener.get_access_status()
                    self.access_ok = (st == winman.UserNotificationListenerAccessStatus.ALLOWED)
                except Exception:
                    pass

            try:
                notifs = await listener.get_notifications_async(
                    winnot.NotificationKinds.TOAST)
                self._getnotif_warned = False
            except Exception as e:
                if not getattr(self, "_getnotif_warned", False):
                    self._getnotif_warned = True
                    self._report("Lecture des notifications en erreur : %r "
                                 "(le listener réessaie)." % e, "warn")
                continue

            for notif in notifs:
                try:
                    nid = notif.id
                except Exception:
                    continue

                # --- extraction titre/corps TOT (pour le diagnostic SEEN) ---
                title = body = ""
                try:
                    binding = notif.notification.visual.get_binding(
                        winnot.KnownNotificationBindings.toast_generic)
                    if binding is not None:
                        elements = [e.text for e in binding.get_text_elements()]
                        if elements:
                            title = elements[0]
                            body = elements[1] if len(elements) > 1 else ""
                except Exception:
                    pass

                # DIAGNOSTIC : trace TOUTE notif livree par Windows, une fois par nid.
                # Si un tour rate n'apparait PAS ici -> Windows ne l'a pas livree (throttling).
                # S'il apparait ici mais sans NOTIF -> c'est la deduplication (corrigeable).
                if nid not in seen_logged:
                    seen_logged.add(nid)
                    _log("SEEN id=%s ti=[%s] bd=[%s]" % (nid, title, body))

                if nid in seen_ids:
                    continue
                seen_ids.add(nid)

                if self._remove:
                    try:
                        listener.remove_notification(nid)
                    except Exception:
                        pass
                    seen_ids.discard(nid)   # TOUJOURS oublier (meme si remove echoue)
                                            # -> un meme nid reutilise plus tard sera retraite

                if not title and not body:
                    continue
                ntype = _classify(body)
                if ntype is None:
                    if title and " " not in title.strip():
                        _log("NOTIF non reconnue : %s | %s" % (title, body))
                    continue
                pseudo = extract_pseudo(title)
                _log("NOTIF [%s] %s -> %s" % (ntype, pseudo, body))
                try:
                    self.event.emit(pseudo or "", body or "", ntype)
                except Exception:
                    pass

            if len(seen_ids) > 800:
                seen_ids = set(list(seen_ids)[-300:])
            if len(seen_logged) > 1500:
                seen_logged = set(list(seen_logged)[-400:])


# ===========================================================================
#  Repli PowerShell (si winsdk absent) — emet le même signal
# ===========================================================================
PS_SCRIPT = r'''
$ErrorActionPreference='SilentlyContinue'
$m=New-Object System.Threading.Mutex($false,'Global\DPF_Python_NotifListener')
if(-not $m.WaitOne(0)){exit}
$log='{DIR}dpf_notif_log.txt'
$out='{DIR}dpf_turn.txt'
'STARTED '+(Get-Date) | Set-Content $log -Encoding UTF8
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$ag=([System.WindowsRuntimeSystemExtensions].GetMethods()|?{$_.Name-eq'AsTask'-and$_.GetParameters().Count-eq 1-and$_.GetParameters()[0].ParameterType.Name-eq'IAsyncOperation`1'})[0]
function Aw($t,$r){$a=$ag.MakeGenericMethod($r);$n=$a.Invoke($null,@($t));$n.Wait(-1)|Out-Null;$n.Result}
[void][Windows.UI.Notifications.Management.UserNotificationListener,Windows.UI.Notifications,ContentType=WindowsRuntime]
[void][Windows.UI.Notifications.UserNotification,Windows.UI.Notifications,ContentType=WindowsRuntime]
$l=[Windows.UI.Notifications.Management.UserNotificationListener]::Current
$acc=Aw $l.RequestAccessAsync() ([Windows.UI.Notifications.Management.UserNotificationListenerAccessStatus]);('ACCESS='+$acc)|Add-Content $log
$seen=@{};$errLogged=$false
while($true){
  try{
    $ns=Aw $l.GetNotificationsAsync(1) ([System.Collections.Generic.IReadOnlyList[Windows.UI.Notifications.UserNotification]])
    foreach($n in $ns){
      $key=[string]$n.Id+'_'+$n.CreationTime.UtcTicks;$now=[DateTime]::Now.Ticks
      if($seen.ContainsKey($key) -and ($now-$seen[$key]) -lt 30000000){continue}
      $seen[$key]=$now
      $tx=@($n.Notification.Visual.Bindings[0].GetTextElements()|%{$_.Text})
      $ti=if($tx.Count-ge 1){$tx[0]}else{''}
      $bd=if($tx.Count-ge 2){($tx[1..($tx.Count-1)]-join' ')}else{''}
      ('SEEN ti=['+$ti+'] bd=['+$bd+']')|Add-Content $log
      if($bd-match'de jouer'-or$bd-match'change'-or$bd-match'propose'-or$ti-match'de jouer'){
        ($ti+'|'+$bd+'|'+[DateTime]::Now.Ticks)|Set-Content $out -Encoding UTF8
        ('NOTIF='+$ti+' / '+$bd)|Add-Content $log
        if({REMOVE}){try{$l.RemoveNotification($n.Id)}catch{}}
      }
      if($seen.Count-gt 300){$seen=@{}}
    }
  }catch{if(-not $errLogged){('ERR '+$_)|Add-Content $log;$errLogged=$true}}
  Start-Sleep -Milliseconds 250
}'''


class _PSNotifier:
    def __init__(self, owner):
        self._owner = owner
        self._proc = None
        self._last = ""
        self._timer = QTimer(owner)
        self._timer.timeout.connect(self._poll)

    def start(self, remove_banner=True):
        try:
            ps_dir = APP_DIR
            if not ps_dir.endswith(os.sep):
                ps_dir += os.sep
            script = (PS_SCRIPT.replace("{DIR}", ps_dir)
                      .replace("{REMOVE}", "$true" if remove_banner else "$false"))
            with open(PS_FILE, "w", encoding="utf-8") as f:
                f.write(script)
            self._proc = subprocess.Popen(
                ["powershell.exe", "-WindowStyle", "Hidden", "-NoProfile",
                 "-ExecutionPolicy", "Bypass", "-File", PS_FILE],
                creationflags=0x08000000)
        except Exception as e:
            _log("repli PS impossible : %r" % e)
            self._proc = None
            return False
        try:
            if os.path.exists(TURN_FILE):
                self._last = open(TURN_FILE, "r", encoding="utf-8-sig", errors="ignore").read()
        except Exception:
            self._last = ""
        self._timer.start(120)
        return True

    def set_remove_banner(self, val):
        # le script PS fige l'option REMOVE a son lancement -> on relance pour l'appliquer
        self.stop()
        self.start(val)

    def stop(self):
        self._timer.stop()
        if self._proc:
            try:
                self._proc.terminate()
            except Exception:
                pass
            self._proc = None

    def _poll(self):
        try:
            data = open(TURN_FILE, "r", encoding="utf-8-sig", errors="ignore").read()
        except Exception:
            return
        if not data or data == self._last:
            return
        self._last = data
        parts = data.split("|")
        if len(parts) < 2:
            return
        title, body = parts[0].strip(), parts[1].strip()
        ntype = _classify(body) or ("echange" if any(
            h in (body + " " + title).lower() for h in ("change", "propose", "echange", "échange")) else "combat")
        self._owner.event.emit(extract_pseudo(title), body, ntype)
