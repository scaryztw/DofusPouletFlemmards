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
  AutoTrade par image, switch sur MP reçu, enregistreur de macros, presets, raccourcis, messages
  & actualités du jeu.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-4.0.0-7C6CF6">
  <img src="https://img.shields.io/badge/python-3.12.10-blue">
  <img src="https://img.shields.io/badge/langues-FR%20%7C%20EN%20%7C%20ES%20%7C%20DE%20%7C%20PT-success">
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
L'overlay reste épinglé au-dessus de Dofus de manière fiable (ré-épinglage auto si Windows le décroche).

### A-Switch (focus de combat auto)
Passe sur la bonne fenêtre dès que c'est son tour, **via les notifications Windows de Dofus** (aucune
détection de pixel, donc léger et fiable). Le focus est réglable **par perso** (colonne *Focus Combat*).

### A-Trade (AutoTrade par image)
Accepte les demandes d'échange **tout seul**, sans dépendre des notifications (qui sont bugguées sur
les demandes répétées au même perso). DPF lit une petite zone de l'écran : dès qu'il voit le popup
*« En attente de la réponse de &lt;pseudo&gt; »*, il **bascule sur la fenêtre du receveur, valide avec
Entrée, puis revient sur le lanceur**. Conçu pour consommer quasiment rien (le scan ne tourne que
lorsque le popup est présent).

