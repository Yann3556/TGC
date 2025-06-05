import dash
from dash import dcc, html, dash_table, Input, Output
import dash_bootstrap_components as dbc
import pandas as pd
from plotly import graph_objects as go
import re
# Chargement des données
df_tournois = pd.read_pickle("df_tournois.pkl")
df_cartes = pd.read_pickle("df_cartes.pkl")
df_joueurs = pd.read_pickle("df_joueurs.pkl")
df_matchs = pd.read_pickle("df_matchs.pkl")
df_winrate = pd.read_pickle("df_winrate.pkl")
df_player_winrate = pd.read_pickle("df_player_winrate.pkl")
df_popular_serie = pd.read_pickle("df_popular_serie.pkl")
df_evolution_participants = pd.read_pickle("df_evolution_participants.pkl")
df_match_stats = pd.read_pickle("df_match_stats.pkl")
df_cartes_last3 = pd.read_pickle("df_cartes_last3.pkl")
df_decks = pd.read_pickle("df_decks.pkl")
df_deck_vs = pd.read_pickle("df_deck_vs.pkl")
df_winrate_cartes = pd.read_pickle("df_winrate_cartes.pkl")
print("✅ df_winrate_cartes chargé avec", len(df_winrate_cartes), "lignes")

# Préparation des decks
deck_subset = df_decks.drop_duplicates("deck_hash").sort_values("nb_utilisations", ascending=False).head(15)
df_decks_light_summary = deck_subset["deck"].map(lambda d: ", ".join([f"{c['card_name']} x{c['card_count']}" for c in d]))
df_decks_light = pd.concat([
    deck_subset[["deck_hash", "nb_utilisations"]].reset_index(drop=True),
    df_decks_light_summary.rename("deck_summary")
], axis=1)

# Ajout des résumés de decks adverses dans df_deck_vs
summary_map = df_decks_light.drop_duplicates("deck_hash")[["deck_hash", "deck_summary"]]
df_deck_vs = df_deck_vs[df_deck_vs['deck_adversaire'].isin(summary_map['deck_hash'])]
df_deck_vs = pd.merge(df_deck_vs, summary_map, left_on="deck_adversaire", right_on="deck_hash", how="left", suffixes=('', '_adversaire'))


# Moyenne du winrate par carte
mean_winrate_by_card = df_winrate_cartes.groupby("card_name")["winrate"].mean()

# Popularité moyenne par carte
df_card_usage = df_cartes.groupby(["card_name", "saison_tournoi"])["card_count"].sum().reset_index()
df_card_usage = df_card_usage.rename(columns={"saison_tournoi": "saison"})
df_card_usage = pd.merge(df_card_usage, df_match_stats.groupby("saison")["nb_matchs"].sum().reset_index().rename(columns={"nb_matchs": "total_matchs"}), on="saison", how="left")
df_card_usage["taux_utilisation"] = df_card_usage["card_count"] / df_card_usage["total_matchs"]
mean_popularity_by_card = df_card_usage.groupby("card_name")["taux_utilisation"].mean()


def trier_saisons(saisons):
    def extract_key(s):
        match = re.match(r"([A-Z])(\d+)([a-z]*)", s)
        if match:
            lettre, num, suffixe = match.groups()
            return (lettre, int(num), suffixe)
        return ("Z", 999, s)  # fallback en dernier
    return sorted(saisons, key=extract_key)

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = "JCC Pokémon - Visualisation"

def create_table(df, id_table):
    return dash_table.DataTable(
        id=id_table,
        columns=[{"name": i, "id": i} for i in df.columns],
        data=df.to_dict("records"),
        page_size=10,
        style_table={"overflowX": "auto"},
        style_cell={"textAlign": "left", "padding": "5px"},
        style_header={"backgroundColor": "#f5f5f5", "fontWeight": "bold"},
        filter_action="native",
        sort_action="native"
    )

