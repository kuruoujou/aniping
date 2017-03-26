#!/usr/bin/env python3
import os, requests, time, shutil, json, sys, logging
from datetime import date
from aniping import db, back_end

log = logging.getLogger(__name__)


def get_access_token(config):
    """Get the access token from anilist if necessary, otherwis return the last
    access token we received.

    Returns:
        The access token as a string.
    """
    anilist_token_file="/tmp/.anilist-token"
    try:
        with open(anilist_token_file, "r") as f:
            token_file = json.load(f)
        token = token_file['token']
        expiry = token_file['expiration']
    except (IOError, json.decoder.JSONDecodeError):
        token = None
        expiry = None

    if not expiry or ((int(expiry) - int(time.time())) < 300):
        new_token = requests.post(
            "https://anilist.co/api/auth/access_token?grant_type=client_credentials&client_id=%s&client_secret=%s"
            % (config['ANILIST']['CLIENT_ID'], config['ANILIST']['CLIENT_SECRET'])).json()

        with open(anilist_token_file, "w") as f:
            json.dump({'token':new_token['access_token'], 'expiration':new_token['expires']}, f)

        token=new_token['access_token']
        expiry=new_token['expires']

    return token

def get_season_string(season_int=None):
    """Gets next month's airing season (to allow for a preview of what's to come).
    
    Args:
        A season int from anilist to parse (optional)

    Returns:
        The season (winter, spring, summer, or fall) as a string.
    """
    monthsToSeasons = {(1,2,3):'winter', (4,5,6):'spring', (7,8,9):'summer', (10,11,12):'fall'}
    if season_int:
        season = next(val for key, val in monthsToSeasons.items() if int(season_int)%10 in key)
    else:
        targetDate = date.today()
        season = next(val for key, val in monthsToSeasons.items() if targetDate.month in key)
    return season

def get_remote_show_info(aid, config):
    """Gets the information about a show on anilist.

    Args:
        aid: The anilist ID of the show to grab.
        token: The access token to connect to anilist with.
        config: The config dictionary as read from config.yml

    Returns:
        A dictionary describing the show.
    """
    image_cache = config['IMAGE_CACHE']
    os.makedirs(image_cache, exist_ok=True)
    cache_contents = os.listdir(image_cache)
    token = get_access_token(config)
    ani_show = requests.get("https://anilist.co/api/anime/%s/page?access_token=%s"%(str(aid),token))
    if ani_show.status_code == 410:
        return None
    ani_show = ani_show.json()
    show = {}
    show['type'] = ani_show['type']
    show['title'] = ani_show['title_romaji']
    show['alt_title'] = ani_show['title_english']
    show['link'] = 'https://anilist.co/anime/%s'%ani_show['id']
    show['start_date'] = ani_show['start_date']
    try:
        show['studio'] = next(studio for studio in ani_show['studio'] if studio['main_studio'] == 1)['studio_name'] if ani_show['studio'] else ""
    except StopIteration:
        show['studio'] = ani_show['studio'][0]['studio_name']
    show['next_episode_date'] = ani_show['airing']['time'] if ani_show['airing'] else ani_show['start_date']
    show['next_episode'] = ani_show['airing']['next_episode'] if ani_show['airing'] else 1
    show['total_episodes'] = ani_show['total_episodes']
    show['description'] = ani_show['description']
    show['genre'] = ",".join(ani_show['genres'])
    show['airing'] = ani_show['airing_status']
    show['season'] = ani_show['season']

    grab_image = ani_show['image_url_lge']
    filename = grab_image.split("reg/")[1]

    if filename not in cache_contents:
        image_request = requests.get(ani_show['image_url_lge'], stream=True)
        with open("%s/%s"%(image_cache, filename), 'wb') as f:
            shutil.copyfileobj(image_request.raw, f)
        del image_request

    show['image'] = "%s/%s"%(image_cache, filename)
    show['aid'] = ani_show['id']

    return show
    
