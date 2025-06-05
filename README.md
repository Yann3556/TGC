# 📘 README – Mode opératoire du projet

## 🗂️ Structure du projet

Notre projet est organisé autour de **quatre scripts principaux** :

### 🔹 `extraction.py`
Ce fichier permet de récupérer l’ensemble des données nécessaires, notamment via du **scraping**.  
Les données collectées sont ensuite enregistrées dans un dossier `output`, situé au même niveau que le fichier `extraction.py`.

### 🔹 `nettoyage.py`
Ce script effectue des **transformations sur les données brutes** :  
- Création de nouvelles colonnes  
- Normalisation  
- Restructuration des formats  
- Suppression des doublons

### 🔹 `transfere_bdd.py`
Ce script **anonymise les joueurs** en leur attribuant un identifiant unique.  
Il permet également de **charger les données** transformées dans une **base de données PostgreSQL** pour qu'elles soient exploitables par l’application.

### 🔹 `dash.py`
Ce script lance une application **Dash interactive**.  
L’utilisateur peut visualiser les données à travers plusieurs onglets dynamiques (tournois, decks, joueurs, cartes, etc.).

---

## 🧱 Structure des tables

La structure des tables PostgreSQL est définie dans les fichiers suivants :

- `00_create_wrk_tables.sql`  
- `01_dwh_cards.sql`  
- `02_create_players_matchs.sql`

👉 **Important :** Ces fichiers doivent être placés **dans le même répertoire** que `transfere_bdd.py` pour garantir le bon fonctionnement du chargement des données.

---

## 🚀 Lancement du projet

Pour exécuter l’application, vous devez disposer d’une **instance PostgreSQL fonctionnelle**.

### 🔧 Installation de PostgreSQL (portable)

Vous pouvez télécharger une version portable ici :  
🔗 [https://sourceforge.net/projects/pgsqlportable/](https://sourceforge.net/projects/pgsqlportable/)

Une fois téléchargé :  
1. Lancez PostgreSQL via l'exécutable **`PostgreSQL - Start`**  
2. Le serveur PostgreSQL sera activé localement

---

## ▶️ Exécution des scripts

Une fois PostgreSQL lancé, exécutez les scripts dans l’ordre suivant :

```bash
python extraction.py
python nettoyage.py
python transfere_bdd.py
python dash.py
```

L’application Dash sera ensuite accessible dans votre navigateur à l’adresse indiquée dans le terminal, généralement :  
🌐 `http://127.0.0.1:8050`
