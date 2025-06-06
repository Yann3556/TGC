from dataclasses import dataclass, asdict
import os
import json
import re
import logging

try:
    import aiohttp
    import aiofile
    from bs4 import BeautifulSoup, Tag
    import asyncio
except ImportError as e:
    import sys
    print(f"Missing module: {e.name}.")
    print("Install the dependencies with: pip install -r requirements.txt")
    sys.exit(1)

base_url = "https://play.limitlesstcg.com"
headers = {'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.106 Safari/537.36'}
proxy_url = os.environ.get("http_proxy") or os.environ.get("HTTP_PROXY")

# --- Logger configuration ---
logger = logging.getLogger("scraper")
if logger.hasHandlers():
    logger.handlers.clear()
    
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

# Console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# File handler
file_handler = logging.FileHandler("scraper.log", encoding='utf-8')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)


scraping_stats = {
    "tournaments_scraped": 0,
    "total_players": 0,
    "total_decklists": 0,
    "total_cards": 0,
    "total_matches": 0
}
# --- Dataclasses used for json generation ---
@dataclass
class DeckListItem:
    type: str
    url: str
    name: str
    count: int

@dataclass
class Player:
    id: str
    name: str
    placing: str
    country: str
    decklist: list[DeckListItem]

@dataclass
class MatchResult:
    player_id: str
    score: int

@dataclass
class Match:
    match_results: list[MatchResult]

@dataclass
class Tournament:
    id: str
    name: str
    date: str
    organizer: str
    format: str
    nb_players: str
    players: list[Player]
    matches: list[Match]

# --- Helpers ---
def extract_trs(soup: BeautifulSoup, table_class: str):
    table = soup.find(class_=table_class)
    if not table:
        logger.warning(f"Table with class '{table_class}' not found.")
        return []
    trs = table.find_all("tr")
    if trs:
        trs.pop(0)  # Remove header
    return trs

def construct_standings_url(tournament_id: str):
    return f"/tournament/{tournament_id}/standings?players"

def construct_pairings_url(tournament_id: str):
    return f"/tournament/{tournament_id}/pairings"

def construct_decklist_url(tournament_id: str, player_id: str):
    return f"/tournament/{tournament_id}/player/{player_id}/decklist"

def extract_previous_pairings_urls(pairings: BeautifulSoup):
    pairing_nav = pairings.find(class_="mini-nav")
    if pairing_nav is None:
        return []
    pairing_urls = pairing_nav.find_all("a")
    if pairing_urls:
        pairing_urls.pop(-1)  # remove current page link
    return [a.attrs["href"] for a in pairing_urls]

def is_bracket_pairing(pairings: BeautifulSoup):
    return pairings.find("div", class_="live-bracket") is not None

regex_tournament_id = re.compile(r'[a-zA-Z0-9_\-]*')
def is_table_pairing(pairings: BeautifulSoup):
    pairings_div = pairings.find("div", class_="pairings")
    if pairings_div is not None:
        table = pairings_div.find("table", {'data-tournament': regex_tournament_id})
        return table is not None
    return False

def extract_matches_from_bracket_pairings(pairings: BeautifulSoup):
    matches = []
    bracket = pairings.find("div", class_="live-bracket")
    if not bracket:
        return matches
    matches_div = bracket.find_all("div", class_="bracket-match")
    for match in matches_div:
        # Skip matches with bye
        if match.find("a", class_="bye") is not None:
            continue
        players_div = match.find_all("div", class_="live-bracket-player")
        match_results = []
        for player in players_div:
            match_results.append(MatchResult(
                player.attrs["data-id"],
                int(player.find("div", class_="score").attrs["data-score"])
            ))
        matches.append(Match(match_results))
    return matches

def extract_matches_from_table_pairings(pairings: BeautifulSoup):
    matches = []
    matches_tr = pairings.find_all("tr", {'data-completed': '1'})
    for match in matches_tr:
        p1 = match.find("td", class_="p1")
        p2 = match.find("td", class_="p2")
        if p1 is not None and p2 is not None:
            matches.append(Match([
                MatchResult(p1.attrs["data-id"], int(p1.attrs["data-count"])),
                MatchResult(p2.attrs["data-id"], int(p2.attrs["data-count"]))
            ]))
    return matches

