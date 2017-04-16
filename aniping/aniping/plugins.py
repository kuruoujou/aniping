#/usr/bin/env python3
import logging, os, importlib, sys
from typing import Optional

_logger = logging.getLogger(__name__)

CATEGORIES={
    "back_end": {"directory": "back_end", "multiload": False, "class": "BackEnd", "config": "BACK_END"},
    "scraper": {"directory": "scraper", "multiload": True, "class": "Scraper", "config": "SCRAPER"},
    "db": {"directory": "db", "multiload": False, "class":"DataBase", "config": "DATABASE"},
    "search":{"directory": "search", "multiload": True, "class": "SearchEngine", "config": "SEARCH"}
    }

class AniPluginManager(object):
    """Plugin manager for aniping plugins.
    
    Handles loading and scanning of plugins, as well as calling functions within those plugins.
    Some plugins can be multiloaded - meaning multiple plugins of that type can be loaded -
    and others can only be loaded once, like the database.
    """
    def __init__(self, config):
        """AniPluginManger initializer.
        
        Intilizes the aniping plugin manager.
        
        Note:
            This does not scan for or load plugins, that must be done explicitly.
        
        Args:
            config (dict): The configuration dictionary loaded by Flask.
        """
        _logger.debug("AniPluginManager initializing!")
        self._config = config
        self._available_plugins = {cat:[] for cat,v in CATEGORIES.items()}
        self._loaded_plugins = {cat:[] for cat,v in CATEGORIES.items()}
        _logger.debug("Initialized!")
        
    @property
    def available_plugins(self) -> dict:
        """dict: Dictionary of available plugins, keyed by plugin type."""
        return self._available_plugins
        
    @property
    def loaded_plugins(self) -> dict:
        """dict: Dictionary of loaded plugin classes, keyed by plugin type."""
        out={}
        for cat,clses in self._loaded_plugins.items():
            out[cat] = []
            for cls in clses:
                out[cat].append(cls)
        return out
        
    @property
    def plugin_categories(self) -> list:
        """dict: Plugin categories that key available and loaded plugins."""
        return list(CATEGORIES.keys())
        
    def scan_for_plugins(self):
        """Plugin scanner.
        
        Scans for plugins in the known plugin directories. Adds them to the
        available plugins dictionary, ready to be loaded.
        
        Returns:
            The available plugins dictionary.
        """
        for category,info in CATEGORIES.items():
            for module in os.listdir(os.path.join(os.path.dirname(__file__),info["directory"])):
                if module == "__init__.py" or module[-3:] != ".py":
                    continue
                importlib.import_module("aniping.{0}.{1}".format(info["directory"], module[:-3]))
                self._available_plugins[category].append(module[:-3])
        return self._available_plugins
        
    def load_plugins(self):
        """Plugin loader.
        
        Loads plugins that are configured in config.yml. Adds the instanciated
        class instance to a dictionary for use by the plugin callers.
        
        Returns:
            The loaded plugins dictionary.
        """
        for category,catinfo in CATEGORIES.items():
            if catinfo["config"] in self._config:
                plugins_to_load = self._config[catinfo["config"]] if isinstance(self._config[catinfo["config"]], list) else [self._config[catinfo["config"]]]
                for cls in eval(catinfo["class"]).__subclasses__():
                    if not any(isinstance(x, cls) for x in self._loaded_plugins[category]):
                        if catinfo["multiload"] and cls.__name__ in plugins_to_load:
                            self._loaded_plugins[category].append(cls(self._config, self))
                        elif not catinfo["multiload"] and cls.__name__ == plugins_to_load[0]:
                            self._loaded_plugins[category].append(cls(self._config, self))
        return self._loaded_plugins
        
    def plugin_category_function(self, category, func, *args, **kwargs):
        """Call all plugins of a specified category with a function.
        
        Attempts to call the function in all plugins. Function should only be something
        defined in the plugin's base class.
        
        Args:
            category (str): The plugin category to call.
            func (str): The function to call in that category.
            *args: Arguments that will be passed to the function.
            **kwargs: Keyword arguments that will be passed to the function.
        
        Returns:
            If it's a multiloaded function, it will return a list of all of the responses
            from the all of the plugins. If it is not, it will just return the response
            from the function.
        """
        for cls in self._loaded_plugins[category]:
            if not CATEGORIES[category]["multiload"]:
                return getattr(cls,func)(*args, **kwargs)
            else:
                output = []
                output.append(getattr(cls,func)(*args, **kwargs))
                return output
    
    def plugin_function(self, plugin, func, *args, **kwargs):
        """Call a specific plugin's function.
        
        This is useful if you have plugins of different types that interact directly.
        Should be used incredibly sparingly.
        
        Args:
            plugin (str): The plugin to call.
            func (str): The function to call from the plugin.
            *args: Arguments that will be passed to the function.
            **kwargs: Keyword arguments that will be passed to the function.
            
        Returns:
            The plugin function's response.
        """
        for category, classes in self._loaded_plugins.items():
            for cls in classes:
                if cls.__id__ == plugin:
                    return getattr(cls,func)(*args, **kwargs)

    
