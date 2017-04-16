#!/usr/bin/env python3
import requests, logging
from aniping.plugins import BackEnd

_logger = logging.getLogger(__name__)

class Sonarr(BackEnd):
    """Sonarr backend plugin.
    
    This plugin implements the sonarr backend for finding and downloading shows.
    """
    def __init__(self, config, plugin_manager):
        """Initilizes the sonarr backend plugin.
        
        Args:
            config (dict): The configuration dictionary as read by flask.
            plugin_manager (:obj:`AniPluginManager): An instance of the AniPluginManager.
        """
        super().__init__(config, plugin_manager)
        self.__name__       = "Sonarr"
        self.__id__         = "sonarr"
        self.__author__     = "Spencer Julian <hellothere@spencerjulian.com>"
        self.__version__    = "0.01"
        
        self.config = self._config['SONARR']
        self._name = self.config['NAME'] if 'NAME' in self.config else 'Sonarr'
        self._url = self.config['URL']
        self._api_key = self.config['API_KEY']
        self._library_path = self.config['LIBRARY_PATH']
        self._quality_profile = self._quality_profile_selected(self.config['QUALITY_PROFILE'])
        self._tag_prefix = "ap:"
    
    @property 
    def name(self):
        """str: Returns the plugin's name."""
        return self._name
    
    @property 
    def url(self):
        """str: Returns the configured url of the sonarr instance."""
        return self._url
    
    @property
    def api_key(self):
        """str: Returns the configured sonarr api key."""
        return self._api_key
        
    @property
    def _login_type(self):
        """str: Returns "basic" or "form", depending on what sort of logons sonarr requires. None if neither."""
        _logger.debug("Checking if sonarr requires logins.")
        out = requests.get(self.url)
        if out.status_code == 401:
            _logger.debug("Yes - basic.")
            return "basic"
        else:
            if "Sonarr - Login" in out.text:
                _logger.debug("Yes - form.")
                return "form"
        _logger.debug("No logins required.")
        return None
        
    def check_auth(self, username, password):
        """Checks if a user gives a correct username and password.
        
        User and pass are checked back against sonarr, 
        we do not handle our own authentication. Unfortunately,
        particularly with the form authentication, this is a bit
        fragile.
     
        Args:
            username (str): The username to check.
            password (str): The password to check.
     
        Returns:
            bool.
            
                * True -- user is authenticated
                * False -- user is not authenticated or an error occurred
                
        """
        _logger.debug("Entering check_auth")
        login_type = self._login_type
        if not login_type:
            _logger.debug("Sonarr does not have logins configured. Return logged in.")
            return True
        elif login_type == "basic":
            _logger.debug("Sonarr is using basic HTTP authentication, trying to authenticate...")
            sonarr_output = requests.get(self.url, auth=(username, password))
            if sonarr_output.status_code == 200:
                _logger.debug("Successful.")
                return True
            _logger.debug("Failed.")
        elif login_type == "form":
            _logger.debug("Sonarr is using form-based authentication. This is fragile for us. Trying to authenticate...")
            sonarr_output = requests.post(self.url + "/login", json={"username": username, "password": password})
            if "Sonarr Ver." in sonarr_output.text:
                return True
                _logger.debug("Successful.")
            _logger.debug("Failed.")
        return False
        
    def check_for_login(self):
        if not self._login_type:
            return False
        return True
        
    def search(self, term):
        """Searches sonarr for a particular show. 
        
        This searches whatever indexers sonarr has configured.
        
        Args:
            term (str): The title of the show we're searching for.
        
        Returns:
            list. A list of dictionaries describing the show in sonarr's format.
        """
        _logger.debug("Entering search. Trying to find show using Sonarr's search.")
        output = requests.get("{0}/api/series/lookup?term={1}&apikey={2}".format(self.url, term, self.api_key)).json()
        _logger.debug("Found {0} items.".format(len(output)))
        for item in output:
            _logger.debug("Item {0} has TVDB ID {1}".format(item['title'], item['tvdbId']))
            item['beid'] = item['tvdbId']
        return output
        
    def get_show(self, beid):
        """Gets a specific show from sonarr. 
        
        Because sonarr doesn't have internal IDs we can always use, we use the TVDB id
        to find a show, which should be just as unique. All this function
        does is call back_end.search with a ``tvdb:`` search keyword.
        
        Args:
            beid (int): The TVDB ID for the show.
            
        Returns:
            dict. A dictionary describing the show in sonarr's format.
        """
        _logger.debug("Entering get show. Getting show from sonarr - calling search with TVDB ID {0}".format(beid))
        output = self.search("tvdb:{0}".format(beid))
        _logger.debug("Returning {0}".format(output[0]['title']))
        return output[0]
        
    def get_watching_shows(self):
        """Get all of the shows we're downloading in sonarr. 
        
        This is basically just a list of shows in sonarr, because it doesn't store shows
        that are not being downloaded.
        
        Returns:
            list. A list of dictionaries decribing shows in sonarr's format.
        """
        _logger.debug("Entering get_watching_shows. Getting all shows being watched from sonarr.")
        shows = requests.get("{0}/api/series?apikey={1}".format(self.url, self.api_key)).json()
        for show in shows:
            show['beid'] = show['tvdbId']
        _logger.debug("Found {0} shows. Returning the list.".format(len(shows)))
        return shows
        
    def add_update_show(self, beid, subgroup):
        """Adds or edits a show in sonarr.
        
        Args:
            beid (int): The TVDB ID of the show we're adding or editing.
            subgroup (str): The subgroup we're using for this show.
        """
        _logger.debug("Entering add_update_show.")
        tag = self._subgroup_tag(subgroup)
        
        show = None
        _logger.debug("Getting all shows being watched and searching for show with ID {0}.".format(beid))
        shows = self.get_watching_shows()
        for item in shows:
            if int(item['tvdbId']) == int(beid):
                _logger.debug("Found show {0} with ID {1} in watching shows! Updating instead of creating.".format(item['title'], item['tvdbID']))
                show = item
        if not show:
            _logger.debug("Show not found in watching list, creating a new one.")
            show = self.get_show(beid)    
            payload = {
                "tvdbId":           int(beid),
                "title":            show['title'],
                "qualityProfileId": self._quality_profile,
                "titleSlug":        show['titleSlug'],
                "images":           show['images'],
                "seasons":          show['seasons'],
                "rootFolderPath":   self._library_path,
                "addOptions":       {"ignoreEpisodesWithFiles":True},
                "tags":             [tag]
            }
            out = requests.post("{0}/api/series?apikey={1}".format(self.url, self.api_key), json=payload)
        else:
            show['tags'] = [tag]
            requests.put("{0}/api/series?apikey={1}".format(self.url, self.api_key), json=show)
        
    def remove_show(self, beid):
        """Remove a given show from sonarr.

        It will not delete files. The backend ID we're given is not the ID we need, so the show
        is looked up first.
        
        Args:
            beid (int): The TVDB ID of the show.
        """
        _logger.debug("Entering remove_show. Getting all shows being watched from sonarr.")
        shows = self.get_watching_shows()
        _logger.debug("Got all shows. Attempting to find show with ID {0}".format(beid))
        show = [x for x in shows if x['beid'] == beid][0]
        _logger.debug("Found show {0}. Deleting.".format(show['title']))
        requests.delete("{0}/api/series/{1}?apikey={2}".format(self.url, show['id'], self.api_key))
        
    def subgroup_selected(self, beid):
        """Uses results from search to determine which subgroup is selected.
        
        We base it on the tags. Right now, the first tag is assumed to be the subgroup.
        
        Args:
            beid (int): The tvdb id of the show to get the subgroup for.
            
        Returns:
            str. The first tag on the show, which we assume to be the subgroup.
            None if none is found.
        """
        _logger.debug("Entering subgroup_selected. Getting subgroup from tags - calling get_watching_shows()")
        shows = self.get_watching_shows()
        for item in shows:
            _logger.debug("Checking if show ID {0} matches TVDB ID {1}".format(item['tvdbId'], beid))
            if item['tvdbId'] == beid:
                # Is an ID, needs to be a string.
                for tag in item['tags']:
                    label = self._get_tag(id=tag)
                    if label.startswith(self._tag_prefix):
                        _logger.debug("Match found! Returning tag {0}".format(label))
                        return label
        _logger.debug("No match found, returning None")
        return None
        
    def fanart(self, beid):
        """Returns a list of fanart URLs based on search results.
        
        Args:
            beid (int): The TVDB ID for the show to get fanart from.
            
        Returns:
            list. All fanart urls in the results.
        """
        _logger.debug("Entering fanart (backend). Getting show with ID {0}".format(beid))
        show = self.get_show(beid)
        _logger.debug("Found show {0}. Getting fanart links.".format(show['title']))
        fanart = [x['url'] for x in show['images'] if x['coverType'] == 'fanart']
        _logger.debug("Found {0} fanart links. Returning the list.".format(len(fanart)))
        return fanart

    def _quality_profile_selected(self, quality_profile_selected):
        """Translates a quality profile string from the config file to the ID in sonarr.
        
        Args:
            quality_profile_selected (str): The selected quality profile
            in the config file.
            
        Returns:
            int. The ID of the selected quality profile, or 1 if it wasn't found.
        """
        _logger.debug("Checking for selected quality profile {0} in sonarr".format(quality_profile_selected))
        profiles = requests.get("{0}/api/profile?apikey={1}".format(self.url, self.api_key))
        for profile in profiles.json():
            if profile['name'].lower().replace(" ","") == quality_profile_selected.lower().replace(" ",""):
                _logger.debug("Found quality profile {0} as ID {1}".format(profile['name'], profile['id']))
                return profile['id']
        _logger.debug("Quality profile {0} not found, defaulting to profile ID 1".format(quality_profile_selected))
        return 1
        
    def _subgroup_tag(self, subgroup):
        """Adds a subgroup tag and restriction if it doesn't exist in sonarr. Returns the tag if it does.
        
        Args:
            subgroup (str): The subgroup to add as a tag.
        
        Returns:
            int. The sonarr ID of the tag that was created.
        """
        _logger.debug("Entering subgroup_tag, Checking if tag exists already.")
        tag = self._get_tag(label=subgroup)
        if not tag:
            _logger.debug("Tag does not exist. Creating tag and restriction for subgroup {0}".format(subgroup))
            tag = requests.post("{0}/api/tag?apikey={1}".format(self.url, self.api_key), json={'label':self._tag_builder(subgroup)})
            restrict = requests.post("{0}/api/restriction?apikey={1}".format(self.url, self.api_key), json={'required': subgroup, 'tags': [tag.json()['id']]})
            return tag.json()['id']
        _logger.debug("Found the tag! Returning it.")
        return tag
        
    def _get_tag(self, label=None, id=None):
        """Searches the tags for a specific tag, and returns it if it's there.
        
        Args:
            label (str): the tag string we're searching for
            id (str): the tag ID we're searching for
            
        Returns:
            int. The sonarr ID of the tag if it exists. None if it does not.
        """
        _logger.debug("Entering get_tag. Getting all tags from sonarr.")
        tags = requests.get("{0}/api/tag?apikey={1}".format(self.url, self.api_key)).json()
        if label:
            _logger.debug("Found {0} tags. Checking if {1} is in them.".format(len(tags), label))
            for checktag in tags:
                if self._tag_builder(label) == checktag['label']:
                    _logger.debug("Found tag {0} with ID {1}!".format(checktag['label'], checktag['id']))
                    return checktag['id']
        if id:
            _logger.debug("Found {0} tags. Checking if ID {1} is in them.".format(len(tags), id))
            for checktag in tags:
                if checktag['id'] == id:
                    _logger.debug("Found tag id {0} with label {1}!".format(checktag['id'], checktag['label']))
                    return checktag['label']
        _logger.debug("Couldn't find any relevant tags, returning None.")
        return None
        
    def _tag_builder(self, tag):
        """Builds the tag name to ensure continuity between tag functions.
        
        Args:
            tag (str): The tag to build.
            
        Returns:
            str. The build tag, complete with prefix and munged
            appropriately.
        """
        return "{0}{1}".format(self._tag_prefix, tag.lower().replace(" ","_"))
        