# Construire DPF en .exe (pour distribution Discord)

But : produire un exécutable autonome pour que tes utilisateurs n'aient **pas** besoin
d'installer Python ni les dépendances.

## Pré-requis (sur la machine de build, Windows)
- Python 3.10+ installé.
- Les dépendances du projet installées : lance d'abord `1-Installer-dependances.bat`.

## Build
Double-clique **`3-Build-EXE.bat`**.

Le script :
1. installe/maj PyInstaller ;
2. compile en mode **onedir** (dossier), fenêtré (pas de console), avec l'icône ;
3. embarque `dpf-icone.ico`, `dpf-banner-dark.png`, `dpf-banner-light.png` et le paquet `winsdk` (lecture des notifications).

Résultat : `dist\DofusPouletFlemmards\` contenant `DofusPouletFlemmards.exe`.

## Distribution
- Zippe et partage **tout le dossier** `DofusPouletFlemmards` (pas seulement l'exe).
- Au 1er lancement, `dpf_config.json` et les logs (`dpf_notif_log.txt`, etc.) se créent
  **à côté de l'exe** — donc le dossier doit être inscriptible (évite `Program Files`).

## Notes
- **onedir** est volontaire (vs onefile) : démarrage plus rapide, et l'identité d'app
  pour les notifications Windows est plus stable.
- Si les notifications ne sont pas captées sur une machine, vérifier :
  Paramètres > Confidentialité > Notifications (accès autorisé) — le bouton
  **Diagnostic** (onglet Debug) le dit en clair.
- Antivirus : un exe PyInstaller non signé peut déclencher un faux positif. Pour une
  diffusion large, envisager une signature de code (certificat) — sinon prévenir tes
  utilisateurs.
