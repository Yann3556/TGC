-- public.tournaments definition
DROP TABLE IF EXISTS public.wrk_tournaments;
CREATE TABLE public.wrk_tournaments (
  tournament_id varchar NULL,
  tournament_name varchar NULL,
  tournament_date timestamp NULL,
  tournament_organizer varchar NULL,
  tournament_format varchar NULL,
  tournament_nb_players int NULL
);

DROP TABLE IF EXISTS public.wrk_decklists;
CREATE TABLE public.wrk_decklists (
  tournament_id varchar NULL,
  player_id varchar NULL,
  card_type varchar NULL,
  card_name varchar NULL,
  card_url varchar NULL,
  card_count int NULL
);

CREATE TABLE IF NOT EXISTS public.wrk_players (
    player_id TEXT,
    tournament_id TEXT,
    name TEXT,
    player_placing TEXT,
    country TEXT,
    PRIMARY KEY (player_id, tournament_id)
);

DROP TABLE IF EXISTS public.wrk_matches CASCADE;

CREATE TABLE public.wrk_matches (
    match_id INTEGER,
    tournament_id TEXT,
    player_id TEXT,
    opponent_id TEXT,
    score INTEGER,
    win_or_lose TEXT,
    PRIMARY KEY (match_id, player_id)
);