- **Liste blanche par perso** (colonne *A-Trade* dans l'onglet Comptes) : choisis **quels persos**
  acceptent auto les échanges (ex. seulement ta mule). Les persos décochés ne déclenchent **aucun switch**.
- **Exclusion des défis et des invitations de groupe** : un défi ou une invitation de groupe (même bouton
  orange qu'un échange) ne déclenche plus l'A-Trade par erreur.

### 📰 Actualités Dofus Retro *(nouveau en v4)*
Un onglet dédié qui affiche **les dernières actualités officielles de la semaine**, récupérées
directement du site Dofus Retro :

- Liste des news des **7 derniers jours** (repli sur les plus récentes s'il n'y a rien cette semaine),
  avec le nombre affiché dans le titre.
- **Lecture de l'article complet dans l'app** (accordéon) : **texte intégral + toutes les images**,
  préchargées pour un affichage net, sans saut, et sans ouvrir le navigateur.
- Bouton **« Ouvrir le site »** pour la version web (commentaires, etc.).
- **Suit la langue de DPF** : FR / EN / ES / PT (l'allemand bascule sur l'anglais, le site n'existant
  qu'en 4 langues).
- DPF **s'ouvre directement sur cet onglet** au lancement.

### 💬 Switch sur MP reçu
Quand un de tes persos reçoit un **message privé**, DPF **bascule automatiquement sur sa fenêtre**.
Activable **par perso** via la colonne *Focus MP* (onglet Comptes). Fonctionne via les notifications
Windows, comme l'A-Switch de combat.

### 🔴 Enregistreur de macro
Dans l'onglet **Actions**, le bouton **« Rec »** capture tes positions automatiquement : clique Rec,
puis clique **en jeu** chaque position dans l'ordre — fini l'ajout une par une. (Les clics dans la
fenêtre DPF sont ignorés, donc cliquer « Stop » ne crée pas de position parasite.)

### 🌍 Multilingue (5 langues)
Interface complète en **Français, English, Español, Deutsch, Português** — y compris les infobulles,
les messages de statut et le Diagnostic. Change la langue dans **Paramètres → Affichage** (DPF
redémarre tout seul pour l'appliquer). Les **actualités** suivent aussi la langue choisie.

### Le reste
- **Macros** : une ou plusieurs positions cliquées dans l'ordre, déclenchées par une touche (option boucle).
- **Presets d'ordre (initiative)** : mémorise un ordre de fenêtres, rechargeable par bouton ou raccourci.
- **Raccourcis personnalisés (clavier + souris)** : fenêtre suivante / précédente, retour direct,
  perso favori, valider échange, chrono, overlay, A-Trade, touche « passer le tour »… Tu peux aussi
  assigner la **molette** ou un **bouton latéral** de la souris (jamais le clic gauche/droit).
- **Messages par perso** : envoie un message ciblé à une ou plusieurs fenêtres.
- **Invitations de groupe** acceptées automatiquement (via Entrée, plus aucune position à capturer).
- **Favori ⭐** (un seul à la fois), **alias d'affichage** des persos (ne touche pas au nom dans Dofus),
  réorganisation par glisser-déposer.
- **Diagnostic + état de santé** : l'onglet Debug vérifie en un coup d'œil ce qui cloche (numpy/A-Trade,
  accès notifications, fenêtres détectées, position « Accepter », pseudos A-Trade). Bouton
  **« Copier le diagnostic »** pour l'envoyer facilement au support.
- **Thème clair / sombre** + **couleur d'accent personnalisable** (boutons, surbrillances…),
  overlay épinglé intelligemment (au-dessus de Dofus uniquement).
- **Export / import** de la configuration, **notification de mise à jour** (popup avec lien GitHub),
  réduction & **redémarrage** depuis la barre système.

---

## 📥 Installation

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

1. Lance tes fenêtres **Dofus Retro**, puis DPF. DPF s'ouvre sur l'onglet **Actualités** ;
   passe sur **Fenêtres** pour piloter tes persos.
2. Onglet **Fenêtres** : tes persos sont détectés tout seuls. Renomme (alias d'affichage), réorganise
   (glisser-déposer), mets-en un en favori ⭐, ou enregistre un **preset d'ordre**.
3. Onglet **Comptes** : règle par perso le **Focus Combat**, le **Focus Échange**, l'**Auto-Skip**,
   la **liste blanche A-Trade** et le **Focus MP**.
4. Active **A-Switch / A-Skip / A-Trade** depuis l'overlay (ou les onglets).
5. Crée tes **macros** (avec l'enregistreur **Rec**), **raccourcis** et **messages** dans les onglets dédiés.

> 💡 Les **acceptations** (échanges, invitations de groupe) se font désormais via la touche **Entrée** :
> aucune position « Oui » à capturer.

### Régler l'A-Trade (par image)
1. Onglet **Échange → AutoTrade par image** → coche **Activer A-Trade**.
2. Mets un fichier **`<pseudo>.png`** par perso dans le dossier `SCREENSHOT-ECHANGE`
   (bouton *Ouvrir le dossier*). Ce sont des captures du **nom du perso** tel qu'il apparaît dans le popup.
   > ⚠️ **Refais tes captures directement via DPF et supprime les anciennes** (notamment celles de la
   > version AHK) : elles ne sont plus garanties compatibles.
3. Clique **« Sélectionner la zone (glisser) »** et entoure le **nom** dans le popup
   *« En attente de la réponse de … »* (prends large : le texte est centré, sa position bouge selon la
   longueur du pseudo).
4. (Optionnel) Capture la **Position « Accepter »** en haut de l'onglet si tu utilises la **validation
   automatique** de l'échange (DPF clique « Accepter » sur l'autre fenêtre quand tu valides la tienne).
5. Dans l'onglet **Comptes**, coche la colonne **A-Trade** uniquement pour les persos qui doivent accepter.
6. Bouton **« Diagnostic A-Trade »** (pendant un échange) = écrit dans l'onglet **Debug** ce que DPF voit,
   pratique pour régler. Bouton **« Copier le diagnostic »** pour l'envoyer au support.

---

## 🧱 Générer un .exe (optionnel)

Double-clique sur **`3-Build-EXE.bat`**. L'exécutable se trouvera dans `dist/DofusPouletFlemmards/`.
D�tails : voir **[BUILD-EXE.md](BUILD-EXE.md)**.

**Après le build**, tu peux supprimer les fichiers temporaires de PyInstaller (recréés à chaque build) :
- le dossier **`build/`**
- le fichier **`DofusPouletFlemmards.spec`**

Garde uniquement **`dist/DofusPouletFlemmards/`** — c'est ce dossier que tu distribues (en entier, pas juste l'`.exe`).

> 🖱️ **Lancer facilement** : clic droit sur **`DofusPouletFlemmards.exe`** → *Envoyer vers* → *Bureau (créer un raccourci)*.
> Tu peux ensuite renommer le raccourci et lancer DPF depuis le bureau.
> ⚠️ **Ne déplace/copie pas l'`.exe` seul** hors de son dossier (il a besoin des fichiers à côté) — crée un **raccourci**, pas une copie.

> ⚠️ Si tu as **lancé l'exe pour tester**, supprime aussi **`dpf_config.json`** et les logs
> (**`dpf_notif_log.txt`**) créés **à côté de l'exe** avant de partager le dossier : ils contiennent
> **tes** réglages, raccourcis et pseudos.

---

## 📦 Dépendances

PySide6, pywin32, psutil, keyboard, mouse, numpy, et les paquets `winrt-*` (notifications & OCR Windows).
Liste complète : **[requirements.txt](requirements.txt)**.

---

## 💬 Contact & support

Créé par **scaryztw** — Discord : **scaryztw**
GitHub : https://github.com/scaryztw/DofusPouletFlemmards

---

<p align="center"><sub>Projet communautaire, non affilié à Ankama. Utilise-le à tes risques selon les CGU du jeu.</sub></p>