class AniPlugin(object):
    """Base Aniping Plugin Class.
    
    This class should never be extended from directly by a plugin, with
    the exception of the front-end. Everything else should extend from one of this
    class' subclasses.
    
    Several attributes are defined here that should be defined for all plugins.
    
    Attributes:
        __name__ (str): The name of the plugin.
        __id__ (str): The plugin's ID. This is what is used to load the plugin.
        __author__ (str): The plugin's author.
        __version__ (str): The version of the plugin. Optional, but set it to 0.01 if not in use.
        apm (:obj:`AniPluginManager`): An AniPluginManager instantiation. Should only be used by plugins sparingly, use helper methods when possible.
    """
    def __init__(self, config, plugin_manager):
        """Initilizes the plugin.
        
        Sets up the attributes for the plugin.
        
        Note:
            Always call super().__init__(config, plugin_manager) from your plugins, or else you
            may not get all of the helper functions, or may not even be loaded.
            
        Args:
            config: The configuration dictionary passed to the AniPluginManager instance.
            plugin_manager: The AniPluginManager instance used to instantiate this plugin.
        """
        self.__name__       = None
        self.__id__         = None
        self.__author__     = None
        self.__version__    = None
        
        self._config = config
        self.apm = plugin_manager
        
    @property
    def name(self) -> Optional[str]:
        """str: Should return the name of your plugin, but is optional."""
        return None
        
    def back_end(self, func, *args, **kwargs):
        """Calls back_end functions.
        
        This is a helper function which calls functions from the back_end category.
        Remember back_ends are not multiloaded, so you will only get a single response
        from whatever function is called.
        
        Args:
            func (str): The function to call from the back_end plugin.
            *args: The arguments to pass to the plugin.
            **kwargs: The keyword arguments to pass to the plugin.
        
        Returns:
            The response of the function you called.
        """
        return self.apm.plugin_category_function("back_end", func, *args, **kwargs)
        
    def scraper(self, func, *args, **kwargs):
        """Calls scraper functions.
        
        This is a helper function which calls functions from the scraper category.
        Remember that scrapers are multiloaded, so you will get a list of responses.
        
        Args:
            func (str): The function to call from the scraper plugins.
            *args: The arguments to pass to the plugins.
            **kwargs: The keyword arguments to pass to the plugins.
        
        Returns:
            A list of responses of the function you called from each plugin.
        """
        return self.apm.plugin_category_function("scraper", func, *args, **kwargs)
        
    def db(self, func, *args, **kwargs):
        """Calls database functions.
        
        This is a helper function which calls functions from the database category.
        Remember databases are not multiloaded, so you will only get a single response
        from whatever function is called.
        
        Args:
            func (str): The function to call from the database plugin.
            *args: The arguments to pass to the plugin.
            **kwargs: The keyword arguments to pass to the plugin.
        
        Returns:
            The response of the function you called.
        """
        return self.apm.plugin_category_function("db", func, *args, **kwargs)
        
    def search(self, func, *args, **kwargs):
        """Calls search_engine functions.
        
        This is a helper function which calls functions from the search_engine category.
        Remember that search_engines are multiloaded, so you will get a list of responses.
        
        Args:
            func (str): The function to call from the search_engine plugins.
            *args: The arguments to pass to the plugins.
            **kwargs: The keyword arguments to pass to the plugins.
        
        Returns:
            A list of responses of the function you called from each plugin.
        """
        return self.apm.plugin_category_function("search", func, *args, **kwargs)
        
