Structure de notre code
Notre projet est organisé en quatre fichiers principaux :

extraction.py
Ce fichier permet de récupérer l’ensemble des données nécessaires, notamment via du scraping.
Les données collectées sont ensuite enregistrées dans un dossier output, situé au même niveau que le fichier extraction.py.

transfere_bdd.py
Ce script anonymise les joueurs en leur attribuant un identifiant unique.
Il se charge également de charger les données dans une base PostgreSQL pour les rendre exploitables dans l’application.

nettoyage.py
Ce fichier effectue des transformations sur les données brutes :
création de nouvelles colonnes, normalisation, restructuration des formats, suppression des doublons, etc.

dash.py
Ce fichier lance l'application Dash qui permet de visualiser les données de manière interactive.
L’utilisateur peut explorer les tournois, les decks, les joueurs et les cartes à travers plusieurs onglets dynamiques.

Structure des tables
La structure des tables PostgreSQL est définie dans les fichiers suivants :

00_create_wrk_tables.py

01_dwh_cards.py

02_create_players_matchs.py

Ces fichiers doivent impérativement se trouver dans le même répertoire que le fichier transfere_bdd.py pour garantir leur bon fonctionnement lors du chargement des données.

Lancement du projet
Pour exécuter correctement l’application, vous devez disposer d’une instance PostgreSQL fonctionnelle.

Installation de PostgreSQL portable
Vous pouvez télécharger une version portable de PostgreSQL ici :
https://sourceforge.net/projects/pgsqlportable/

Une fois le téléchargement effectué :

Lancez PostgreSQL via l'exécutable PostgreSQL - Start

Cela activera le serveur PostgreSQL en local

Telecharger les fichiers
Lancer les scripts
Une fois PostgreSQL activé, vous pouvez exécuter dans le terminal les fichiers dans cet ordre :
python extraction.py
python nettoyage.py
python transfere_bdd.py
python dash.py

L'application Dash sera ensuite accessible dans votre navigateur à l’adresse indiquée dans le terminal (généralement http://127.0.0.1:8050).