app.layout = dbc.Container([
    html.H1("📊 Pokémon TCG - Données Tournois", className="my-4"),
    dcc.Tabs([
        #########################
       dcc.Tab(label="Vue d'ensemble", children=[
    html.Br(),
    html.H5("📊 Indicateurs clés du métagame"),

    html.Div([
        html.Div([
            html.H6("🏆 Tournois analysés", style={"color": "#444"}),
            html.H4(f"{df_tournois['tournament_id'].nunique()}", style={"color": "#7B68EE"})
        ], style={
            "padding": "20px", "backgroundColor": "#f7f7f7", "borderRadius": "12px",
            "textAlign": "center", "flex": "1", "boxShadow": "0 2px 6px rgba(0,0,0,0.1)"
        }),

        html.Div([
            html.H6("⚔️ Matchs joués", style={"color": "#444"}),
            html.H4(f"{df_matchs['match_id'].nunique():,}".replace(",", " "), style={"color": "#20B2AA"})
        ], style={
            "padding": "20px", "backgroundColor": "#f7f7f7", "borderRadius": "12px",
            "textAlign": "center", "flex": "1", "boxShadow": "0 2px 6px rgba(0,0,0,0.1)"
        }),

        html.Div([
            html.H6("🃏 Cartes rencontrées", style={"color": "#444"}),
            html.H4(f"{df_winrate_cartes['card_name'].nunique():,}".replace(",", " ") if not df_winrate_cartes.empty else "0",
        style={"color": "#FF6B9D"})

        ], style={
            "padding": "20px", "backgroundColor": "#f7f7f7", "borderRadius": "12px",
            "textAlign": "center", "flex": "1", "boxShadow": "0 2px 6px rgba(0,0,0,0.1)"
        }),
    ], style={"display": "flex", "gap": "30px", "flexWrap": "wrap", "marginBottom": "40px"}),

    html.H5("📈 Winrate et Taux d'usage des cartes (Bubble Chart)"),
    html.Label("🃏 Filtrer par carte(s) :", style={
        'fontWeight': 'bold', 'color': '#555', 'marginBottom': '10px'
    }),
    dcc.Dropdown(
        id="dropdown-cartes-overview",
        options=[{"label": c, "value": c} for c in sorted(df_winrate_cartes['card_name'].unique())],
        multi=True,
        searchable=True,
        placeholder="Sélectionne une ou plusieurs cartes...",
        style={'marginBottom': '20px', "width": "60%"}
    ),

    dcc.Graph(id="graph-winrate-bubble-overview", style={"height": "600px"})
])

,
        #########################
        dcc.Tab(label="Tournois", children=[
            html.Br(),
            html.H5("🏆 Classement des séries avec le plus de participants"),
            create_table(df_popular_serie, "table-populaire-serie"),
            html.Br(),
            html.H5("📈 Évolution du nombre de participants par saison"),
            dcc.Graph(
                figure={
                    "data": [
                        {"x": df_evolution_participants["saison"],
                         "y": df_evolution_participants["total_players"],
                         "type": "line", "mode": "lines+markers", "name": "Participants"}
                    ],
                    "layout": {"title": "Participants par saison", "xaxis": {"title": "Saison"}, "yaxis": {"title": "Total"}}
                }
            )
        ]),
        
########################################
        dcc.Tab(label="Decks", children=[
    html.Br(),
    html.H5("🧙‍♂️ Decks les plus utilisés"),

    html.Label("Filtrer par saison :"),
    dcc.Dropdown(
        id="dropdown-saison-decks",
        options=[{"label": s, "value": s} for s in sorted(df_decks["saison"].dropna().unique())],
        placeholder="Choisir une saison",
        clearable=True,
    ),
    html.Br(),

    html.Label("Filtrer par carte incluse dans le deck :"),
    dcc.Dropdown(
        id="dropdown-carte-deck",
        options=[{"label": c, "value": c} for c in sorted(df_cartes["card_name"].dropna().unique())],
        placeholder="(Optionnel) Choisir une carte",
        clearable=True,
    ),
    html.Br(),

    dash_table.DataTable(
        id="table-decks",
        columns=[
            {"name": "Deck ID", "id": "deck_hash"},
            {"name": "Utilisations", "id": "nb_utilisations"},
            {"name": "Résumé du deck", "id": "deck_summary"}
        ],
        data=df_decks_light.drop_duplicates("deck_hash").sort_values("nb_utilisations", ascending=False).head(100).to_dict("records"),
        page_size=10,
        style_table={"overflowX": "auto"},
        style_cell={"textAlign": "left", "padding": "5px"},
        style_header={"backgroundColor": "#f5f5f5", "fontWeight": "bold"},
        row_selectable="single"
    ),
    html.Br(),
    html.Div(id="deck-detail"),
    html.Br(),
    html.Div(id="deck-matchups"),
])
,
        dcc.Tab(label="Joueurs", children=[
            html.Br(),
            html.H5("👥 Table des joueurs"),
            dash_table.DataTable(
                id="table-joueurs",
                columns=[{"name": i, "id": i} for i in df_joueurs.columns if i != "name"],
                data=df_joueurs.to_dict("records"),
                page_size=10,
                row_selectable="multi",
                style_table={"overflowX": "auto"},
                style_cell={"textAlign": "left", "padding": "5px"},
                style_header={"backgroundColor": "#f5f5f5", "fontWeight": "bold"},
                filter_action="native",
                sort_action="native"
            ),
            html.Br(),
            html.H5("🎛️ Sélection de joueur(s)"),
            dcc.Dropdown(
                id="dropdown-joueurs",
                options=[{"label": pid, "value": pid} for pid in sorted(df_joueurs["player_id"].dropna().unique())],
                multi=True,
                placeholder="Choisir un ou plusieurs joueurs (par ID)"
            ),
            html.Br(),
            html.H5("📈 Évolution du taux de victoire par saison"),
            dcc.Graph(id="graph-player-winrate"),
            html.Br(),
            html.H5("🏆 Top 20 des cartes les plus utilisées (filtrable par type)"),
            dcc.Dropdown(
                id="type-de-carte-déroulante",
                options=[{"label": c, "value": c} for c in sorted(df_cartes["card_type"].dropna().unique())],
                placeholder="Filtrer par type de carte"
            ),
            dcc.Graph(id="graph-top-cartes"),
            html.Br(),
            html.H5("📦 Cartes des 3 derniers tournois du joueur sélectionné"),
            html.Div(id="tables-cartes-derniers-tournois")
        ]),


        #########################################################################
       dcc.Tab(label="Cartes", children=[
    html.Br(),
    html.H5("📈 Évolution du taux de victoire des cartes par saison"),

    dcc.Dropdown(
        id="dropdown-carte-winrate",
        options=[{"label": c, "value": c} for c in sorted(df_winrate_cartes["card_name"].dropna().unique())],
        placeholder="(Optionnel) Zoom sur une carte",
        style={"margin-bottom": "20px"}
    ),

    html.Label("Filtrer par type de carte :"),
    dcc.Dropdown(
        id="dropdown-card-type",
        options=[{"label": c, "value": c} for c in sorted(df_cartes["card_type"].dropna().unique())],
        placeholder="Tous les types",
        clearable=True,
        style={"margin-bottom": "20px"}
    ),

    html.Label("Filtrer par saison :"),
    dcc.Dropdown(
        id="dropdown-saison-carte",
        options=[{"label": s, "value": s} for s in sorted(df_cartes["saison_tournoi"].dropna().unique())],
        placeholder="Toutes les saisons",
        clearable=True,
        style={"margin-bottom": "20px"}
    ),

    html.Label("Filtrer par winrate moyen (%) :"),
    dcc.RangeSlider(
        id="range-winrate",
        min=0, max=100, step=1, value=[0, 100],
        marks={i: f"{i}%" for i in range(0, 101, 20)},
        tooltip={"placement": "bottom"}
    ),

    html.Br(),
    html.Label("Filtrer par popularité moyenne :"),
    dcc.RangeSlider(
        id="range-popularite",
        min=0, max=1, step=0.01, value=[0, 1],
        marks={0: "0", 0.25: "0.25", 0.5: "0.5", 0.75: "0.75", 1: "1"},
        tooltip={"placement": "bottom"}
    ),

    html.Br(),
    dcc.Graph(id="graph-winrate-cartes"),

    html.Br(),
    html.H5("📊 Évolution de la popularité (nombre de fois jouée)"),
    dcc.Graph(id="graph-popularite-carte")
])


    ])
], fluid=True, style={"width": "95vw", "margin": "0 auto", "padding": "20px"})

