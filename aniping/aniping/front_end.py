import hashlib,time,requests,threading,logging
from pathlib import Path
from itertools import zip_longest
from aniping import db, back_end, scraper, search
from urllib.parse import quote_plus
from datetime import datetime

log = logging.getLogger(__name__)

"""Front end helper functions, used by the index page."""
def check_auth(username, password, config):
    """Checks if a user gives a correct username and password.
    User and pass are checked back against our backend, we do not handle our own
    authentication.
 
    Args:
            username: The username to check.
            password: The password to check.
            config: The configuration dictionary
 
    Returns:
            A boolean determining if the crednetials are valid.
    """
    log.debug("blah")
    return back_end.check_auth(username, password, config)
    
def set_login_id():
    """Creates a login ID and writes it to the database.
 
    Returns:
           The CID of the cookie.
    """
    cid = hashlib.sha256(str.encode(str(time.time()))).hexdigest()
    expiry = int(time.time()) + 7200 #All cookies expire in 2 hours
    db.add_login_id(cid, expiry)
    return cid

def check_login_id(cid, config):
    """Gets a login id from the database and checks that it's valid.
    If no login id is passed or if it's invalid, check if the backend
    has logins enabled.
 
    Args:
            cid: The cookie ID for the user.
 
    Returns:
             True or False
    """
    cdb = db.get_login_id(cid)
    if cdb:
        if cdb['expiration'] > int(time.time()):
            return True
        db.delete_login_id(cid)
    if not back_end.check_for_login(config):
        return True
    return False

def delete_login_id(cid):
    """Deletes a cookie from the database. Used for logging out.
    Just calls back to db.delete_cookie, but don't want anything
    directly calling db functions.

    Args:
            cid: The cookie ID for the user.

    """
    db.delete_login_id(cid)
    
def star_show(id):
    """Star a show in the database.
    
    Args:
        id: The ID of the show to star.
    """
    show = db.get_show(id=id)
    show['starred'] = 1 if show['starred'] == 0 else 0
    db.change_show(id=id, starred=show['starred'])
    
def get_show_from_db(id):
    """Gets the show information out of the database.
    """
    return db.get_show(id=id)
    
def search_show_from_backend(id, config):
    """Searches for a show in our DB from our backend downloader.
    """
    show = get_show_from_db(id)
    output = back_end.search(quote_plus(show['title']), config)
    if not output:
        output = back_end.search(quote_plus(show['alt_title']), config)
    if not output:
        return None
    return output[0]
    
def get_show_from_backend(id, config):
    """Gets a show from our backend based on a backend ID
    """
    output = back_end.get_show(id, config)
    return output

def get_subgroups(id):
    """Gets a list of sub groups from our backend search engine.
    """
    show = get_show_from_db(id)
    subgroups, results = search.results(id)
    return subgroups
    
            
def get_selected_group(beid, config):
    """Gets the selected subgroup from the show.
    """
    return back_end.subgroup_selected(beid, config)
    
def get_fanart(show):
    """Gets some fanart for the show.
    """
    return back_end.fanart(show)[0]
    
def add_update_show(dbid, beid, subgroup, config):
    """Adds a given show to the backend for downloading.
    """
    back_end.add_update_show(beid, subgroup, config)
    db.change_show(id=dbid, beid=beid)

def remove_show(id, config):
    """Removes a show from the backend given it's database ID
    """
    beid = db.get_show(id=id)['beid']
    back_end.remove_show(config, beid)
 
def get_shows_for_display(config, term=None):
    """Gets the shows from the backend and the scraper,
    filtered by search results if a term is provided"""
    if not term:
        log.debug("No term provided, sending default.")
        watching, airing, specials, movies = output_display_lists(*scraper.get_shows_by_category(config))
        log.debug("Got the following lists:")
        log.debug("WATCHING\n====================\n{0}".format(watching))
        log.debug("AIRING\n====================\n{0}".format(airing))
        log.debug("SPECIALS\n====================\n{0}".format(specials))
        log.debug("MOVIES\n====================\n{0}".format(movies))
        return watching, airing, specials, movies
    log.debug("Term provided, attempting to search for term {0}".format(term))
    watching, airing, specials, movies = output_display_lists(*scraper.get_shows_by_category(config, search_results=db.search_show(term)))
    log.debug("Got the following lists:")
    log.debug("WATCHING\n====================\n{0}".format(watching))
    log.debug("AIRING\n====================\n{0}".format(airing))
    log.debug("SPECIALS\n====================\n{0}".format(specials))
    log.debug("MOVIES\n====================\n{0}".format(movies))
    return watching, airing, specials, movies

def do_first_time_setup(config):
    """Function that the front-end calls to thread out
    a new first-time setup run"""
    log.debug(">>>>>>Starting First Time Setup Thread<<<<<<")
    ftst = threading.Thread(target=scrape_shows, args=(config,))
    ftst.start()
    log.debug(">>>>>>Separate Thread Started<<<<<<")
    return True

def output_display_lists(watching, airing, specials, movies):
    """Takes the display lists and massages them for output
    """
    log.debug("Removing watching shows from airing,specials,and movies lists")
    airing = [x for x in airing if x not in watching]
    specials = [x for x in specials if x not in watching]
    movies = [x for x in movies if x not in watching]
    
    for listed in (watching,airing,specials,movies):
        for item in listed:
            try:
                log.debug("Attempting to set date on show {0} with ID {1}".format(item['title'], item['id']))
                item['next_episode_date'] = datetime.strptime(item['next_episode_date'], '%Y-%m-%dT%H:%M:%S+09:00').strftime('%B %d, %Y')
            except (ValueError, TypeError):
                if item['next_episode_date'] == None or item['next_episode_date'] == "":
                    log.debug("Could not set date, so setting to \"unknown\"")
                    item['next_episode_date'] = "unknown"
                else:
                    try:
                        log.debug("The format did not work, so trying a different format.")
                        item['next_episode_date'] = datetime.strptime(item['next_episode_date'], '%b %d, %Y').strftime('%B %d, %Y')
                    except (ValueError, TypeError):
                        log.debug("Failed, leaving next_episode_date as is.")
                        item['next_episode_date'] = item['next_episode_date']
    
    log.debug("Returning lists with {0} items in watching, {1} in airing, {2} in specials, and {3} in movies.".format(len(watching), len(airing), len(specials), len(movies)))
    return watching, airing, specials, movies
    
def scrape_shows(config):
    """Calls to the scraper to scrape shows from our source
    """
    p = Path('/tmp/.aniping-setup')
    if p.is_file():
        log.debug("Scrape lock file exists, exiting.")
        return False
    else:
        log.debug("Scrape lock file does not exist, creating.")
        p.write_text("running")
    log.debug("Beginning show scraper.")
    scraper.scrape_shows(config)
    log.debug("Show scraper complete, removing lock file.")
    p.unlink()
    log.debug("scraper done.")
    return True
