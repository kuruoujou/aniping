#!/usr/bin/env python3
"""front_end

This submodule handles functions required by the front_end - app.py.
Most functions should be defined here and called by app.py. Because
app.py will only call to this particular submodule, it is acceptable
to include functions that do nothing but call back to a different
function in the module.
"""
import hashlib,time,requests,threading,logging
from pathlib import Path
from itertools import zip_longest
from aniping import db, back_end, scraper, search
from urllib.parse import quote_plus
from datetime import datetime

log = logging.getLogger(__name__)

def check_auth(username, password, config):
    """Authentication Check Function.
    
    Checks if a user gives a correct username and password.
    User and pass are checked back against our backend, we do not handle our own
    authentication.
 
    Args:
        username (str): The username to check.
        password (str): The password to check.
        config (dict): The configuration dictionary.
 
    Returns:
        bool.
        
            * True -- user is authenticated
            * False -- user is not authenticated or an error occurred
    """
    log.debug("blah")
    return back_end.check_auth(username, password, config)
    
def set_login_id():
    """Session id Creator
    
    Creates a session id and writes it to the database.
 
    Returns:
        str. The id of the session.
    """
    cid = hashlib.sha256(str.encode(str(time.time()))).hexdigest()
    expiry = int(time.time()) + 7200 #All cookies expire in 2 hours
    db.add_login_id(cid, expiry)
    return cid

