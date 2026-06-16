<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="dpf-banner-dark.png">
    <img src="dpf-banner-light.png" alt="DofusPouletFlemmards" width="420">
  </picture>
</p>

<h1 align="center">DofusPouletFlemmards (DPF)</h1>

<p align="center">
  <em>Le tool des flemmards, pour les flemmards.</em><br>
  Assistant de multibox pour <strong>Dofus Retro</strong> — overlay, switch de combat automatique,
  AutoTrade par image, macros, presets, raccourcis & messages.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-3.0.3-7C6CF6">
  <img src="https://img.shields.io/badge/python-3.12.10-blue">
  <img src="https://img.shields.io/badge/OS-Windows-0078D6">
</p>

---

## ✨ Fonctionnalités

### Overlay flottant
Un petit panneau posé au-dessus de Dofus, déplaçable et redimensionnable, avec la liste de tes
persos dans l'ordre, le perso actif surligné, le chrono, et trois interrupteurs :

- **A-Switch** — bascule automatiquement sur la fenêtre dont c'est le tour en combat.
- **A-Skip** — passe le tour automatiquement sur les persos que tu choisis.
- **A-Trade** — accepte les échanges automatiquement (voir plus bas).

Clic sur un pseudo = focus direct sur sa fenêtre. Clic sur le badge **DPF** = afficher/masquer la fenêtre principale.

### A-Switch (focus de combat auto)
Passe sur la bonne fenêtre dès que c'est son tour, **via les notifications Windows de Dofus** (aucune
détection de pixel, donc léger et fiable). Tu peux désactiver le focus par perso.

### A-Trade (AutoTrade par image)
Accepte les demandes d'échange **tout seul**, sans dépendre des notifications (qui sont bugguées sur
les demandes répétées au même perso). DPF lit une petite zone de l'écran : dès qu'il voit le popup
*« En attente de la réponse de &lt;pseudo&gt; »*, il **bascule sur la fenêtre du receveur, clique
« Oui », puis revient sur le lanceur**. Conçu pour consommer quasiment rien (le scan ne tourne que
lorsque le popup est présent).

### Le reste
- **Macros** : une ou plusieurs positions cliquées dans l'ordre, déclenchées par une touche (option boucle).
- **Presets d'ordre (initiative)** : mémorise un ordre de fenêtres, rechargeable par bouton ou raccourci.
- **Raccourcis personnalisés (clavier + souris)** : fenêtre suivante / précédente, retour direct,
  perso favori, valider échange, chrono, overlay, A-Trade… Tu peux aussi assigner la **molette** ou
  un **bouton latéral** de la souris (jamais le clic gauche/droit).
- **Messages par perso** : envoie un message ciblé à une ou plusieurs fenêtres.
- **Invitations de groupe** acceptées automatiquement.
- **Favori ⭐** (un seul à la fois), renommage des persos, réorganisation par glisser-déposer.
- **Thème clair / sombre**, overlay épinglé intelligemment (au-dessus de Dofus uniquement).
- **Export / import** de la configuration, **vérification de mise à jour**, réduction dans la barre système.

---

## 🚀 Installation

> **Prérequis : Windows + Python 3.12.10** (⚠️ surtout pas 3.13 / 3.14, certaines dépendances ne sont
> pas encore compatibles).

1. **Installe Python 3.12.10** :
   👉 https://www.python.org/downloads/release/python-31210/
   (en bas de page : *Windows installer (64-bit)*). **Coche bien « Add python.exe to PATH »** pendant l'installation.

2. **Installe le Visual C++ Redistributable x64** (requis par certaines dépendances comme PySide6 / numpy,
   au cas où il manque sur ta machine) :
   👉 https://aka.ms/vs/17/release/vc_redist.x64.exe

3. **Récupère DPF** : sur la page GitHub, bouton vert **Code → Download ZIP**, puis dézippe.
   (ou `git clone https://github.com/scaryztw/DofusPouletFlemmards`)

4. Double-clique sur **`1-Installer-dependances.bat`** → installe les dépendances Python.

5. Double-clique sur **`2-Lancer-DPF.bat`** → lance DPF. 🎉

### Dépannage
- **Rien ne se lance / fermeture immédiate ?** Lance **`DEBUG-DPF.bat`** : il garde la fenêtre ouverte
  et affiche l'erreur exacte (utile pour le support).
- **Erreur de DLL au lancement** → installe le **VC++ Redistributable x64** (étape 2).
- **`python` introuvable** → réinstalle Python en cochant *Add to PATH*, puis relance `1-Installer-dependances.bat`.

---

## 🎮 Utilisation

1. Lance tes fenêtres **Dofus Retro**, puis DPF.
2. Onglet **Fenêtres** : tes persos sont détectés tout seuls. Renomme, réorganise (glisser-déposer),
   mets-en un en favori ⭐, ou enregistre un **preset d'ordre**.
3. Onglet **Échange** : capture la **Position « Oui »** et **« Accepter »** (survole le bouton dans le
   jeu et clique). Les fenêtres doivent être **empilées au même endroit**.
4. Active **A-Switch / A-Skip / A-Trade** depuis l'overlay (ou les onglets).
5. Crée tes **macros**, **raccourcis** et **messages** dans les onglets dédiés.

### Régler l'A-Trade (par image)
1. Onglet **Échange → AutoTrade par image** → coche **Activer A-Trade**.
2. Mets un fichier **`<pseudo>.png`** par perso dans le dossier `SCREENSHOT-ECHANGE`
   (bouton *Ouvrir le dossier*). Ce sont des captures du **nom du perso** tel qu'il apparaît dans le popup.
   Les mêmes fichiers que la version AHK fonctionnent.
3. Clique **« Sélectionner la zone (glisser) »** et entoure le **nom** dans le popup
   *« En attente de la réponse de … »* (prends large : le texte est centré, sa position bouge selon la
   longueur du pseudo).
4. Vérifie que **Position « Oui »** (en haut) tombe bien sur le bouton « Oui » de la demande.
5. Bouton **« Diagnostic A-Trade »** (pendant un échange) = écrit dans l'onglet **Debug** ce que DPF voit,
   pratique pour régler.

---

## 🧱 Générer un .exe (optionnel)

Double-clique sur **`3-Build-EXE.bat`**. L'exécutable se trouvera dans `dist/DofusPouletFlemmards/`.
Détails : voir **[BUILD-EXE.md](BUILD-EXE.md)**.

---

## 📦 Dépendances

PySide6, pywin32, psutil, keyboard, numpy, et les paquets `winrt-*` (notifications & OCR Windows).
Liste complète : **[requirements.txt](requirements.txt)**.

---

## 💬 Contact & support

Créé par **scaryztw** — Discord : **scaryztw**
GitHub : https://github.com/scaryztw/DofusPouletFlemmards

---

<p align="center"><sub>Projet communautaire, non affilié à Ankama. Utilise-le à tes risques selon les CGU du jeu.</sub></p>