regex_card_url = re.compile(r'pocket\.limitlesstcg\.com/cards/.*')
def extract_decklist(decklist: BeautifulSoup) -> list[DeckListItem]:
    decklist_div = decklist.find("div", class_="decklist")
    cards = []
    if decklist_div:
        cards_a = decklist_div.find_all("a", {'href': regex_card_url})
        for card in cards_a:
            cards.append(DeckListItem(
                card.parent.parent.find("div", class_="heading").text.split(" ")[0],
                card.attrs["href"],
                card.text[2:],  # remove quantity + space
                int(card.text[0])
            ))
    return cards

# --- Cache filename cleaner function ---
def sanitize_cache_filename(url: str) -> str:
    filename = "cache" + url
    # Keep only alnum and '/' (to preserve directories)
    filename = ''.join(ch for ch in filename if ch.isalnum() or ch == '/')
    # Replace 'nul' which could cause issues on Windows with a safer string
    # Use regex to replace any standalone 'nul' word to '__nul__'
    filename = re.sub(r'\bnul\b', '__nul__', filename)
    filename += ".html"
    return filename

async def async_soup_from_url(session: aiohttp.ClientSession, sem: asyncio.Semaphore, url: str, use_cache: bool = True):
    if url is None:
        logger.debug("URL is None, returning None")
        return None

    cache_filename = sanitize_cache_filename(url)

    if use_cache and os.path.isfile(cache_filename):
        logger.debug(f"Cache hit for {url} -> {cache_filename}")
        async with sem:
            try:
                async with aiofile.async_open(cache_filename, "r") as f:
                    html = await f.read()
            except OSError as e:
                logging.error(f"Insufficient disk space when writing cache file {cache_filename}. Stopping the program.")
                raise RuntimeError("Insufficient disk space, stopping the program") from e
    else:
        logger.info(f"Fetching {url} from source")
        kwargs = {"proxy": proxy_url} if proxy_url else {}
        async with session.get(url, **kwargs) as resp:
            html = await resp.text()

        # Ensure directory exists
        directory = os.path.dirname(cache_filename)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)

        async with sem:
            async with aiofile.async_open(cache_filename, "w") as f:
                await f.write(html)

    return BeautifulSoup(html, 'html.parser')

# --- Extract players ---
regex_player_id = re.compile(r'/tournament/[a-zA-Z0-9_\-]*/player/[a-zA-Z0-9_]*')
regex_decklist_url = re.compile(r'/tournament/[a-zA-Z0-9_\-]*/player/[a-zA-Z0-9_]*/decklist')

async def extract_players(session: aiohttp.ClientSession, sem: asyncio.Semaphore, standings_page: BeautifulSoup, tournament_id: str) -> list[Player]:
    player_trs = extract_trs(standings_page, "striped")
    player_ids = [tr.find("a", {'href': regex_player_id}).attrs["href"].split('/')[4] for tr in player_trs]
    has_decklist = [tr.find("a", {'href': regex_decklist_url}) is not None for tr in player_trs]
    player_names = [tr.attrs.get('data-name', '') for tr in player_trs]
    player_placings = [tr.attrs.get("data-placing", '-1') for tr in player_trs]
    player_countries = [tr.attrs.get("data-country", '') for tr in player_trs]

    decklist_urls = [construct_decklist_url(tournament_id, pid) if has else None for pid, has in zip(player_ids, has_decklist)]
    decklist_pages = await asyncio.gather(*[async_soup_from_url(session, sem, url, True) for url in decklist_urls])

    players = []
    for i, player_id in enumerate(player_ids):
        if decklist_pages[i] is None:
            continue
        players.append(Player(
            player_id,
            player_names[i],
            player_placings[i],
            player_countries[i],
            extract_decklist(decklist_pages[i])
        ))

    return players

async def extract_matches(session: aiohttp.ClientSession, sem: asyncio.Semaphore, tournament_id: str) -> list[Match]:
    matches = []
    last_pairings = await async_soup_from_url(session, sem, construct_pairings_url(tournament_id))
    previous_urls = extract_previous_pairings_urls(last_pairings)
    previous_pairings = await asyncio.gather(*[async_soup_from_url(session, sem, url) for url in previous_urls])
    pairings_all = previous_pairings + [last_pairings]

    for pairing in pairings_all:
        if is_bracket_pairing(pairing):
            matches += extract_matches_from_bracket_pairings(pairing)
        elif is_table_pairing(pairing):
            matches += extract_matches_from_table_pairings(pairing)
        else:
            logger.warning("Unrecognized pairing type encountered.")
    
    return matches