def get_season_shows(config):
    """Gets the list of this season's shows from anilist.
    """
    token = get_access_token(config)
    target_date = date.today()
    airing_list = requests.get("https://anilist.co/api/browse/anime?year=%s&season=%s&full_page=true&access_token=%s"%(target_date.year,get_season_string(),token))

    return airing_list.json()
    
def get_listed_shows():
    """Just calls back to db.get_all_shows()
    """
    log.debug("Calling back db for getting all shows.")
    return db.get_all_shows()

def update_show(aid, config):
    """Adds or edits a show in the local database based on ID
    """
    show = get_remote_show_info(aid, config)
    if not show:
        return None
		
    local_show = db.get_show(aid=aid)
    if not local_show:
        db.add_show(show['aid'], show['type'], show['title'], show['alt_title'], show['total_episodes'], show['next_episode'], show['next_episode_date'], show['start_date'], show['genre'], show['studio'], show['description'], show['link'], show['image'], show['airing'], get_season_string(show['season']))
    else:
        db.change_show(aid=show['aid'], show_type=show['type'], title=show['title'], alt_title=show['alt_title'], total_episodes=show['total_episodes'], next_episode=show['next_episode'], next_episode_date=show['next_episode_date'], start_date=show['start_date'], genre=show['genre'], studio=show['studio'], description=show['description'], link=show['link'], image=show['image'], airing=show['airing'], season_name=get_season_string(show['season']))

    # Don't want to be killed by too many requests in too short of a period,
    # so self-rate limit to about 4 requests per second.
    time.sleep(0.25)
    
def get_shows_by_category(config, search_results=None):
    """Gets all shows from the DB and seperates into watching,
    tv, movies, and specials."""
    if not search_results:
        log.debug("No list of shows provided, so getting all listed shows.")
        search_results = get_listed_shows()
    watching = []
    log.debug("Getting shows being watched from backend.")
    be_watching = back_end.get_watching_shows(config)
    log.debug("WATCHING SHOWS:\n====================\n{0}".format(be_watching))
    for item in be_watching:
        log.debug("Attempting to get information for show {0} with backend ID {1}".format(item['title'],item['beid']))
        db_show = db.get_show(beid=item['beid'])
        if db_show:
            log.debug("Found show info, adding to watching list.")
            watching.append(db_show)
    
    types = {'airing':['tv','tv short'], 'specials':['special', 'ova', 'ona'], 'movies':['movie']}

    log.debug("Filtering items based on their type from anilist.")
    airing = [x for x in search_results if x['type'].lower() in types['airing']]
    specials = [x for x in search_results if x['type'].lower() in types['specials']]
    movies = [x for x in search_results if x['type'].lower() in types['movies']]

    log.debug("Returning lists with {0} items in watching, {1} in airing, {2} in specials, and {3} in movies.".format(len(watching), len(airing), len(specials), len(movies)))
    return watching, airing, specials, movies
    
def scrape_shows(config):
    """Checks our anilist for shows and updates them in the database if they're there. If not, adds them.
    Deletes everything else.
    """
    log.debug("Starting to scrape shows.")
    sys.stdout.flush()
    log.debug("Getting all shows from DB...")
    all_shows = get_listed_shows()
    log.debug("ALL SHOWS\n====================\n{0}".format(all_shows))
    log.debug("Getting this seasons's shows")
    airing_list = get_season_shows(config)  
    log.debug("SEASON SHOWS\n====================\n{0}".format(airing_list))
    # Clean out shows from the list that aren't airing.
    log.debug("Cleaning show list to get this season's airing shows...")
    airing_ids = [show['id'] for show in airing_list]
    delete_shows = [x for x in all_shows if x['aid'] not in airing_ids]
    log.debug("SHOWS TO DELETE\n====================\n{0}".format(delete_shows))
    
    for show in delete_shows:
        log.debug("Calling DB to remove show {0} with ID {1}".format(show['title'], show['id']))
        db.remove_show(id=show['id'])
    
    for show in airing_list:
        log.debug("Calling to update show {0} with ID {1}".format(show['title_romaji'], show['id']))
        update_show(show['id'], config)
    