@app.callback(
    Output("table-decks", "data"),
    Input("dropdown-saison-decks", "value"),
    Input("dropdown-carte-deck", "value")
)
def filtrer_decks_par_saison_et_carte(saison_selectionnee, carte_selectionnee):
    filtered = df_decks_light.copy()

    # Filtrage par saison
    if saison_selectionnee:
        hashes_valides_saison = df_decks[df_decks["saison"] == saison_selectionnee]["deck_hash"].unique()
        filtered = filtered[filtered["deck_hash"].isin(hashes_valides_saison)]

    # Filtrage par carte
    if carte_selectionnee:
        hashes_contenant_carte = df_decks[df_decks["deck"].map(
            lambda deck: any(carte["card_name"] == carte_selectionnee for carte in deck)
        )]["deck_hash"].unique()
        filtered = filtered[filtered["deck_hash"].isin(hashes_contenant_carte)]

    return filtered.drop_duplicates("deck_hash").sort_values("nb_utilisations", ascending=False).head(100).to_dict("records")

@app.callback(
    Output("deck-detail", "children"),
    Input("table-decks", "selected_rows")
)
def afficher_cartes_deck(selected_rows):
    if selected_rows is None or len(selected_rows) == 0:
        return html.Div("Sélectionne un deck pour voir son contenu.")
    selected_hash = df_decks_light.iloc[selected_rows[0]]["deck_hash"]
    cartes = df_decks[df_decks["deck_hash"] == selected_hash].iloc[0]["deck"]
    df_cartes_deck = pd.DataFrame(cartes)
    return html.Div([
        html.H6("📃 Cartes du deck sélectionné"),
        create_table(df_cartes_deck, "table-deck-cartes")
    ])