class SearchEngine(AniPlugin):
    """Base Search Engine Class.
    
    Extend this class if you are making a SearchEngine plugin.
    
    Search engines are only used by aniping to find specific sub and release groups
    that are work on a given show. Examples of search engines include Nyaa Torrents
    or Google if you're ambitious.
    
    Note:
        Check the AniPlugin Class documentation for details on what must
        be included with all plugins. This documentation only describes what
        is needed with search engine plugins.
    """
    @property
    def url(self) -> str:
        """str: Should return the URL of your search engine."""
        return None
               
    def results(self, query):
        """Searches for a show and returns results.
        
        This function will search the search engine for a given query, typically
        a show title.
        
        Args:
            query (str): The query to pass to the search engine. Typically a show title.
        
        Returns:
            Should return a tuple with two lists. 
            
                * groups - A list of subgroups parsed from search results.
                * results - The raw search results.
        """
        raise NotImplementedError()
        
class Scraper(AniPlugin):
    """Base scraper class.
    
    Extend this class if you are making a Scraper plugin.
    
    Scrapers are used to collect the list of shows airing in a given season, as well as their
    descriptions, air dates, images, and most of the other metadata. Most of this class is
    usually run in a separate, spawned thread to download information without blocking the 
    web server.
    
    Examples of scrapers include anilist, myanimelist, or hummingbird.
    
    Note:
        Check the AniPlugin Class documentation for details on what must
        be included with all plugins. This documentation only describes what
        is needed with search engine plugins.
    """
    @property
    def url(self) -> str:
        """str: Should return the URL of your scraper."""
        return None
        
    def get_shows_by_category(self, search_results=None):
        """Gets show from the database and backend by category.
        
        Should gets all shows from the DB and seperates into watching,
        tv, movies, and specials. You'll probably need to contact the
        backend to get shows being watched.
        
        This is a scraper function because it relies on categories that
        should be provided by the scraper. However, they should be separated
        into the 4 described below.
                    
        Keyword Args:
            search_results (str): A list of database shows to parse into
                                  the separate lists instead of all shows.
                                  When none, should return all shows from db
                                  using ``self.db("get_all_shows")``
        
        Returns:
            tuple. 4 lists of shows.
            
                * watching -- Shows currently being watched.
                * airing -- TV shows being aired.
                * specials -- TV and Web Specials (OVA, ONA, etc.) airing or due to air.
                * movies -- Movies airing or due to premiere.
        """
        raise NotImplementedError()
    
    def scrape_shows(self):
        """Gets shows from the scraper service and adds them to the database.
        
        Scraper is a bit of a misnomer, but don't worry about that.
        
        This should check your scraper service for all shows airing this season
        and either add them to the database or update them if they are already there.
        It should delete anything in the database that is not airing - the back end
        should keep track of shows that have not yet finished but still ongoing.
        
        This will almost always be run in a separate thread from the main server instance,
        so keep that in mind when building and debugging, because things like "print" may
        not work as expected.
        
        This will run weekly or as configured.
        """
        raise NotImplementedError()

