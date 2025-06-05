import psycopg2 as psycopg
import pandas as pd
import re
from thefuzz import fuzz, process
import hashlib
import json

def get_connection_string():
    return "postgresql://postgres:@localhost:5432/postgres"

def harmoniser_colonne(df, colonne, seuil_similarite=90):
    noms_uniques = df[colonne].dropna().unique()
    mapping = {}
    for nom in noms_uniques:
        match = process.extractOne(nom, mapping.keys(), scorer=fuzz.token_sort_ratio)
        if match and match[1] >= seuil_similarite:
            mapping[nom] = mapping[match[0]]
        else:
            mapping[nom] = nom
    df[colonne + "_harmonized"] = df[colonne].map(mapping)
    return df

def extraire_saison_depuis_nom(nom_carte):
    match = re.search(r"\(([^-]+)-\d+\)", nom_carte)
    return match.group(1) if match else None

def calculer_hash_liste(cartes):
    cartes_triées = sorted(cartes, key=lambda x: x["card_name"])
    return hashlib.md5(json.dumps(cartes_triées, sort_keys=True).encode()).hexdigest()

# Connexion
with psycopg.connect(get_connection_string()) as conn:
    df_tournois = pd.read_sql("SELECT * FROM public.wrk_tournaments", conn)
    df_cartes = pd.read_sql("SELECT * FROM public.wrk_decklists", conn)
    df_joueurs = pd.read_sql("SELECT * FROM public.wrk_players", conn)
    df_matchs = pd.read_sql("SELECT * FROM public.wrk_matches", conn)

# Participants
df_nb_joueurs_par_tournoi = df_joueurs.groupby("tournament_id").agg(
    total_players=("player_id", "nunique")
).reset_index()
df_tournois = pd.merge(df_tournois, df_nb_joueurs_par_tournoi, on="tournament_id", how="left")

# Harmonisation
df_tournois["tournament_date"] = pd.to_datetime(df_tournois["tournament_date"])
df_tournois["saison_tournoi"] = df_tournois["tournament_date"].dt.year.astype(str)
df_tournois["tournament_serie"] = df_tournois["tournament_name"].str.replace(r"#.*", "", regex=True).str.strip()
df_tournois = harmoniser_colonne(df_tournois, "tournament_serie")

# Saison réelle
df_cartes["saison_carte"] = df_cartes["card_name"].apply(extraire_saison_depuis_nom)
saison_par_tournoi = (
    df_cartes.groupby(["tournament_id", "saison_carte"])
    .size().reset_index(name="nb_cartes")
    .sort_values(["tournament_id", "nb_cartes"], ascending=[True, False])
    .drop_duplicates("tournament_id")
    .rename(columns={"saison_carte": "saison_reelle"})
)
df_tournois = pd.merge(df_tournois, saison_par_tournoi[["tournament_id", "saison_reelle"]], on="tournament_id", how="left")
df_tournois["saison_tournoi"] = df_tournois["saison_reelle"]

# Saison dans les cartes
df_cartes = pd.merge(
    df_cartes,
    df_tournois[["tournament_id", "saison_tournoi", "tournament_date"]],
    on="tournament_id",
    how="left"
)

# Création des decks
deck_liste = []
for (pid, tid), group in df_cartes.groupby(["player_id", "tournament_id"]):
    cartes = group[["card_name", "card_count"]].to_dict(orient="records")
    hash_deck = calculer_hash_liste(cartes)
    summary = ", ".join([f"{c['card_name']} x{c['card_count']}" for c in cartes])
    deck_liste.append({
        "player_id": pid,
        "tournament_id": tid,
        "deck_hash": hash_deck,
        "deck": cartes,
        "deck_summary": summary,
        "tournament_date": group["tournament_date"].iloc[0],
        "saison": group["saison_tournoi"].iloc[0]
    })
df_decks = pd.DataFrame(deck_liste)

# Fréquence des decks
df_decks_freq = df_decks.groupby("deck_hash").agg(nb_utilisations=("deck_hash", "count")).reset_index()
df_decks = pd.merge(df_decks, df_decks_freq, on="deck_hash", how="left")

# Attribution des decks aux matchs
deck_hash_map = df_decks.set_index(["player_id", "tournament_id"])["deck_hash"].to_dict()
df_matchs["deck_joueur"] = df_matchs.set_index(["player_id", "tournament_id"]).index.map(deck_hash_map)
df_matchs["deck_adversaire"] = df_matchs.set_index(["opponent_id", "tournament_id"]).index.map(deck_hash_map)
df_matchs["is_win"] = df_matchs["win_or_lose"].str.lower() == "win"