async def handle_tournament_standings_page(
    session: aiohttp.ClientSession,
    sem: asyncio.Semaphore,
    standings_page: BeautifulSoup,
    tournament_id: str, 
    tournament_name: str,
    tournament_date: str,
    tournament_organizer: str,
    tournament_format: str,
    tournament_nb_players: int
):
    output_file = f"output/{tournament_id}.json"
    logger.info(f"Processing tournament {tournament_id}...")

    if os.path.isfile(output_file):
        logger.info(f"Skipping tournament {tournament_id} (already processed)")
        return
    else:
        output_dir = os.path.dirname(output_file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)

    players = await extract_players(session, sem, standings_page, tournament_id)
    if not players:
        logger.info(f"No players with decklists found for tournament {tournament_id}, skipping.")
        return

    nb_decklists = sum(1 for p in players if len(p.decklist) > 0)
    matches = await extract_matches(session, sem, tournament_id)

    tournament = Tournament(
        tournament_id,
        tournament_name,
        tournament_date,
        tournament_organizer,
        tournament_format,
        tournament_nb_players,
        players,
        matches
    )
    scraping_stats["tournaments_scraped"] += 1
    scraping_stats["total_players"] += len(players)
    scraping_stats["total_decklists"] += nb_decklists
    scraping_stats["total_matches"] += len(matches)
    scraping_stats["total_cards"] += sum(len(p.decklist) for p in players)
    logger.info(f"Tournament {tournament_id} has {len(players)} players, {nb_decklists} decklists, {len(matches)} matches")
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(asdict(tournament), f, indent=2)

first_tournament_page = "/tournaments/completed?game=POCKET&format=STANDARD&platform=all&type=online&time=all"
regex_standings_url = re.compile(r'/tournament/[a-zA-Z0-9_\-]*/standings')

async def handle_tournament_list_page(session: aiohttp.ClientSession, sem: asyncio.Semaphore, url: str):
    soup = await async_soup_from_url(session, sem, url, False)
    if soup is None:
        logger.error(f"Failed to get content for tournament list page {url}")
        return

    pagination = soup.find("ul", class_="pagination")
    if not pagination:
        logger.error(f"Pagination not found on page {url}")
        return

    current_page = int(pagination.attrs.get("data-current", "1"))
    max_page =1 # int(pagination.attrs.get("data-max", "1"))

    logger.info(f"Extracting completed tournaments page {current_page} / {max_page}")

    tournament_trs = extract_trs(soup, "completed-tournaments")
    tournament_ids = [tr.find("a", {'href': regex_standings_url}).attrs["href"].split('/')[2] for tr in tournament_trs]
    tournament_names = [tr.attrs.get('data-name', '') for tr in tournament_trs]
    tournament_dates = [tr.attrs.get('data-date', '') for tr in tournament_trs]
    tournament_organizers = [tr.attrs.get('data-organizer', '') for tr in tournament_trs]
    tournament_formats = [tr.attrs.get('data-format', '') for tr in tournament_trs]
    tournament_nb_players = [tr.attrs.get('data-players', '0') for tr in tournament_trs]

    standings_urls = [construct_standings_url(tid) for tid in tournament_ids]

    standings_pages = await asyncio.gather(*[async_soup_from_url(session, sem, url) for url in standings_urls])

    for i in range(len(tournament_ids)):
        await handle_tournament_standings_page(
            session, sem, standings_pages[i],
            tournament_ids[i], tournament_names[i], tournament_dates[i],
            tournament_organizers[i], tournament_formats[i], tournament_nb_players[i]
        )

    if current_page < max_page:
        next_page_url = f"{first_tournament_page}&page={current_page + 1}"
        await handle_tournament_list_page(session, sem, next_page_url)

async def main():
    connector = aiohttp.TCPConnector(limit=20)
    sem = asyncio.Semaphore(50)
    async with aiohttp.ClientSession(base_url=base_url, connector=connector, headers=headers) as session:
        await handle_tournament_list_page(session, sem, first_tournament_page)
    logger.info("=== Scraping Summary ===")
    logger.info(f"Tournaments scraped    : {scraping_stats['tournaments_scraped']}")
    logger.info(f"Total players         : {scraping_stats['total_players']}")
    logger.info(f"Total decklists       : {scraping_stats['total_decklists']}")
    logger.info(f"Total cards           : {scraping_stats['total_cards']}")
    logger.info(f"Total matches         : {scraping_stats['total_matches']}")
    logger.info("================================ End of execution ================================")

if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()
    asyncio.run(main())