class DataBase(AniPlugin):
    """Base Database Class.
    
    Extend this class if you are making a database plugin.
    
    Databases store the ongoing shows and shows being watched for aniping, as well
    as the shows that are starred and the like. Check the ``add_show`` method for 
    the expected schema for that table, and the ``add_login_id`` method for the exepcted
    schema for the session_id table.
    
    Examples of databases include sqlite3 and mysql, but plugins
    can also be configured for things such as json or even plain text.
        
    Note:
        Check the AniPlugin Class documentation for details on what must
        be included with all plugins. This documentation only describes what
        is needed with search engine plugins.
    """
    @property
    def db_loc(self) -> Optional[str]:
        """str: the location of your database. Can be a url or a filename, or anything else really."""
        return None
        
    @property
    def db_schema(self) -> Optional[str]:
        """str: The database's schema. Can be read from an external file or simply added here."""
        return None
        
    def get_login_id(self, session_id):
        """Gets a session ID from the database.
        
        Should get a session id from the database if it hasn't expired.
        Should delete it if it has.
        
        Args:
            session_id (int): The session id to lookup in the database.
        
        Returns:
            Should return the session_id if it is valid, or `None` if it is not.
        """
        raise NotImplementedError()
        
    def add_login_id(self, session_id, expiry):
        """Adds session IDs to the database.
        
        Writes a session ID for a user to the database. The table should include
        a minimum of the two columns below. They are the only two used by the rest
        of aniping.
        
        Note:
            The column names do not need to match the argument names, provided they are
            stored as expected. Also, any additional columns you add will not be used by
            aniping, so will be limited to internal use to this plugin, and potentially
            other plugins.
        
        Args:
            session_id (int): the session ID to add to the database.
            expiry (int): The expiration date and time of the session id
                          as a unix timestamp. Typically now + 2 hours.
        """
        raise NotImplementedError()
    
    def delete_login_id(self, session_id):
        """Deletes session IDs from the database.
        
        Deletes a session id from the database.
        
        Args:
            session_id (int): The session id to delete.
        """
        raise NotImplementedError()
        
    def add_show(self, aid, show_type, title, alt_title, synonyms, total_episodes, next_episode,
                next_episode_date, start_date, genre, studio, description, link, image,
                airing, season_name):
        """Adds show to the database.
        
        All arguments are required. The scraper should gather these arguments and pass them to
        this function in the expected format, which is described below. Build your database
        schema based on that.
        
        Note:
            The column names do not need to match the argument names, provided they are stored
            as expected. Also, any additional columns you add will not be used by aniping, so
            will be limited to intenal use to this plugin, and potentially other plugins.

        Args:
            aid (int): The scraper ID of the show
            show_type (str): The type of show being added (tv, ona, ova, movie, etc.)
            title (str): The show's title
            alt_title (str): The show's alternate title. May be the same as the title.
            synonyms (str): A pipe-separated (|) list of synonyms for the show.
            total_episodes (int): The show's total number of episodes
            next_episode (int): The next airing episode
            next_episode_date (int): The next airing episode's scheduled date as a unix timestamp.
            start_date (int): The date the show starts or started as a unix timestamp.
            genre (str): A comma-separated list of genres for the show
            studio (str): The show's primary studio
            description (str): A brief description or synopsis for the show
            link (str): A link to more info - anilist, mal, etc.
            image (str): The locally cached link to the image for the show.
            airing (str): The airing status of the show.
            season_name (str): The season string of the show (winter, spring, summer, fall)
        """
        raise NotImplementedError()
        
    def change_show(self, id=None, aid=None, beid=None, show_type=None, title=None, alt_title=None, 
                synonyms=None, total_episodes=None, next_episode=None, next_episode_date=None, start_date=None, 
                genre=None, studio=None, description=None, link=None, image=None, airing=None, 
                season_name=None, starred=None):
        """Modifies a show in the database.
        
        One of id, aid, or beid is required to look up the show, but all other arguments are optional. If multiple of 
        id, aid, and beid are provided, they should be handled in the order id, aid, beid, and anything following the 
        first match should be considered an update for the database.
        
        Example:
            If you want to change the title for a show and have it's beid::
            
                db.change_show(beid=12345, title="My Show")
                
            But if you want to change the beid for a show and you have it's 
            database id::
            
                db.change_show(id=10, beid=54321)

        Keyword Args:
            id (int): The show's database ID
            aid (int): The scraper ID of the show
            beid (int): The backend ID of the show
            show_type (str): The type of show being added (tv, ona, ova, movie, etc.)
            title (str): The show's title
            alt_title (str): The show's alternate title. May be the same as the title.
            synonyms (str): A pipe-separated (|) list of synonyms for the show.
            total_episodes (int): The show's total number of episodes
            next_episode (int): The next airing episode
            next_episode_date (int): The next airing episode's scheduled date as a unix timestamp.
            start_date (int): The date the show starts or started. as a unix timestamp.
            genre (str): A comma-separated list of genres for the show
            studio (str): The show's primary studio
            description (str): A brief description or synopsis for the show
            link (str): A link to more info - anilist, mal, etc.
            image (str): The locally cached link to the image for the show.
            airing (str): The airing status of the show.
            season_name (str): The season string of the show (winter, spring, summer, fall)
            starred (int): The highlight status of the show. 1=True, 0=False.
        """
        raise NotImplementedError()
        
    def get_all_shows(self):
        """Should get all shows from the database.
        
        Returns:
            A list of dictionaries describing shows from the scraper.
            
            A database show should be a dictionary with the following structure, based on the schema defined in ``add_show``.
        
                * ``id``:               database id (int)
                * ``aid``:              scraper id (int)
                * ``beid``:             backend id (int)
                * ``type``:             type of show, such as 'tv', 'ova', or 'movie'. (str)
                * ``title``:            the official show title from the scraper (str)
                * ``alt_title``:        the shows alternate title, such as an english
                                        translated title. (str)
                * ``synonyms``:         A pipe-separated (|) list of synonyms for the show (str)
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
        raise NotImplementedError()
        
    def get_show(self, id=None, aid=None, beid=None):
        """Should get a single show from the database.
        
        Should get a given single show from the database. Only one of the three arguments is required, 
        and they should be handled in order: id, aid, beid.
        
        Keyword Args:
            id (int): The database ID for the show
            aid (int): The scraper ID for the show
            beid (int): The backend ID for the show

        Returns:
            A database show dictionary with the following structure if it exists, None otherwise.
        
                * ``id``:               database id (int)
                * ``aid``:              scraper id (int)
                * ``beid``:             backend id (int)
                * ``type``:             type of show, such as 'tv', 'ova', or 'movie'. (str)
                * ``title``:            the official show title from the scraper (str)
                * ``alt_title``:        the shows alternate title, such as an english
                                        translated title. (str)
                * ``synonyms``:         A pipe-separated (|) list of synonyms for the show (str)
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
        raise NotImplementedError()
        
    def remove_show(self, id=None, aid=None, beid=None):
        """Show deleter.
        
        Removes a given show from the database. Only one of the three arguments is required, 
        and they should be handled in order: id, aid, beid.
        
        Keyword Args:
            id (int): The database ID for the show.
            aid (int): The scraper ID for the show.
            beid (int): The backend ID for the show.
        """
        raise NotImplementedError()
        
    def search_show(self, term):
        """Show full-text search.
        
        When this method is called, a full-text search is expected to be performed against
        the database. If a full-test search can not be performed with your database of choice,
        try returning ``None`` for this function.
        
        Args:
            term (str): The term to search for in the database.      
        Returns:
            A list of dictionaries describing shows from the scraper.
            
            A database show is a dictionary with the following structure.
        
                * ``id``:               database id (int)
                * ``aid``:              scraper id (int)
                * ``beid``:             backend id (int)
                * ``type``:             type of show, such as 'tv', 'ova', or 'movie'. (str)
                * ``title``:            the official show title from the scraper (str)
                * ``alt_title``:        the shows alternate title, such as an english
                                        translated title. (str)
                * ``synonyms``:         A pipe-separated (|) list of synonyms of the show (str)
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
        raise NotImplementedError()
        
class BackEnd(AniPlugin):
    """Base backend class.
    
    Extend this class if you are making a Back End plugin.
    
    Backends are what actually perform the download operations, and keep track of everything
    that is currently being watched. They can also be configured to perform other opeations,
    such as adding things to a watch list or similar.
    
    Examples of backends include sonarr and couchpotato.
    
    Note:
        Check the AniPlugin Class documentation for details on what must
        be included with all plugins. This documentation only describes what
        is needed with search engine plugins.
    """
    @property
    def url(self) -> str:
        """str: Should return the URL of your search engine."""
        return None
    
    @property
    def api_key(self) -> Optional[str]:
        """str: Should return the the API key of your backend, if it needs one."""
        return None
        
    @property
    def username(self) -> Optional[str]:
        """str: Should return the username used to log into your backend if there is no api key."""
        return None
        
    @property
    def password(self) -> Optional[str]:
        """str: Should return the password used to log into your backend if there is no api key."""
        return None
        
    def check_auth(self, username, password):
        """Authentication check function.
        
        Should check if a user gives a correct username and password. These should be checked against
        the backend login database somehow, a new username and password pair should not be necessary to
        log into aniping.
     
        Args:
            username (str): The username to check.
            password (str): The password to check.
     
        Returns:
            bool.
            
                * True -- user is authenticated
                * False -- user is not authenticated or an error occurred
                
        """
        raise NotImplementedError()
        
    def check_for_login(self):
        """Checks if a login is necessary.
        
        Not all backends require logins all the time, so this function
        should check to see if one is necessary.
     
        Returns:
            bool.
            
                * True -- Login is required.
                * False -- Login is not required, proceed assuming already logged in.
                
        """
        raise NotImplementedError()
        
    def search(self, title):
        """Searches the backend for a particular show.
        
        This should search whatever indexes the backend has configured. It should
        return shows that may not yet be added to the backend. If the backend isn't
        capable of this, try calling ``search.query(title)`` and parsing the results
        there.
        
        Args:
            title (str): The title of the show we're searching for.
        
        Returns:
            list. A list of dictionaries describing the show. The response format should contain
            
                * ``title`` - the show's title (str)
                * ``overview`` - an overview of the show (str)
                * ``tvdbId`` - the TVDB ID of the show (int)
                * ``remotePoser`` - a URL to an image of the show's poster (str)
                * ``year`` - The year the show is airing (int)  
                * ``network`` - The network the show is airing on (str)
                * ``beid`` - an ID this show can be used to refer to in the backend, usually the TVDB ID (int)
                * ``images`` - A list of dictionaries describing images for the show, each in the following format: {"coverType": "fanart, banner, or poster", "url": "image URL"} (list)
        """
        raise NotImplementedError()
        
    def get_show(self, beid):
        """Get a show from the backend.
        
        Uses a backend id - typically something like the TVDB ID but can be whatever - to
        get a show from the backend.
        
        Args:
            id (int): The backend ID for the show.
            
        Returns:
            dict. A dictionary describing the show. The response format should contain
                        
                * ``title`` - the show's title (str)
                * ``overview`` - an overview of the show (str)
                * ``tvdbId`` - the TVDB ID of the show (int)
                * ``remotePoser`` - a URL to an image of the show's poster (str)
                * ``year`` - The year the show is airing (int)  
                * ``network`` - The network the show is airing on (str)
                * ``beid`` - an ID this show can be used to refer to in the backend, usually the TVDB ID (int)
                * ``images`` - A list of dictionaries describing images for the show, each in the following format: {"coverType": "fanart, banner, or poster", "url": "image URL"} (list)
        """
        raise NotImplementedError()
    
    def get_watching_shows(self):
        """Get all of the shows being tracked by the backend for downloading or watching.
        
        Returns:
            list. A list of dictionaries describing the show. The response format should contain
            
                * ``title`` - the show's title (str)
                * ``overview`` - an overview of the show (str)
                * ``tvdbId`` - the TVDB ID of the show (int)
                * ``remotePoser`` - a URL to an image of the show's poster (str)
                * ``year`` - The year the show is airing (int)  
                * ``network`` - The network the show is airing on (str)
                * ``beid`` - an ID this show can be used to refer to in the backend, usually the TVDB ID (int)
        """
        raise NotImplementedError()
        
    def add_update_show(self, beid, subgroup):
        """Adds or edits a show in the backend.
        
        As all aniping ever really deals with in the backend is the subgroup, that is all
        that should be expected in this method. Additionally, this method should be capable of
        both adding and editing a show.
        
        Args:
            beid (int): The backend ID of the show we're adding or editing.
            subgroup (str): The subgroup or release group we're using for this show.
        """
        raise NotImplementedError()
        
    def remove_show(self, beid):
        """Remove a given show from the backend.
        
        This should only delete files if the end user wants it to.
        
        Args:
            beid (int): The Backend ID of the show.
        """
        raise NotImplementedError()
        
    def subgroup_selected(self, beid):
        """Returns the selected subgroup for the show.
        
        The backend is the only place this information should be stored.
        
        Args:
            beid (int): The backend id of the show to get the subgroup for.
            
        Returns:
            A string of the subgroup the show is using. None if none is found.
        """
        raise NotImplementedError()
        
    def fanart(self, beid):
        """Returns fanart from the backend.
        
        If this backend does not support fanart, try calling to another service to collect it.
        Returning an empty list is acceptable as well.
        
        Args:
            beid (int): The backend ID for the show to get fanart from.
            
        Returns:
            list. All fanart urls in the results.
        """
        raise NotImplementedError()