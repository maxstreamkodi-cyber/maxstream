# MaxStream IPTV – application Kodi (Kodi 21 « Omega »)

Application IPTV plein écran pour Kodi, inspirée de IPTV Smarters Player Lite.
Compatible **API Xtream Codes**, **URL M3U / M3U Plus** et **fichiers M3U locaux**.
Elle s'installe comme une application (Extensions › **Programmes**), et peut aussi envoyer
ses chaînes et le guide TV vers le **menu TV de Kodi** (via PVR IPTV Simple Client).

## Installation

**Page de téléchargement : https://xmahieu.github.io/maxstream/**

1. Kodi › Paramètres › Système › Extensions › activer **Sources inconnues**.
2. Paramètres › Gestionnaire de fichiers › Ajouter une source : `https://xmahieu.github.io/maxstream/` (nom : maxstream).
3. Extensions › **Installer depuis un fichier zip** › maxstream › `repository.maxstream-1.0.0.zip`.
4. Extensions › **Installer depuis un dépôt** › MaxStream Repository › Extensions de programmes › **MaxStream IPTV**.

Les mises à jour arrivent ensuite automatiquement. MaxStream s'ouvre dans Extensions › Programmes.

## Soutenir le projet

MaxStream est gratuit. Pour soutenir son développement : **[don de 5 € via PayPal](https://paypal.me/MaxStreamKodi/5EUR)**
(aussi accessible dans l'appli : bouton étoile en haut de l'accueil).

## Écrans

| Écran | Contenu |
|---|---|
| Accueil | Tuiles TV en direct / Films / Séries, raccourcis Replay, Guide TV, Favoris, Recherche, Listes, Compte, rangée « Reprendre la lecture », heure, date d'expiration, engrenage (paramètres, menu TV, guide, catégories masquées, cache) |
| TV en direct | Catégories (Tout, Favoris, Vus récemment, …) · chaînes avec logo, numéro, programme en cours, progression, badges Replay/Favori · **aperçu vidéo** (OK = aperçu, OK encore = plein écran) · programme en cours + 2 suivants · Plein écran / Guide TV / Favori / Replay · recherche de chaîne |
| Films / Séries | Catégories (Tout, Favoris, Ajouts récents, …) · grille d'affiches avec note, badge NOUVEAU, progression · tri Ajouts récents / A-Z / Mieux notés · recherche |
| Fiche film | Fond, affiche, note, année, durée, genre, synopsis, réalisation, casting · Reprendre à / Depuis le début / Bande-annonce (extension YouTube) / Favori · films de la même catégorie |
| Fiche série | Même en-tête · Lire ou Reprendre l'épisode suivant · onglets de saisons · épisodes avec progression |
| Guide / Replay | Jours à gauche, programmes à droite (DIRECT, REPLAY), description ; OK sur un programme passé lance le replay |

Menu contextuel (touche C / appui long) : favoris sur une chaîne ou une affiche, « Masquer la catégorie » sur une catégorie.

## Lecture fluide

Le tampon par défaut de Kodi (20 Mo) ne couvre que quelques secondes d'un film HD/4K : si le serveur IPTV
ralentit, l'image se fige. Au premier lancement, MaxStream propose **Optimiser Kodi pour le streaming**
(aussi dans l'engrenage et dans Paramètres › Lecture) : cache 256 Mo (selon la RAM), vitesse de lecture 20x,
et 5 tentatives de reconnexion réseau (`advancedsettings.xml`, actif après redémarrage de Kodi).

**Relais de flux (depuis 2.1.0).** Le service MaxStream fait passer films, séries, replay et chaînes TS
par un relais local (127.0.0.1). Si le fournisseur n'envoie plus rien pendant 5 secondes ou coupe la
connexion, le relais se reconnecte aussitôt et reprend à l'octet exact (films/séries) ou rouvre la chaîne
(direct) ; Kodi continue sur son cache pendant ce temps. Chaque reprise est notée dans le journal Kodi
(`relay: ... reconnecting`). Désactivable dans Paramètres › Lecture. Le guide TV n'est jamais mis à jour
pendant une lecture.

## Menu TV de Kodi

Engrenage › **Envoyer les chaînes vers le menu TV de Kodi** (ou Paramètres › Menu TV de Kodi) :
installe PVR IPTV Simple Client si besoin, écrit `channels.m3u` + `epg.xml` dans les données de MaxStream,
crée une configuration « MaxStream » dans IPTV Simple et la recharge. Le service de MaxStream
garde ensuite ces fichiers à jour (replay inclus pour les comptes Xtream). Si les chaînes n'apparaissent
pas dans TV après quelques secondes, redémarrez Kodi.

## Structure

```
script.maxstream/
  default.py                    entrée : sans argument ouvre l'interface, action=… lance une action
  service.py                    reprise de lecture + mise à jour guide TV + synchro menu TV
  resources/lib/
    gui/home.py live.py vod.py detail.py guide.py base.py   logique des écrans
    provider.py  m3u.py  epg.py  net.py                      Xtream / M3U / XMLTV
    playback.py  storage.py  actions.py  pvr.py  ui.py  common.py
  resources/skins/Default/1080i/script-maxstream-*.xml       mises en page (générées)
  resources/skins/Default/media/                             textures et icônes (générées)
  resources/settings.xml, resources/language/                (générés ; FR + EN)
tools/
  gen_skin.py gen_skin_media.py gen_art.py gen_settings.py gen_strings.py build_zip.py
  test/run_tests.py             89 vérifications de bout en bout (stubs Kodi + faux serveur Xtream/M3U)
  test/render_skin.py           rendu approximatif des écrans XML en PNG
  build_repo.py                 génère docs/ (dépôt Kodi + page GitHub Pages)
repository.maxstream/           extension « dépôt » (adresse de addons.xml)
docs/                           publié par GitHub Pages (ne pas modifier à la main)
```

## Développement

```
python tools/gen_strings.py script.maxstream
python tools/gen_settings.py script.maxstream/resources/settings.xml
python tools/gen_skin_media.py script.maxstream
python tools/gen_skin.py script.maxstream
python tools/test/run_tests.py
python tools/build_zip.py
python tools/build_repo.py      # puis commit + push : Kodi propose la mise à jour
```

Publier une nouvelle version : augmenter `version` dans `script.maxstream/addon.xml`, lancer
`tools/build_repo.py`, committer et pousser `docs/`.

Les écrans utilisent les polices du skin actif (Estuary par défaut). Journal Kodi : lignes préfixées
`[script.maxstream]` (mots de passe masqués).

Cette extension ne fournit aucun contenu : utilisez-la uniquement avec des listes auxquelles vous avez légalement accès.