@app.callback(
    Output("deck-matchups", "children"),
    Input("table-decks", "selected_rows")
)
def afficher_matchups_deck(selected_rows):
    if selected_rows is None or len(selected_rows) == 0:
        return html.Div("Sélectionne un deck pour voir ses matchups.")

    selected_hash = df_decks_light.iloc[selected_rows[0]]["deck_hash"]
    df_vs = df_deck_vs[df_deck_vs["deck_hash"] == selected_hash].copy()
    min_matchs = 5
    df_vs = df_vs[df_vs["total_matchs"] >= min_matchs]

    if df_vs.empty:
        return html.Div("Pas assez de données de matchups pour ce deck.")

    df_vs_sorted = df_vs.sort_values("winrate", ascending=False)
    top3 = df_vs_sorted.head(3)
    bottom3 = df_vs_sorted.tail(3)

    def render_matchup_block(title, df_part):
        return html.Div([
            html.H6(title),
            html.Ul([
                html.Li(f"{row['deck_summary']} — {row['winrate']:.1f}% sur {row['total_matchs']} matchs")
                for _, row in df_part.iterrows()
            ])
        ])

    return html.Div([
        render_matchup_block("✅ Meilleurs matchups", top3),
        html.Br(),
        render_matchup_block("❌ Pires matchups", bottom3)
    ])


