#!/usr/bin/env python3
import os, requests, time, shutil, json, sys, logging
from datetime import date
from aniping.plugins import Scraper

log = logging.getLogger(__name__)

class Anilist(Scraper):
    """Anilist Scraper Plugin.
    
    This plugin implements the anilist scraper and tracker for getting show information.
    """
    def __init__(self, config, plugin_manager):
        """Initilizes the anilist scraper plugin.
        
        Args:
            config (dict): The configuration dictionary as read by flask.
            plugin_manager (:obj:`AniPluginManager): An instance of the AniPluginManager.
        """
        super().__init__(config, plugin_manager)
        self.__name__       = "Anilist"
        self.__id__         = "anilist"
        self.__author__     = "Spencer Julian <hellothere@spencerjulian.com>"
        self.__version__    = "0.01"
        
        self.config = self._config['ANILIST']
        self._image_cache = self._config['IMAGE_CACHE']
        self._client_id = self.config['CLIENT_ID']
        self._client_secret = self.config['CLIENT_SECRET']
        self._name = self.config['NAME'] if 'NAME' in self.config else 'Anilist'
        
        self._url = "https://anilist.co"
        self._api_url = "{0}/api".format(self._url)
        self._access_token = None
        self._access_token_expiry = int(time.time())
        
    @property
    def name(self) -> str:
        """str: Returns the name of the plugin."""
        return self._name
        
    @property
    def url(self) -> str:
        """str: Returns the url of anilist."""
        return self._url
        
    def get_shows_by_category(self, search_results=None):
        """Gets all shows from the DB and seperates into watching, tv, movies, and specials.
                   
        Keyword Args:
            search_results (str): A list of database shows to parse into
                                  the separate lists instead of all shows.
        
        Returns:
            tuple. 4 lists of shows.
            
                * watching -- Shows currently being watched.
                * airing -- TV shows being aired.
                * specials -- TV and Web Specials (OVA, ONA, etc.) airing or due to air.
                * movies -- Movies airing or due to premiere.
        """
        if not search_results:
            log.debug("No list of shows provided, so getting all listed shows.")
            search_results = self.db("get_all_shows")
        watching = []
        log.debug("Getting shows being watched from backend.")
        be_watching = self.back_end("get_watching_shows")
        log.debug("WATCHING SHOWS:\n====================\n{0}".format(be_watching))
        for item in be_watching:
            log.debug("Attempting to get information for show {0} with backend ID {1}".format(item['title'],item['beid']))
            db_show = self.db("get_show", beid=item['beid'])
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
        
    def scrape_shows(self):
        """Checks our anilist for shows and updates them in the database if they're there. 
        
        If not, adds them. Deletes everything else.
        Typically run in a separate thread from the main server instance.
        Should run regularly to keep the database up to date.
        
        Args:
            config (dict): The configuration dictionary.
        """
        log.debug("Starting to scrape shows.")
        sys.stdout.flush()
        log.debug("Getting all shows from DB...")
        all_shows = self.db("get_all_shows")
        log.debug("ALL SHOWS\n====================\n{0}".format(all_shows))
        log.debug("Getting this seasons's shows")
        airing_list = self._get_season_shows()
        log.debug("SEASON SHOWS\n====================\n{0}".format(airing_list))
        # Clean out shows from the list that aren't airing.
        log.debug("Cleaning show list to get this season's airing shows...")
        airing_ids = [show['id'] for show in airing_list]
        delete_shows = [x for x in all_shows if x['aid'] not in airing_ids]
        log.debug("SHOWS TO DELETE\n====================\n{0}".format(delete_shows))
        
        for show in delete_shows:
            log.debug("Calling DB to remove show {0} with ID {1}".format(show['title'], show['id']))
            self.db("remove_show", id=show['id'])
        
        for show in airing_list:
            log.debug("Calling to update show {0} with ID {1}".format(show['title_romaji'], show['id']))
            self._update_show(show['id'])
        
    def _require_access_token(func):
        """Access token decorator function.
        
        Decorates functions that require the anilist access token. Checks
        if the token is valid and generates a new one if it is not.
        
        Returns:
            The response of the function.
        """
        def wrapper(self, *args, **kwargs):
            if not self._access_token_valid():
                self._get_access_token()
            return func(self, *args, **kwargs)
        return wrapper
       
    def _access_token_valid(self):
        """Checks if the access token is valid and not expired.
        
        Returns:
            True if it is valid. False otherwise.
        """
        if not self._access_token or (int(self._access_token_expiry) - int(time.time())) < 300:
            return False
        return True
    
    def _get_access_token(self):
        """If the locally cached token hasn't expired, use it. Otherwise, get a new token from anilist.

        Returns:
            str. The access token.
        """
        new_token = requests.post(
                "{0}/auth/access_token?grant_type=client_credentials&client_id={1}&client_secret={2}".format(self._api_url, self._client_id, self._client_secret)
                ).json()
        self._access_token=new_token['access_token']

    def _get_season_string(self, season_int=None):
        """Season string generator.
        
        Generates this month's season name, or the season name from a given season int.
        A season int is defined by anilist as "First 2 numbers are the year (16 is 2016). 
        Last number is the season starting at 1 (3 is Summer)."
        
        Keyword Args:
            season_int (int): An optional season int from anilist for a season.

        Returns:
            The season (winter, spring, summer, or fall) as a string.
        """
        monthsToSeasons = {(1,2,3):'winter', (4,5,6):'spring', (7,8,9):'summer', (10,11,12):'fall'}
        seasonIntToSeasons = {1:'winter', 2:'spring', 3:'summer', 4:'fall'}
        if season_int:
            season = seasonIntToSeasons[int(str(season_int)[2:])]
        else:
            targetDate = date.today()
            season = next(val for key, val in monthsToSeasons.items() if targetDate.month in key)
        return season

    @_require_access_token
    def _get_remote_show_info(self, aid):
        """Gets a show's information from anilist. 
        
        Munges the data as necessary to fit appropriately in the database.

        Args:
            aid (int): The anilist ID of the show to grab.

        Returns:
            dict. The show's description in the aniping database format.
            A database show is a dictionary with the following structure.
        
                * ``id``:               database id (int)
                * ``aid``:              scraper id (int)
                * ``beid``:             backend id (int)
                * ``type``:             type of show, such as 'tv', 'ova', or 'movie'. (str)
                * ``title``:            the official show title from the scraper (str)
                * ``alt_title``:        the shows alternate title, such as an english
                                        translated title. (str)
                * ``total_episodes``:   The total number of episodes in the show (int)
                * ``next_episode``:     The next episode to air, according to the scraper (int)
                * ``next_episode_date``:The day the next episode is due to air from the scraper (int)
                * ``start_date``:       The day the first episode starts, from the scraper (int)
                * ``genre``:            A comma separated list of show genres. (str)
                * ``studio``:           The primary studio producing the show (str)
                * ``description``:      A synopsis or description for the show (str)
                * ``link``:             A link to a page describing the show, such as anilist. (str)
                * ``image``:            A relative link to the show's poster. (str)
                * ``airing``:           The airing status of the show according to the scraper (str)
                * ``season_name``:      The name of the season: winter, spring, summer, or fall (str)
                * ``starred``:          Whether the show is highlighted or not (int)
        """
        os.makedirs(self._image_cache, exist_ok=True)
        cache_contents = os.listdir(self._image_cache)
        ani_show = requests.get("{0}/anime/{1}/page?access_token={2}".format(self._api_url, str(aid), self._access_token))
        if ani_show.status_code == 410:
            return None
        ani_show = ani_show.json()
        show = {}
        show['type'] = ani_show['type']
        show['title'] = ani_show['title_romaji']
        show['alt_title'] = ani_show['title_english']
        show['synonyms'] = "|".join(ani_show['synonyms'])
        show['link'] = '{0}/anime/{1}'.format(self._url,ani_show['id'])
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
            image_request = requests.get(grab_image, stream=True)
            with open(os.path.join(self._image_cache,filename), 'wb') as f:
                shutil.copyfileobj(image_request.raw, f)
            del image_request

        show['image'] = os.path.join(self._image_cache, filename)
        show['aid'] = ani_show['id']

        return show
    
    @_require_access_token
    def _get_season_shows(self):
        """Gets the list of this season's shows from anilist.
                    
        Returns:
            list. A list of shows in the anilist format. These are
            expected to be run through _get_remote_show_info, as anilist
            does not provide everything for every show in this output.
        """
        target_date = date.today()
        airing_list = requests.get("{0}/browse/anime?year={1}&season={2}&full_page=true&access_token={3}".format(self._api_url,target_date.year,self._get_season_string(),self._access_token))

        return airing_list.json()

    @_require_access_token
    def _update_show(self, aid):
        """Adds or edits a show in the local database based on anilist id. 
        
        Used by the scraper to add and update show information. Sleeps for a tenth of a second
        after each call to help prevent rate-limiting by anilist.
        
        Args:
            aid (int): Anilist ID of the show to update.      
        """
        show = self._get_remote_show_info(aid)
        if not show:
            return None
            
        local_show = self.db("get_show", aid=aid)
        if not local_show:
            self.db("add_show", show['aid'], show['type'], show['title'], show['alt_title'], show['synonyms'], show['total_episodes'], show['next_episode'], show['next_episode_date'], show['start_date'], show['genre'], show['studio'], show['description'], show['link'], show['image'], show['airing'], self._get_season_string(show['season']))
        else:
            self.db("change_show", aid=show['aid'], show_type=show['type'], title=show['title'], alt_title=show['alt_title'], synonyms=show['synonyms'], total_episodes=show['total_episodes'], next_episode=show['next_episode'], next_episode_date=show['next_episode_date'], start_date=show['start_date'], genre=show['genre'], studio=show['studio'], description=show['description'], link=show['link'], image=show['image'], airing=show['airing'], season_name=self._get_season_string(show['season']))

        # Don't want to be killed by too many requests in too short of a period,
        # so self-rate limit to about 10 requests per second.
        time.sleep(0.1)