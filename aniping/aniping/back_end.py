#!/usr/bin/env python3
"""back_end

This submodule handles functions dealing with the aniping backend
instance, sonarr in this case.

This is a terminal submodule for the aniping package, and so should
not import any additional aniping submodules.
"""
import requests, logging

log = logging.getLogger(__name__)


def check_auth(username, password, config):
    """Authentication check function.
    
    Checks if a user gives a correct username and password.
    User and pass are checked back against sonarr, 
    we do not handle our own authentication. Unfortunately,
    particularly with the form authentication, this is a bit
    fragile.
 
    Args:
        username (str): The username to check.
        password (str): The password to check.
        config (dict): The configuration dictionary
 
    Returns:
        bool.
        
            * True -- user is authenticated
            * False -- user is not authenticated or an error occurred
            
    """
    log.debug("Entering check_auth")
    login_type = check_for_login(config)
    if not login_type:
        log.debug("Sonarr does not have logins configured. Return logged in.")
        return True
    elif login_type == "basic":
        log.debug("Sonarr is using basic HTTP authentication, trying to authenticate...")
        sonarr_output = requests.get(config['SONARR']['URL'], auth=(username, password))
        if sonarr_output.status_code == 200:
            log.debug("Successful.")
            return True
        log.debug("Failed.")
    elif login_type == "form":
        log.debug("Sonarr is using form-based authentication. This is fragile for us. Trying to authenticate...")
        sonarr_output = requests.post(config['SONARR']['URL'] + "/login", json={"username": username, "password": password})
        if "Sonarr Ver." in sonarr_output.text:
            return True
            log.debug("Successful.")
        log.debug("Failed.")
    return False
    
def check_for_login(config):
    """Login check function.
    
    Checks if logins are enabled for sonarr, and if so, checks
    which kind we need (forms or basic).
    
    Args:
        config (dict): the configuration dictionary
        
    Returns:
        str.
        
            * ``form`` for form-based login
            * ``basic`` for basic http login
            * None for no login required
    """
    log.debug("Checking if sonarr requires logins.")
    out = requests.get(config['SONARR']['URL'])
    if out.status_code == 401:
        log.debug("Yes - basic.")
        return "basic"
    else:
        if "Sonarr - Login" in out.text:
            log.debug("Yes - form.")
            return "form"
    log.debug("No logins required.")
    return None
    
def search(term, config):
    """Sonarr search function
    
    Searches sonarr for a particular show. This searches
    whatever indexers sonarr has configured.
    
    Args:
        term (str): The title of the show we're searching for.
        config (dict): The configuration dictionary.
    
    Returns:
        list. A list of dictionaries describing the show in sonarr's format.
    """
    log.debug("Entering search. Trying to find show using Sonarr's search.")
    output = requests.get("{0}/api/series/lookup?term={1}&apikey={2}".format(config['SONARR']['URL'], term, config['SONARR']['API_KEY'])).json()
    log.debug("Found {0} items.".format(len(output)))
    for item in output:
        log.debug("Item {0} has TVDB ID {1}".format(item['title'], item['tvdbId']))
        item['beid'] = item['tvdbId']
    return output
    
def get_show(id, config):
    """Show getter function
    
    Gets a specific show from sonarr. Because sonarr doesn't have
    internal IDs we can always use, we use the TVDB id
    to find a show, which should be just as unique. All this function
    does is call back_end.search with a ``tvdb:`` search keyword.
    
    Args:
        id (int): The TVDB ID for the show.
        config (dict): The configuration dictionary.
        
    Returns:
        dict. A dictionary describing the show in sonarr's format.
    """
    log.debug("Entering get show. Getting show from sonarr - calling search with TVDB ID {0}".format(id))
    output = search("tvdb:{0}".format(id), config)
    log.debug("Returning {0}".format(output[0]['title']))
    return output[0]
    
def subgroup_selected(beid, config):
    """Subgroup getter function.
    
    Uses results from search to determine which subgroup is selected.
    We base it on the tags. Right now, the first tag is assumed to be
    the subgroup.
    
    Args:
        beid (int): The tvdb id of the show to get the subgroup for.
        config (dict): The configuration dictionary.
        
    Returns:
        str. The first tag on the show, which we assume to be the subgroup.
        None if none is found.
    """
    shows = get_watching_shows(config)
    for item in shows:
        if item['tvdbId'] == beid:
            # Is an ID, needs to be a string.
            return item['tags'][0]
    return None
    
def fanart(search_results):
    """Fanart getter function.
    
    Returns a list of fanart URLs based on search results.
    
    Args:
        search_results (list): Results from an earlier sonarr search.
        
    Returns:
        list. All fanart urls in the results.
    """
    return [x['url'] for x in search_results['images'] if x['coverType'] == 'fanart']
    