@app.callback(
    Output("tables-cartes-derniers-tournois", "children"),
    Input("dropdown-joueurs", "value")
)
def update_derniers_decks(joueurs_selectionnes):
    if not joueurs_selectionnes or len(joueurs_selectionnes) != 1:
        return html.Div("Sélectionne un seul joueur pour voir ses derniers decks.")

    joueur_id = joueurs_selectionnes[0]
    df_joueur_decks = df_decks[df_decks["player_id"] == joueur_id]
    df_joueur_decks = df_joueur_decks.sort_values("tournament_date", ascending=False)
    derniers_tournois = df_joueur_decks["tournament_id"].unique()[:3]

    composants = []
    for tid in derniers_tournois:
        tournoi_nom = df_tournois[df_tournois["tournament_id"] == tid]["tournament_name"].values[0]
        deck = df_joueur_decks[df_joueur_decks["tournament_id"] == tid]["deck"].iloc[0]
        df_cartes = pd.DataFrame(deck)
        composants.append(html.H6(f"Tournoi : {tournoi_nom}"))
        composants.append(create_table(df_cartes, f"table-deck-{tid}"))
        composants.append(html.Br())

    return composants


@app.callback(
    Output("dropdown-joueurs", "value"),
    Input("table-joueurs", "selected_rows")
)
def sync_table_joueurs_to_dropdown(selected_rows):
    if not selected_rows:
        return []
    ids = df_joueurs.iloc[selected_rows]["player_id"].tolist()
    return ids


@app.callback(
    Output("graph-player-winrate", "figure"),
    Input("dropdown-joueurs", "value")
)
def update_player_winrate(joueurs_selectionnes):
    if not joueurs_selectionnes:
        return {"data": [], "layout": {"title": "Sélectionne des joueurs"}}

    traces = []
    for pid in joueurs_selectionnes:
        df_joueur = df_player_winrate[df_player_winrate["player_id"] == pid].sort_values("saison")
        traces.append({
            "x": df_joueur["saison"],
            "y": df_joueur["winrate"],
            "type": "line",
            "mode": "lines+markers",
            "name": pid
        })

    return {
        "data": traces,
        "layout": {
            "title": "Évolution du winrate par saison",
            "xaxis": {"title": "Saison"},
            "yaxis": {"title": "Winrate (%)"}
        }
    }


@app.callback(
    Output("graph-top-cartes", "figure"),
    Input("type-de-carte-déroulante", "value")
)
def update_top_cartes(type_selectionne):
    df_filtered = df_cartes if not type_selectionne else df_cartes[df_cartes["card_type"] == type_selectionne]
    
    top_cartes = df_filtered.groupby("card_name")["card_count"].sum().sort_values(ascending=False).head(20)
    
    return {
        "data": [{
            "x": top_cartes.values,
            "y": top_cartes.index,
            "type": "bar",
            "orientation": "h"
        }],
        "layout": {
            "title": f"Top 20 cartes {type_selectionne if type_selectionne else 'toutes catégories'}",
            "xaxis": {"title": "Nombre d'utilisations"},
            "yaxis": {"title": "Carte"},
            "height": 600
        }
    }

