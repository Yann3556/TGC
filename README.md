
Structure de notre code
Notre projet est organisé en quatre fichiers principaux :


extraction.py
Ce fichier permet de récupérer l’ensemble des données nécessaires, notamment via du scraping.
Les données collectées sont ensuite enregistrées dans un dossier output, situé au même niveau que le fichier extraction.py.
Structure du projet

transfere_bdd.py ATTENTION chemin de données a changer
Ce script anonymise les joueurs en leur attribuant un identifiant unique.
Il se charge également de charger les données dans une base PostgreSQL pour les rendre exploitables dans l’application.
Notre projet est organisé autour de **quatre scripts principaux** :

nettoyage.py
Ce fichier effectue des transformations sur les données brutes :
création de nouvelles colonnes, normalisation, restructuration des formats, suppression des doublons, etc.

`extraction.py`
Ce fichier permet de récupérer l’ensemble des données nécessaires, notamment via du **scraping**.  
Les données collectées sont ensuite enregistrées dans un dossier `output`, situé au même niveau que le fichier `extraction.py`.

dash.py
Ce fichier lance l'application Dash qui permet de visualiser les données de manière interactive.
L’utilisateur peut explorer les tournois, les decks, les joueurs et les cartes à travers plusieurs onglets dynamiques.

`nettoyage.py`
Ce script effectue des **transformations sur les données brutes** :  
- Création de nouvelles colonnes  
- Normalisation  
- Restructuration des formats  
- Suppression des doublons

`requements.txt`
Ce fichier permet d'installer les bibliotheqes python avant l'excution des fichiers Python.

`transfere_bdd.py`
Ce script **anonymise les joueurs** en leur attribuant un identifiant unique.  
Il permet également de **charger les données** transformées dans une **base de données PostgreSQL** pour qu'elles soient exploitables par l’application.

`dash.py`
Ce script lance une application **Dash interactive**.  
L’utilisateur peut visualiser les données à travers plusieurs onglets dynamiques (tournois, decks, joueurs, cartes, etc.).

---

Structure des tables

Structure des tables
La structure des tables PostgreSQL est définie dans les fichiers suivants :

00_create_wrk_tables.py
- `00_create_wrk_tables.sql`  
- `01_dwh_cards.sql`  
- `02_create_players_matchs.sql`

**Important :** Ces fichiers doivent être placés **dans le même répertoire** que `transfere_bdd.py` pour garantir le bon fonctionnement du chargement des données.

---

01_dwh_cards.py
## 🚀 Lancement du projet

02_create_players_matchs.py
Pour exécuter l’application, vous devez disposer d’une **instance PostgreSQL fonctionnelle**.

Ces fichiers doivent impérativement se trouver dans le même répertoire que le fichier transfere_bdd.py pour garantir leur bon fonctionnement lors du chargement des données.
### 🔧 Installation de PostgreSQL (portable)

Lancement du projet
Pour exécuter correctement l’application, vous devez disposer d’une instance PostgreSQL fonctionnelle.
Vous pouvez télécharger une version portable ici :  
🔗 [https://sourceforge.net/projects/pgsqlportable/](https://sourceforge.net/projects/pgsqlportable/)

Installation de PostgreSQL portable
Vous pouvez télécharger une version portable de PostgreSQL ici :
https://sourceforge.net/projects/pgsqlportable/
Une fois téléchargé :  
1. Lancez PostgreSQL via l'exécutable **`PostgreSQL - Start`**  
2. Le serveur PostgreSQL sera activé localement

Une fois le téléchargement effectué :
---

Lancez PostgreSQL via l'exécutable PostgreSQL - Start
## ▶️ Exécution des scripts

Cela activera le serveur PostgreSQL en local
Une fois PostgreSQL lancé, exécutez les scripts dans l’ordre suivant :

Lancer les scripts
Une fois PostgreSQL activé, vous pouvez exécuter les fichiers dans cet ordre :
```bash
pip install -r requirements.txt
python extraction.py
python transfere_bdd.py
python nettoyage.py
python dash.py
```

L'application Dash sera ensuite accessible dans votre navigateur à l’adresse indiquée dans le terminal (généralement http://127.0.0.1:8050).