def add_update_show(tvdb, subgroup, config):
    """Show updater function.
    
    Adds or edits a show in sonarr.
    
    Args:
        tvdb (int): The TVDB ID of the show we're adding or editing.
        subgroup (str): The subgroup we're using for this show.
        config (dict): The configuration dictionary.
    """
    tag = subgroup_tag(subgroup, config)
    quality = get_quality_profile(config)
    
    show = None
    shows = get_watching_shows(config)
    for item in shows:
        if int(item['tvdbId']) == int(tvdb):
            show = item
    if not show:
        show = get_show(tvdb, config)    
        payload = {
            "tvdbId":           int(tvdb),
            "title":            show['title'],
            "qualityProfileId": quality,
            "titleSlug":        show['titleSlug'],
            "images":           show['images'],
            "seasons":          show['seasons'],
            "rootFolderPath":   config['LIBRARY_PATH'],
            "addOptions":       {"ignoreEpisodesWithFiles":True},
            "tags":             [tag]
        }
        out = requests.post("{0}/api/series?apikey={1}".format(config['SONARR']['URL'], config['SONARR']['API_KEY']), json=payload)
    else:
        show['tags'] = [tag]
        requests.put("{0}/api/series?apikey={1}".format(config['SONARR']['URL'], config['SONARR']['API_KEY']), json=show)
    
def subgroup_tag(subgroup, config):
    """Subgroup tag creation function.
    
    Adds a subgroup tag and restriction if it doesn't exist
    in sonarr. Returns the tag if it does.
    
    Args:
        subgroup (str): The subgroup to add as a tag.
        config (dict): The configuration dictionary.
    
    Returns:
        int. The sonarr ID of the tag that was created.
    """
    tag = get_tag(subgroup, config)
    if not tag:
        tag = requests.post("{0}/api/tag?apikey={1}".format(config['SONARR']['URL'], config['SONARR']['API_KEY']), json={'label':subgroup.lower().replace(" ", "_")})
        restrict = requests.post("{0}/api/restriction?apikey={1}".format(config['SONARR']['URL'], config['SONARR']['API_KEY']), json={'required': subgroup, 'tags': [tag.json()['id']]})
        return tag.json()['id']
    return tag
    
def get_tag(tag, config):
    """Tag getter function.
    
    Searches the tags for a specific tag, and returns it
    if it's there.
    
    Args:
        tag (str): the tag we're searching for
        config (dict): the configuration dictionary
        
    Returns:
        int. The sonarr ID of the tag if it exists. None if it does not.
    """
    tags = requests.get("{0}/api/tag?apikey={1}".format(config['SONARR']['URL'], config['SONARR']['API_KEY']))
    for checktag in tags.json():
        if tag.lower().replace(" ", "_") == checktag['label']:
            return checktag['id']
    return None
    
def get_quality_profile(config):
    """Quality profile getter.
    
    Get the quality profile ID from the string listed in the
    configuration dictionary.
    
    Args:
        config (dict): The configuration dictionary
    
    Returns:
        int. The profile id if it is found, defaults to 1 if it is not.
    """
    profiles = requests.get("{0}/api/profile?apikey={1}".format(config['SONARR']['URL'], config['SONARR']['API_KEY']))
    for profile in profiles.json():
        if profile['name'].lower().replace(" ","") == config['SONARR']['QUALITY_PROFILE'].lower().replace(" ",""):
            return profile['id']
    
    # Default to whatever the first quality profile is
    return 1
    
def get_watching_shows(config):
    """Show getter function.
    
    Get all of the shows we're downloading in sonarr. This is basically
    just a list of shows in sonarr, because it doesn't store shows
    that are not being downloaded.
    
    Args:
        config (dict): The configuration dictionary
    
    Returns:
        list. A list of dictionaries decribing shows in sonarr's format.
    """
    shows = requests.get("{0}/api/series?apikey={1}".format(config['SONARR']['URL'], config['SONARR']['API_KEY'])).json()
    for show in shows:
        show['beid'] = show['tvdbId']
    return shows
    
def remove_show(config, id):
    """Show remover function.
    
    Remove a given show from sonarr. It will not delete files.
    The backend ID we're given is not the ID we need, so the show
    is looked up first.
    
    Args:
        config (dict): the configuration dictionary.
        id (int): The TVDB ID of the show.
    """
    shows = get_watching_shows(config)
    show = [x for x in shows if x['beid'] == id][0]
    requests.delete("{0}/api/series/{1}?apikey={2}".format(config['SONARR']['URL'], show['id'], config['SONARR']['API_KEY']))