@app.callback(
    Output("graph-winrate-cartes", "figure"),
    Input("dropdown-carte-winrate", "value"),
    Input("range-winrate", "value"),
    Input("range-popularite", "value"),
    Input("dropdown-card-type", "value"),
    Input("dropdown-saison-carte", "value")
)
def afficher_winrates_bubble(carte_selectionnee, plage_winrate, plage_popularite, type_carte, saison_selectionnee):
    cartes_valides = set(mean_winrate_by_card[(mean_winrate_by_card >= plage_winrate[0]) & (mean_winrate_by_card <= plage_winrate[1])].index)
    cartes_valides &= set(mean_popularity_by_card[(mean_popularity_by_card >= plage_popularite[0]) & (mean_popularity_by_card <= plage_popularite[1])].index)

    if type_carte:
        cartes_type = df_cartes[df_cartes["card_type"] == type_carte]["card_name"].unique()
        cartes_valides &= set(cartes_type)

    if saison_selectionnee:
        cartes_saison = df_cartes[df_cartes["saison_tournoi"] == saison_selectionnee]["card_name"].unique()
        cartes_valides &= set(cartes_saison)

    df = df_winrate_cartes[df_winrate_cartes["card_name"].isin(cartes_valides)]
    df = df[df["total_matchs"] > 100]  # pour éviter trop de bruit

    if carte_selectionnee:
        df = df[df["card_name"] == carte_selectionnee]

    if df.empty:
        return go.Figure(layout=dict(
            title="Aucune donnée disponible pour les filtres sélectionnés",
            xaxis=dict(visible=False), yaxis=dict(visible=False)
        ))

    df["usage_rate"] = df["total_matchs"] / df["total_matchs"].sum() * 100

    ordre_saisons = trier_saisons(df["saison"].unique())
    df["saison"] = pd.Categorical(df["saison"], categories=ordre_saisons, ordered=True)
    df = df.sort_values("saison")
    df["saison"] = df["saison"].astype(str)

    fig = go.Figure()
    for card in df["card_name"].unique():
        d = df[df["card_name"] == card]
        fig.add_trace(go.Scatter(
            x=d["saison"],
            y=d["winrate"],
            mode="markers+lines",
            name=card,
            marker=dict(
                size=d["usage_rate"],
                sizemode="area",
                sizeref=2. * max(df["usage_rate"].max(), 1) / (40 ** 2),
                sizemin=6,
                line=dict(width=1, color="rgba(0,0,0,0.3)")
            ),
            hovertemplate="<b>%{text}</b><br>Saison: %{x}<br>Winrate: %{y:.1f}%<br>Taux d’usage: %{marker.size:.1f}%<extra></extra>",
            text=[card] * len(d)
        ))

    fig.update_layout(
        title="Winrate des cartes (bubble chart)",
        xaxis=dict(title="Saison", categoryorder="array", categoryarray=ordre_saisons),
        yaxis=dict(title="Winrate (%)"),
        height=600,
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(l=50, r=50, t=50, b=50),
        showlegend=bool(carte_selectionnee is None)
    )
    return fig

@app.callback(
    Output("graph-popularite-carte", "figure"),
    Input("dropdown-carte-winrate", "value"),
    Input("range-winrate", "value"),
    Input("range-popularite", "value"),
    Input("dropdown-card-type", "value"),
    Input("dropdown-saison-carte", "value")
)
def afficher_popularite_bubble(carte_selectionnee, plage_winrate, plage_popularite, type_carte, saison_selectionnee):
    cartes_valides = set(mean_winrate_by_card[(mean_winrate_by_card >= plage_winrate[0]) & (mean_winrate_by_card <= plage_winrate[1])].index)
    cartes_valides &= set(mean_popularity_by_card[(mean_popularity_by_card >= plage_popularite[0]) & (mean_popularity_by_card <= plage_popularite[1])].index)

    if type_carte:
        cartes_type = df_cartes[df_cartes["card_type"] == type_carte]["card_name"].unique()
        cartes_valides &= set(cartes_type)

    if saison_selectionnee:
        cartes_saison = df_cartes[df_cartes["saison_tournoi"] == saison_selectionnee]["card_name"].unique()
        cartes_valides &= set(cartes_saison)

    df = df_card_usage[df_card_usage["card_name"].isin(cartes_valides)]

    if carte_selectionnee:
        df = df[df["card_name"] == carte_selectionnee]

    if df.empty:
        return go.Figure(layout=dict(
            title="Aucune donnée disponible pour les filtres sélectionnés",
            xaxis=dict(visible=False), yaxis=dict(visible=False)
        ))

    df["size"] = df["taux_utilisation"] * 100

    ordre_saisons = trier_saisons(df["saison"].unique())
    df["saison"] = pd.Categorical(df["saison"], categories=ordre_saisons, ordered=True)
    df = df.sort_values("saison")
    df["saison"] = df["saison"].astype(str)

    fig = go.Figure()
    for card in df["card_name"].unique():
        d = df[df["card_name"] == card]
        fig.add_trace(go.Scatter(
            x=d["saison"],
            y=d["taux_utilisation"],
            mode="markers+lines",
            name=card,
            marker=dict(
                size=d["size"],
                sizemode="area",
                sizeref=2. * max(df["size"].max(), 1) / (40 ** 2),
                sizemin=6,
                line=dict(width=1, color="rgba(0,0,0,0.3)")
            ),
            hovertemplate="<b>%{text}</b><br>Saison: %{x}<br>Popularité: %{y:.3f}<extra></extra>",
            text=[card] * len(d)
        ))

    fig.update_layout(
        title="Popularité des cartes (bubble chart)",
        xaxis=dict(title="Saison", categoryorder="array", categoryarray=ordre_saisons),
        yaxis=dict(title="Taux d’utilisation"),
        height=600,
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(l=50, r=50, t=50, b=50),
        showlegend=bool(carte_selectionnee is None)
    )
    return fig