def check_login_id(cid, config):
    """Session ID Check Function.
    
    Gets a session id from the database and checks that it's valid.
    If no session id is passed or if it's invalid, check if the backend
    has logins enabled.
 
    Args:
        cid (str): The session ID for the user.
        config (dict): The configuration dictionary.
 
    Returns:
        bool.
            
            * True -- Session id is valid *or* back end logins are disabled.
            * False -- Session id is not valid or has expired.
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
    """Session id Delete Function.
    
    Deletes a session id from the database. Used for logging out.
    Just calls back to db.delete_login_id.

    Args:
        cid (str): The session ID for the user.

    """
    db.delete_login_id(cid)
    
def star_show(id):
    """Show starring/highlighting function.
    
    Toggles a show starred status in the database.
    
    Args:
        id (int): The ID of the show to star.
    """
    show = get_show_from_db(id)
    show['starred'] = 1 if show['starred'] == 0 else 0
    db.change_show(id=id, starred=show['starred'])
    
def get_show_from_db(id):
    """Show getter function
    
    Gets the show information out of the database.
    Just calls back to db.get_show_from_db.
    
    Args:
        id (int): the database ID for the show.
        
    Returns:
        dict. The show information for the ID passed.
    """
    return db.get_show(id=id)
    
def search_show_from_backend(id, config):
    """Backend show search function
    
    Gets a show from the database and searches for it in
    the backend system.
    
    Args:
        id (int): the database ID for the show.
        config (dict): The configuration dictionary.
        
    Returns:
        dict. The backend search results for the id passed. None if not found.
    """
    show = get_show_from_db(id)
    output = back_end.search(quote_plus(show['title']), config)
    if not output:
        # Sometimes the normal title doesn't give us any results, because it might
        # be non-english or something. The alt-title should give us results in that
        # case.
        output = back_end.search(quote_plus(show['alt_title']), config)
    if not output:
        return None
    return output[0]
    
def get_show_from_backend(id, config):
    """Backend show getter function.
    
    Gets a known show from the backend system from its id.
    
    Args:
        id (int): the backend ID for the show.
        config (dict): The configuration dictionary.
        
    Returns:
        dict. The backend show information.
    """
    output = back_end.get_show(id, config)
    return output

def get_subgroups(id):
    """Subgroup list getter function.
    
    Gets a list of sub groups from the search engine. Generally this
    will be a torrent search site, like nyaa. Nothing is ever downloaded
    directly with aniping! The backend should handle that, if downloading
    is happening. This only gets a list of groups subtitling the show.
    
    Args:
        id (int): the database ID for the show.
    
    Returns:
        list. A list of subgroups.
    """
    show = get_show_from_db(id)
    subgroups, results = search.results(id)
    return subgroups
    
            
def get_selected_group(beid, config):
    """Selected subgroup getter function.
    
    Gets the selected subgroup for the show from the backend.
    Just calls back to back_end.subgroup_selected.
    
    Args:
        beid (int): the backend ID for the show.
        config (dict): The configuration dictionary.
        
    Returns:
        str. The subgroup selected for the series.
    """
    return back_end.subgroup_selected(beid, config)
    
def get_fanart(beid):
    """Fanart getter function.
    
    Gets some fanart for the show from the backend.
    Calls back to back_end.fanart, but because that should be a list,
    just get the first item from that list.
    
    Args:
        beid (int): the backend ID for the show.
        
    Returns:
        str. A link to some fanart.
    """
    return back_end.fanart(beid)[0]
    
def add_update_show(dbid, beid, subgroup, config):
    """Show addition and modification function.
    
    Adds a given show to the backend, or edits it if its already there,
    and calls db.change_show to update the database with the backend id.
    
    Args:
        dbid (int): The database ID for the show.
        beid (int): The backend ID for the show.
        subgroup (str): The selected subgroup for the show, from our search engine.
        config (dict): The configuration dictionary.
    """
    back_end.add_update_show(beid, subgroup, config)
    db.change_show(id=dbid, beid=beid)

def remove_show(id, config):
    """Show removal function.
    
    Removes a show from the backend given it's database ID
    
    Args:
        dbid (int): The database ID for the show.
        config (dict): The configuration dictionary.
    """
    beid = db.get_show(id=id)['beid']
    back_end.remove_show(config, beid)
 
def get_shows_for_display(config, term=None):
    """Show getter function
    
    Gets shows from the scraper and preps them for display. If a term is
    provided, only get shows that include that term.
    
    Args:
        config (dict): The configuration dictionary.
    
    Keyword Args:
        term(str): A search term to filter on.
        
    Returns:
        tuple. 4 lists of shows.
        
            * watching -- Shows currently being watched.
            * airing -- TV shows being aired.
            * specials -- TV and Web Specials (OVA, ONA, etc.) airing or due to air.
            * movies -- Movies airing or due to premiere.
    """
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
    """First Time Setup Function
    
    Begins first time setup for aniping. Starts a new thread to scrape shows.
    
    Args:
        config (dict): The configuration dictionary.
        
    Returns:
        bool. Always returns true.
    """
    log.debug(">>>>>>Starting First Time Setup Thread<<<<<<")
    ftst = threading.Thread(target=scrape_shows, args=(config,))
    ftst.start()
    log.debug(">>>>>>Separate Thread Started<<<<<<")
    return True

def output_display_lists(watching, airing, specials, movies):
    """List output massage function
    
    Takes the display lists and massages them for output by removing
    watching shows from the other lists, handling date formats, and similar
    tasks.
    
    Args:
        watching (list): A list of shows currently being watched.
        airing (list): A list of TV shows currently airing.
        specials (list): A list of TV and web Specials airing or due to air this season.
        movies (list): A list of Movies airing or due to premiere this season.
        
    Returns:
        tuple. 4 lists of shows.
        
            * watching -- Shows currently being watched.
            * airing -- TV shows being aired.
            * specials -- TV and Web Specials (OVA, ONA, etc.) airing or due to air.
            * movies -- Movies airing or due to premiere.
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
    """Show scraper function
    
    Calls to the scraper to scrape shows and add them to the database. 
    Creates a lockfile in /tmp to ensure multiple scraping threads don't run
    simultaneously.
    
    Args:
        config (dict): The configuration dictionary.
    
    Returns:
        bool.
            
            * True -- Scrape is complete.
            * False -- Scrape lock file exists.
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