# Winrate entre decks
df_deck_vs = df_matchs.dropna(subset=["deck_joueur", "deck_adversaire"]).groupby(
    ["deck_joueur", "deck_adversaire"]
).agg(
    total_matchs=("match_id", "count"),
    wins=("is_win", "sum")
).reset_index()
df_deck_vs["winrate"] = df_deck_vs["wins"] / df_deck_vs["total_matchs"] * 100
df_deck_vs = df_deck_vs.rename(columns={"deck_joueur": "deck_hash"})

deck_summary_map = df_decks.drop_duplicates("deck_hash")[["deck_hash", "deck_summary"]]
df_deck_vs = pd.merge(
    df_deck_vs,
    deck_summary_map.rename(columns={"deck_hash": "deck_adversaire", "deck_summary": "deck_summary"}),
    on="deck_adversaire",
    how="left"
)

# Dash datasets
df_popular_serie = df_tournois.groupby("tournament_serie_harmonized").agg(
    total_players=("total_players", "sum"),
    nb_tournois=("tournament_id", "count")
).reset_index().sort_values("total_players", ascending=False)

df_evolution_participants = df_tournois.groupby("saison_tournoi").agg(
    total_players=("total_players", "sum")
).reset_index().rename(columns={"saison_tournoi": "saison"})

df_winrate = df_decks.merge(
    df_matchs[["player_id", "tournament_id", "is_win"]],
    on=["player_id", "tournament_id"]
)
df_winrate = df_winrate.groupby(["deck_hash", "saison"]).agg(
    total_matchs=("is_win", "count"),
    wins=("is_win", "sum")
).reset_index()
df_winrate["winrate"] = df_winrate["wins"] / df_winrate["total_matchs"] * 100

df_matchs = pd.merge(df_matchs, df_tournois[["tournament_id", "saison_tournoi"]], on="tournament_id", how="left")
df_player_winrate = df_matchs.groupby(["player_id", "saison_tournoi"]).agg(
    total_matchs=("match_id", "count"),
    victoires=("is_win", "sum")
).reset_index()
df_player_winrate["winrate"] = df_player_winrate["victoires"] / df_player_winrate["total_matchs"] * 100
df_player_winrate = pd.merge(df_player_winrate, df_joueurs[["player_id", "name"]], on="player_id", how="left")
df_player_winrate = df_player_winrate.rename(columns={"saison_tournoi": "saison"})

df_match_stats = df_matchs.groupby("saison_tournoi").agg(
    nb_matchs=("match_id", "count"),
    taux_victoires=("is_win", "mean")
).reset_index()
df_match_stats["taux_victoires"] *= 100
df_match_stats = df_match_stats.rename(columns={"saison_tournoi": "saison"})

df_cartes_last3 = df_cartes.sort_values("tournament_date", ascending=False)
dernier_tournois_ids = df_cartes_last3["tournament_id"].unique()[:3]
df_cartes_last3 = df_cartes[df_cartes["tournament_id"].isin(dernier_tournois_ids)]

# ➕ Winrate des cartes par saison (corrigé)
df_cartes_winrate = df_matchs.merge(
    df_cartes[["tournament_id", "player_id", "card_name"]],
    on=["tournament_id", "player_id"],
    how="left"
)
df_cartes_winrate["is_win"] = df_cartes_winrate["win_or_lose"].str.lower() == "win"
df_winrate_cartes = df_cartes_winrate.groupby(["card_name", "saison_tournoi"]).agg(
    total_matchs=("match_id", "count"),
    wins=("is_win", "sum")
).reset_index()
df_winrate_cartes["winrate"] = df_winrate_cartes["wins"] / df_winrate_cartes["total_matchs"] * 100
df_winrate_cartes = df_winrate_cartes.rename(columns={"saison_tournoi": "saison"})

# Sauvegardes
df_tournois.to_pickle("df_tournois.pkl")
df_cartes.to_pickle("df_cartes.pkl")
df_joueurs.to_pickle("df_joueurs.pkl")
df_matchs.to_pickle("df_matchs.pkl")
df_decks.to_pickle("df_decks.pkl")
df_deck_vs.to_pickle("df_deck_vs.pkl")
df_popular_serie.to_pickle("df_popular_serie.pkl")
df_winrate.to_pickle("df_winrate.pkl")
df_player_winrate.to_pickle("df_player_winrate.pkl")
df_evolution_participants.to_pickle("df_evolution_participants.pkl")
df_match_stats.to_pickle("df_match_stats.pkl")
df_cartes_last3.to_pickle("df_cartes_last3.pkl")
df_winrate_cartes.to_pickle("df_winrate_cartes.pkl")