@app.callback(
    Output("graph-winrate-bubble-overview", "figure"),
    Input("dropdown-cartes-overview", "value")
)
def update_graph_overview(cartes):
    df = df_winrate_cartes.copy()

    # Vérifie les colonnes requises
    required_cols = {"card_name", "saison", "winrate", "total_matchs"}
    if not required_cols.issubset(df.columns):
        return go.Figure(layout=dict(
            title="Colonnes manquantes dans df_winrate_cartes",
            xaxis=dict(visible=False),
            yaxis=dict(visible=False)
        ))

    # Nettoyage
    df = df[df["total_matchs"].notna() & (df["total_matchs"] > 0)]
    df = df[df["winrate"].notna() & df["card_name"].notna() & df["saison"].notna()]

    # 🔽 Filtrer aux cartes avec > 100 utilisations
    df = df[df["total_matchs"] > 100]

    if df.empty:
        return go.Figure(layout=dict(
            title="Aucune donnée disponible pour le graphique",
            xaxis=dict(visible=False),
            yaxis=dict(visible=False)
        ))

    if cartes:
        df = df[df["card_name"].isin(cartes)]

    # Recalcul taux d’usage
    total_matches = df["total_matchs"].sum()
    df["usage_rate"] = df["total_matchs"] / total_matches * 100

    # 🔽 Tri personnalisé des saisons
    ordre_saisons = trier_saisons(df["saison"].unique())
    df["saison"] = pd.Categorical(df["saison"], categories=ordre_saisons, ordered=True)
    df = df.sort_values("saison")
    df["saison"] = df["saison"].astype(str)  # important pour l'affichage dans Plotly


    fig = go.Figure()
    for card in df["card_name"].unique():
        d = df[df["card_name"] == card]
        fig.add_trace(go.Scatter(
            x=d["saison"],
            y=d["winrate"],
            mode="markers+lines",
            name=card,
            marker=dict(
                size=d["usage_rate"],
                sizemode="area",
                sizeref=2. * max(df["usage_rate"].max(), 1) / (40 ** 2),
                sizemin=6,
                line=dict(width=1, color="rgba(0,0,0,0.3)")
            ),
            hovertemplate="<b>%{text}</b><br>Saison: %{x}<br>Winrate: %{y:.1f}%<br>Taux d’usage: %{marker.size:.1f}%<extra></extra>",
            text=[card] * len(d)
        ))

    fig.update_layout(
        xaxis=dict(
    title="Saison",
    categoryorder="array",
    categoryarray=ordre_saisons  # liste triée
),

        title="Winrate et Taux d’usage des cartes (Bubble Chart)",
        xaxis_title="Saison",
        yaxis_title="Winrate (%)",
        height=600,
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(l=50, r=50, t=50, b=50)
    )
    return fig




if __name__ == "__main__":
    app.run(debug=True)