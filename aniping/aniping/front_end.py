#!/usr/bin/env python3
"""front_end

This submodule handles functions required by the front_end - app.py.
Most functions should be defined here and called by app.py. Because
app.py will only call to this particular submodule, it is acceptable
to include functions that do nothing but call back to a different
function in the module.
"""
import hashlib,time,requests,threading,logging,string
from pathlib import Path
from itertools import zip_longest
from aniping.plugins import AniPlugin, AniPluginManager
from urllib.parse import quote_plus
from datetime import datetime

_logger = logging.getLogger(__name__)

class FrontEnd(AniPlugin):
    """Front End plugin for Aniping.
    
    This is a "special" plugin this is called directly from the main server thread,
    and not handled by the plugin manager. This handles all front-end services the
    application may need, and calls back to other plugins as necessary.
    """
    def __init__(self, config, plugin_manager=None):
        """Aniping Front End Plugin Initializer.
        
        Intilizes the front end plugin. This will also get the instance of the AniPluginManager
        this instance of the server will use for the main thread.
        
        Note:
            This is a special plugin and should not be replaced with another plugin,
            unless all of the functions of this plugin are replicated correctly.
        
        Args:
            config (dict): The configuration dictionary loaded by Flask.
            plugin_manager (:obj:`AniPluginManager`): An aniplugin manager instantiation. Only added because the super init requires it. Should be None.
        """
        super().__init__(config, plugin_manager)
        self.__name__       = "Aniping Front End"
        self.__id__         = "front_end"
        self.__author__     = "Spencer Julian <hellothere@spencerjulian.com>"
        self.__version__    = "0.01"
        
        self.config = self._config
        self._name = "Aniping"
        self.apm = AniPluginManager(self.config)
        self.apm.scan_for_plugins()
        self.apm.load_plugins()
        
    def check_auth(self, username, password):
        """Authentication Check Function.
        
        Checks if a user gives a correct username and password.
        User and pass are checked back against our backend, we do not handle our own
        authentication.
     
        Args:
            username (str): The username to check.
            password (str): The password to check.
     
        Returns:
            bool.
            
                * True -- user is authenticated
                * False -- user is not authenticated or an error occurred
        """
        _logger.debug("Calling to backend check_auth function")
        return self.back_end("check_auth", username, password)
        
    def set_login_id(self):
        """Session id Creator
        
        Creates a session id and writes it to the database.
     
        Returns:
            str. The id of the session.
        """
        _logger.debug("Setting login token.")
        session_id = hashlib.sha256(str.encode(str(time.time()))).hexdigest()
        _logger.debug("Exipres in 2 hours")
        expiry = int(time.time()) + 7200 #All cookies expire in 2 hours
        _logger.debug("calling DB to add login token to database")
        self.db("add_login_id", session_id, expiry)
        _logger.debug("Session ID is {0}".format(session_id))
        return session_id

    def check_login_id(self, session_id):
        """Session ID Check Function.
        
        Gets a session id from the database and checks that it's valid.
        If no session id is passed or if it's invalid, check if the backend
        has logins enabled.
     
        Args:
            session_id (str): The session ID for the user.
     
        Returns:
            bool.
                
                * True -- Session id is valid *or* back end logins are disabled.
                * False -- Session id is not valid or has expired.
        """
        _logger.debug("Checking if session ID is in database")
        db_session_id = self.db("get_login_id", session_id)
        if db_session_id:
            _logger.debug("Session ID found. Checking if it's expired.")
            if db_session_id['expiration'] > int(time.time()):
                _logger.debug("Not expired, session valid.")
                return True
            _logger.debug("Session ID is expired, deleting ID.")
            self.db("delete_login_id", session_id)
        if not self.back_end("check_for_login"):
            _logger.debug("No login on backend, no session ID required.")
            return True
        _logger.debug("Could not find valid sesion ID.")
        return False

    def delete_login_id(self, session_id):
        """Session id Delete Function.
        
        Deletes a session id from the database. Used for logging out.
        Just calls back to db.delete_login_id.

        Args:
            session_id (str): The session ID for the user.

        """
        _logger.debug("Calling to db delete_log_id function.")
        self.db("delete_login_id", session_id)
        
    def star_show(self, dbid):
        """Show starring/highlighting function.
        
        Toggles a show starred status in the database.
        
        Args:
            dbid (int): The database ID of the show to star.
        """
        _logger.debug("Attepting to (un)star show with ID {0}".format(dbid))
        show = self.get_show_from_db(dbid)
        _logger.debug("Show to be (un)starred is {0}".format(show['title']))
        _logger.debug("Current starred value is {0}".format(show['starred']))
        show['starred'] = 1 if show['starred'] == 0 else 0
        _logger.debug("Toggled star value to {0}".format(show['starred']))
        _logger.debug("Writing change to database.")
        self.db("change_show", id=dbid, starred=show['starred'])
        
    def get_show_from_db(self, dbid):
        """Gets the show information out of the database.
        
        Just calls back to db.get_show.
        
        Args:
            dbid (int): the database ID for the show.
            
        Returns:
            dict. The show information for the ID passed.
        """
        _logger.debug("Calling to db get_show function.")
        return self.db("get_show", id=dbid)
        
    def search_show_from_backend(self, dbid):
        """Gets a show from the database and searches for it in the backend system.
        
        Args:
            dbid (int): the database ID for the show.
                        
        Returns:
            dict. The backend search results for the id passed. None if not found.
        """
        _logger.debug("Trying to search for show with db id {0}".format(dbid))
        show = self.get_show_from_db(dbid)
        _logger.debug("Show to search for is {0}".format(show['title']))
        _logger.debug("Calling backend search function.")
        output = self.back_end("search", quote_plus(show['title']))
        if not output:
            # Sometimes the normal title doesn't give us any results, because it might
            # be non-english or something. The alt-title should give us results in that
            # case.
            _logger.debug("Backend could not find show with title {0}, trying with title {1}".format(show['title'], show['alt_title']))
            output = self.back_end("search", quote_plus(show['alt_title']))
        if not output and show['synonyms']:
            # If we still don't have anything, then we'll try looping through synonyms
            # if we have any.
            _logger.debug("Backend could not find show with title {0}, but we have synonyms. Trying them.")
            for synonym in show['synonyms'].split("|"):
                _logger.debug("Trying synonym {0}".format(synonym))
                output = self.back_end("search", quote_plus(synonym))
                if output:
                    break
        if not output:
            # No synonyms, no titles. We'll try taking the normal title and removing numbers,
            # then taking the alt title and removing numbers. Then do the same for punctuation.
            # Still no luck? Then we give up.
            _logger.debug("Backend could not find show with title {0}, trying to strip digits.")
            output = self.back_end("search", quote_plus("".join([c for c in show['title'] if not c.isdigit()])))
        if not output:
            # Last shot - alt title no digits.
            _logger.debug("Backend could not find show with title {0}, trying to strip digits from alt title.")
            output = self.back_end("search", quote_plus("".join([c for c in show['alt_title'] if not c.isdigit()])))
        if not output:
            _logger.debug("Backend could not find any shows. Returning no output.")
            return None
        _logger.debug("Found {0} shows. Returning first result, which is {1}".format(len(output), output[0]['title']))
        return output[0]
        
    def get_show_from_backend(self, beid):
        """Gets a known show from the backend system from its id.
        
        Args:
            beid (int): the backend ID for the show.
            
        Returns:
            dict. The backend show information.
        """
        _logger.debug("Calling backend get_show function.")
        return self.back_end("get_show", beid)

    def get_subgroups(self, dbid):
        """Gets a list of sub groups from the search engine. 
        
        Generally this will be a torrent search site, like nyaa. Nothing is ever downloaded
        directly with aniping! The backend should handle that, if downloading
        is happening. This only gets a list of groups subtitling the show.
        
        Args:
            dbid (int): the database ID for the show.
        
        Returns:
            list. A list of subgroups.
        """
        _logger.debug("Trying to get subgroups for show with db id {0}".format(dbid))
        show = self.get_show_from_db(dbid)
        _logger.debug("Show is {0}".format(show['title']))
        subgroups = []
        results = []
        search_results = self.search("results", show['title'])
        search_results.extend(self.search("results", show['alt_title']))
        if show['synonyms']:
            for synonym in show['synonyms']:
                search_results.extend(self.search("results", synonym))
        search_results.extend(self.search("results", "".join([c for c in show['title'] if not c.isdigit()])))
        search_results.extend(self.search("results", "".join([c for c in show['alt_title'] if not c.isdigit()])))
        search_results.extend(self.search("results", "".join([c for c in show['title'] if c not in set(string.punctuation)])))
        search_results.extend(self.search("results", "".join([c for c in show['alt_title'] if c not in set(string.punctuation)])))
        _logger.debug("Found {0} results.".format(len(search_results)))
        for item in search_results:
            print(item)
            subgroups.extend(item[0])
            results.extend(item[1])
        subgroups = list(set(subgroups))
        _logger.debug("Ended with {0} subgroups.".format(len(subgroups)))
        return subgroups
        
                
    def get_selected_group(self, beid):
        """Gets the selected subgroup for the show from the backend.
        
        Just calls back to back_end.subgroup_selected.
        
        Args:
            beid (int): the backend ID for the show.
            
        Returns:
            str. The subgroup selected for the series.
        """
        _logger.debug("Calling to backend subgroup_selected function.")
        return self.back_end("subgroup_selected", beid)
        
    def get_fanart(self, beid):
        """Gets some fanart for the show from the backend.
        
        Calls back to back_end.fanart, but because that should be a list,
        just get the first item from that list.
        
        Args:
            beid (int): the backend ID for the show.
            
        Returns:
            str. A link to some fanart.
        """
        _logger.debug("Getting first result from backend fanart function.")
        fanart = self.back_end("fanart", beid)
        if len(fanart) > 0:
            return fanart[0]
        else:
            return None
        
    def add_update_show(self, dbid, beid, subgroup):
        """Adds a given show to the backend, or edits it if its already there.
        
        Calls db.change_show to update the database with the backend id.
        
        Args:
            dbid (int): The database ID for the show.
            beid (int): The backend ID for the show.
            subgroup (str): The selected subgroup for the show, from our search engine.
        """
        _logger.debug("Calling backend add_update_show function.")
        self.back_end("add_update_show", beid, subgroup)
        _logger.debug("Calling db change_show function.")
        self.db("change_show", id=dbid, beid=beid)

    def remove_show(self, dbid):
        """Removes a show from the backend given it's database ID
        
        Args:
            dbid (int): The database ID for the show.
        """
        _logger.debug("Attempting to remove show with dbid {0}".format(dbid))
        beid = self.db("get_show", id=dbid)['beid']
        _logger.debug("Show's backend id is {0}".format(beid))
        self.back_end("remove_show", beid)
     
    def get_shows_for_display(self, term=None):
        """Gets shows from the scraper and preps them for display. 
        
        If a term is provided, only get shows that include that term.
              
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
            _logger.debug("No term provided, sending default.")
            watching, airing, specials, movies = self.output_display_lists(*[item for sublist in self.scraper("get_shows_by_category") for item in sublist])
            _logger.debug("Got the following lists:")
            _logger.debug("WATCHING\n====================\n{0}".format(watching))
            _logger.debug("AIRING\n====================\n{0}".format(airing))
            _logger.debug("SPECIALS\n====================\n{0}".format(specials))
            _logger.debug("MOVIES\n====================\n{0}".format(movies))
            return watching, airing, specials, movies
        _logger.debug("Term provided, attempting to search for term {0}".format(term))
        watching, airing, specials, movies = self.output_display_lists(*[item for sublist in self.scraper("get_shows_by_category", search_results=self.db("search_show", term)) for item in sublist])
        _logger.debug("Got the following lists:")
        _logger.debug("WATCHING\n====================\n{0}".format(watching))
        _logger.debug("AIRING\n====================\n{0}".format(airing))
        _logger.debug("SPECIALS\n====================\n{0}".format(specials))
        _logger.debug("MOVIES\n====================\n{0}".format(movies))
        return watching, airing, specials, movies

    def do_first_time_setup(self):
        """Begins first time setup for aniping. Starts a new thread to scrape shows.
        
        Returns:
            bool. Always returns true.
        """
        _logger.debug(">>>>>>Starting First Time Setup Thread<<<<<<")
        ftst = threading.Thread(target=self.scrape_shows)
        ftst.start()
        _logger.debug(">>>>>>Separate Thread Started<<<<<<")
        return True

    def output_display_lists(self, watching, airing, specials, movies):
        """Takes the display lists and massages them for output.

        It does this by removing watching shows from the other lists,
        handling date formats, and similar tasks.
        
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
        _logger.debug("Removing watching shows from airing,specials,and movies lists")
        airing = [x for x in airing if x not in watching]
        specials = [x for x in specials if x not in watching]
        movies = [x for x in movies if x not in watching]
        
        for listed in (watching,airing,specials,movies):
            for item in listed:
                try:
                    _logger.debug("Attempting to set date on show {0} with ID {1}".format(item['title'], item['id']))
                    item['next_episode_date'] = datetime.strptime(item['next_episode_date'], '%Y-%m-%dT%H:%M:%S+09:00').strftime('%B %d, %Y')
                except (ValueError, TypeError):
                    if item['next_episode_date'] == None or item['next_episode_date'] == "":
                        _logger.debug("Could not set date, so setting to \"unknown\"")
                        item['next_episode_date'] = "unknown"
                    else:
                        try:
                            _logger.debug("The format did not work, so trying a different format.")
                            item['next_episode_date'] = datetime.strptime(item['next_episode_date'], '%b %d, %Y').strftime('%B %d, %Y')
                        except (ValueError, TypeError):
                            _logger.debug("Failed, leaving next_episode_date as is.")
                            item['next_episode_date'] = item['next_episode_date']
        
        _logger.debug("Returning lists with {0} items in watching, {1} in airing, {2} in specials, and {3} in movies.".format(len(watching), len(airing), len(specials), len(movies)))
        return watching, airing, specials, movies
        
    def scrape_shows(self):
        """Calls to the scraper to scrape shows and add them to the database. 
        
        Creates a lockfile in /tmp to ensure multiple scraping threads don't run
        simultaneously.
                
        Returns:
            bool.
                
                * True -- Scrape is complete.
                * False -- Scrape lock file exists.
        """
        p = Path('/tmp/.aniping-setup')
        if p.is_file():
            _logger.debug("Scrape lock file exists, exiting.")
            return False
        else:
            _logger.debug("Scrape lock file does not exist, creating.")
            p.write_text("running")
        _logger.debug("Beginning show scraper.")
        local_apm = AniPluginManager(self.config)
        local_apm.scan_for_plugins()
        local_apm.load_plugins()
        local_apm.plugin_category_function("scraper", "scrape_shows")
        _logger.debug("Show scraper complete, removing lock file.")
        p.unlink()
        _logger.debug("scraper done.")
        return True
