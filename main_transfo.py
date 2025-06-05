import psycopg2 as psycopg

import os
import json
import re
import io
import time
from datetime import datetime

# Config PostgreSQL
postgres_db = "postgres"
postgres_user = "postgres"
postgres_password = ""
postgres_host = "localhost"
postgres_port = "5432"

output_directory = "C:/Users/yannp/PycharmProjects/TGC/output"

def get_connection_string():
    return f"postgresql://{postgres_user}:{postgres_password}@{postgres_host}:{postgres_port}/{postgres_db}"

def remove_emojis(text):
    return re.sub(r'[^\x00-\x7F]+', '', text)

def execute_sql_script(path: str):
    with psycopg.connect(get_connection_string()) as conn:
        with conn.cursor() as cur:
            with open(path, encoding='utf-8') as f:
                cur.execute(f.read())

def truncate_wrk_tables():
    with psycopg.connect(get_connection_string()) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                TRUNCATE public.wrk_tournaments,
                         public.wrk_decklists,
                         public.wrk_players,
                         public.wrk_matches
                RESTART IDENTITY CASCADE;
            """)

def copy_to_table(table_name, columns, data_rows):
    with psycopg.connect(get_connection_string()) as conn:
        with conn.cursor() as cur:
            output = io.StringIO()
            for row in data_rows:
                output.write('\t'.join(map(str, row)) + '\n')
            output.seek(0)
            cur.copy_expert(
                f"COPY {table_name} ({', '.join(columns)}) FROM STDIN",
                output
            )

def insert_wrk_tournaments():
    data = []
    for file in os.listdir(output_directory):
        with open(os.path.join(output_directory, file), encoding='utf-8') as f:
            t = json.load(f)
            data.append((
                t['id'],
                remove_emojis(t['name']),
                datetime.strptime(t['date'], '%Y-%m-%dT%H:%M:%S.000Z'),
                remove_emojis(t['organizer']),
                remove_emojis(t['format']),
                int(t['nb_players'])
            ))
    copy_to_table("wrk_tournaments",
                  ["tournament_id", "tournament_name", "tournament_date", "tournament_organizer", "tournament_format",
                   "tournament_nb_players"],
                  data)


def insert_wrk_decklists():
    data = []
    for file in os.listdir(output_directory):
        with open(os.path.join(output_directory, file), encoding='utf-8') as f:
            t = json.load(f)
            tid = t['id']
            for p in t['players']:
                pid = p['id']
                for c in p['decklist']:
                    data.append((
                        tid, pid,
                        remove_emojis(c['type']),
                        remove_emojis(c['name']),
                        remove_emojis(c['url']),
                        int(c['count'])
                    ))
    copy_to_table("wrk_decklists",
                  ["tournament_id", "player_id", "card_type", "card_name", "card_url", "card_count"],
                  data)


def insert_wrk_players():
    data = []
    for file in os.listdir(output_directory):
        with open(os.path.join(output_directory, file), encoding='utf-8') as f:
            t = json.load(f)
            tid = t['id']
            for p in t['players']:
                data.append((
                    p['id'], tid,
                    remove_emojis(p['name']),
                    p.get('placing', None),
                    p.get('country', None)
                ))
    copy_to_table("wrk_players",
                  ["player_id", "tournament_id", "name", "player_placing", "country"],
                  data)

def insert_wrk_matches():
    data = []
    mid = 1
    for file in os.listdir(output_directory):
        with open(os.path.join(output_directory, file), encoding='utf-8') as f:
            t = json.load(f)
            tid = t['id']
            for m in t.get("matches", []):
                results = m.get("match_results", [])
                if len(results) != 2:
                    continue
                p1, p2 = results[0], results[1]
                if p1["player_id"] == p2["player_id"]:
                    continue
                s1, s2 = int(p1["score"]), int(p2["score"])
                r1, r2 = ("Win", "Lose") if s1 > s2 else ("Lose", "Win") if s2 > s1 else ("Draw", "Draw")
                data.append((mid, tid, p1["player_id"], p2["player_id"], s1, r1))
                data.append((mid, tid, p2["player_id"], p1["player_id"], s2, r2))
                mid += 1
    copy_to_table("wrk_matches",
                  ["match_id", "tournament_id", "player_id", "opponent_id", "score", "win_or_lose"],
                  data)

def anonymize_player_ids():
    with psycopg.connect(get_connection_string()) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT DISTINCT player_id FROM (
                    SELECT player_id FROM wrk_players
                    UNION
                    SELECT player_id FROM wrk_decklists
                    UNION
                    SELECT player_id FROM wrk_matches
                    UNION
                    SELECT opponent_id AS player_id FROM wrk_matches
                ) AS all_players;
            """)
            player_ids = [row[0] for row in cur.fetchall()]
            mapping = {pid: f"anon_{i+1}" for i, pid in enumerate(player_ids)}

            cur.execute("CREATE TEMP TABLE temp_mapping (old_id TEXT PRIMARY KEY, new_id TEXT NOT NULL);")
            cur.executemany("INSERT INTO temp_mapping (old_id, new_id) VALUES (%s, %s)", mapping.items())

            for table, fields in {
                "wrk_players": ["player_id"],
                "wrk_decklists": ["player_id"],
                "wrk_matches": ["player_id", "opponent_id"]
            }.items():
                for field in fields:
                    cur.execute(f"""
                        UPDATE {table}
                        SET {field} = temp_mapping.new_id
                        FROM temp_mapping
                        WHERE {table}.{field} = temp_mapping.old_id;
                    """)
        conn.commit()

# SCRIPT PRINCIPAL AVEC CHRONO
steps = [
    ("create wrk tables", lambda: execute_sql_script("00_create_wrk_tables.sql")),
    ("truncate wrk tables", truncate_wrk_tables),
    ("insert tournaments", insert_wrk_tournaments),
    ("insert decklists", insert_wrk_decklists),
    ("insert players", insert_wrk_players),
    ("insert matches", insert_wrk_matches),
    ("execute card script", lambda: execute_sql_script("01_dwh_cards.sql")),
    ("anonymize player_ids", anonymize_player_ids)
]

total_start = time.time()
for label, func in steps:
    print(f"▶ {label}...")
    t0 = time.time()
    func()
    print(f"✅ {label} terminé en {time.time() - t0:.2f}s")

print(f"🎉 Script complet terminé en {time.time() - total_start:.2f}s")
