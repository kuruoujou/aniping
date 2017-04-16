#!/usr/bin/env python3
import os,sys,sqlite3,time,logging
from aniping.plugins import DataBase

log = logging.getLogger(__name__)

class Sqlite(DataBase):
    """Sqlite database plugin.
    
    This plugin implements the sqlite database for aniping.
    """
    def __init__(self, config, plugin_manager):
        """Initilizes the sqlite database plugin.
        
        Args:
            config (dict): The configuration dictionary as read by flask.
            plugin_manager (:obj:`AniPluginManager): An instance of the AniPluginManager.
        """
        super().__init__(config, plugin_manager)
        self.__name__       = "Sqlite"
        self.__id__         = "sqlite"
        self.__author__     = "Spencer Julian <hellothere@spencerjulian.com>"
        self.__version__    = "0.01"
        
        self.config = self._config['SQLITE']
        self._name = self.config['NAME'] if 'NAME' in self.config else 'Sqlite'
        self._db_file = self.config['FILE']
        self._schema_file = self.config['SCHEMA']
        
        self._conn = None
        self._schema = None
        
    @property
    def name(self):
        """str: Returns the name of this plugin."""
        return self._name
        
    @property
    def db_loc(self):
        """str: Returns the sqlite file we use."""
        return self._db_file
        
    @property
    def db_schema(self):
        """str: Returns the contents of the schema file."""
        return self._schema

    def _read(func):
        """Read decorator function.
        
        Wraps read-only database queries to make sure we have an open connection.
        
        Returns:
            The response of the function that is decorated.
        """
        def wrapper(self, *args, **kwargs):
            if not self._conn:
                self._open_database()
            return func(self, *args, **kwargs)
        return wrapper
        
    def _write(func):
        """Write decorator function.
        
        Wraps read-write database queries to make sure we have an open connection,
        and to make sure the results are committed back to the database.
        
        Returns:
            The response of the function that is decorated.
        """
        def wrapper(self, *args, **kwargs):
            if not self._conn:
                self._open_database()
            output = func(self, *args, **kwargs)
            self._commit_changes()
            return output
        return wrapper
        
    def _open_database(self):
        """Opens a connection to the databse."""
        log.debug("Opening sqlite database {0}".format(self._db_file))
        self._conn = sqlite3.connect(self._db_file)
        try:
            log.debug("Checking if database is populated.")
            self._conn.execute("select * from airing_anime_list limit 1");
            self._conn.row_factory = sqlite3.Row
        except sqlite3.OperationalError:
            log.debug("Database needs populated.")
            self._conn.row_factory = sqlite3.Row
            self._populate_database()

        log.debug("database connection established.")

    def _commit_changes(self):
        """Commits changes to the database."""
        log.debug("Committing changes to database.")
        self._conn.commit()
        
    def _populate_database(self):
        """Database populator.
        
        If the database is brand new, this creates the tables
        necessary using schema file.
        """
        log.debug("Opening schema file {0} and executing script.".format(self._schema_file))
        with open(self._schema_file, 'rt') as f:
            self._schema = f.read()
        self._conn.executescript(self._schema)
        self._commit_changes()


    @_write
    def add_login_id(self, session_id, expiry):
        """Writes a session ID for a user to the database.
        
        Args:
            session_id (int): the session ID to add to the database.
            expiry (int): The expiration date and time of the session id
                          as a unix timestamp.
        """
        self._conn.execute('''
            insert into cookies (cookie_id, expiration)
            values (?,?)''', (session_id, expiry)
        )

    @_read
    def get_login_id(self, session_id):
        """Gets a session id from the database if it hasn't expired. Deletes it if it has.
        
        Args:
            session_id (int): The session id to lookup in the database.
        """
        for row in self._conn.execute('''select * from cookies'''):
            if int(time.time()) > row['expiration']:
                self.delete_login_id(row['id'])
            elif row['cookie_id'] == session_id:
                return row
        return None

    @_write
    def delete_login_id(self, session_id):
        """Deletes a session id from the database.
        
        Args:
            session_id (int): The session id to delete.
        """
        self._conn.execute('''delete from cookies where cookie_id=?''', (session_id,))


    @_read
    def get_all_shows(self):
        """Gets a list of all shows from the database.

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
        log.debug("Attempting to get all shows.")
        log.debug("Executing select statement.")
        cur = self._conn.execute('''select * from airing_anime_list''')
        output = [dict(x) for x in cur.fetchall()]
        log.debug("Returning output.")
        log.debug("OUTPUT\n===================\n{0}".format(output))
        return output

    @_write
    def remove_show(self, id=None, aid=None, beid=None):
        """Removes a given show from the database. 
        
        Only one of the three arguments is required, 
        and they are handled in order: id, aid, beid.
        
        Keyword Args:
            id (int): The database ID for the show.
            aid (int): The scraper ID for the show.
            beid (int): The backend ID for the show.
        """
        # Must be a list of tuples to preserve order. Prefer DB ID over Scraper ID over Backend ID
        ids = [('id', id), ('aid', aid), ('beid', beid)]
        where_clause = [x for x in ids if x[1] is not None][0]
        
        delete_string = "delete from airing_anime_list where {0}=?".format(where_clause[0])
        self._conn.execute(delete_string,(int(where_clause[1]),))
     
    @_read     
    def get_show(self, id=None, aid=None, beid=None):
        """Gets a given single show from the database. 
        
        Only one of the three arguments is required, 
        and they are handled in order: id, aid, beid.
        
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
        # Must be a list of tuples to preserve order. Prefer DB ID over Scraper ID over Backend ID
        ids = [('id', id), ('aid', aid), ('beid', beid)]
        where_clause = [x for x in ids if x[1] is not None][0]
        select_string = "select * from airing_anime_list where {0}=?".format(where_clause[0])
        cur = self._conn.execute(select_string,(int(where_clause[1]),))
        output = cur.fetchone()
        output = dict(output) if output is not None else None
        return output

    @_write
    def add_show(self, aid, show_type, title, alt_title, synonyms, total_episodes, next_episode,
            next_episode_date, start_date, genre, studio, description, link, image,
            airing, season_name):
        """Adds a show to the database. 
        
        All arguments are required. Most can be grabbed from the scraper with minimal munging.

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
        self._conn.execute('''
        insert into airing_anime_list
        (aid, type, title, alt_title, total_episodes, next_episode, next_episode_date,
        start_date, genre, studio, description, link, image, airing, season_name,
        starred) values
        (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,0);''', 
        (aid, show_type, title, alt_title, total_episodes, next_episode, next_episode_date,
        start_date, genre, studio, description, link, image, airing, season_name))

    @_write
    def change_show(self, id=None, aid=None, beid=None, show_type=None, title=None, alt_title=None, 
            synonyms=None, total_episodes=None, next_episode=None, next_episode_date=None, start_date=None, 
            genre=None, studio=None, description=None, link=None, image=None, airing=None, 
            season_name=None, starred=None):
        """Modifies a show in the database. 
        
        One of id, aid, or beid is required.
        All other arguments are optional. If multiple of id, aid, and beid
        are provided, they are handled in the order id, aid, beid, and anything
        following the first match is considered an update for the database.
        
        Example:
            If you want to change the title for a show and have it's beid::
            
                db.change_show(beid=12345, title="My SHow")
                
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
        if not id and not aid and not beid:
            raise
     
        # Must be a list of tuples to preserve order. Prefer DB ID over Scraper ID over Backend ID
        ids = [('id', id), ('aid', aid), ('beid', beid)]
        where_clause = [x for x in ids if x[1] is not None][0]
        
        # Also need to preserve order here, because we want to use the 'safe' method of sqlite input
        values = [
            ("type", show_type),
            ("title", title),
            ("alt_title", alt_title),
            ("total_episodes", total_episodes),
            ("next_episode", next_episode),
            ("next_episode_date", next_episode_date),
            ("start_date", start_date),
            ("genre", genre),
            ("studio", studio),
            ("description", description),
            ("link", link),
            ("image", image),
            ("airing", airing),
            ("season_name", season_name),
            ("starred", starred)
            ]
        for item in ids:
            if item[0] != where_clause[0]:
                values.append(item)
        
        change_vals = [x for x in values if x[1] is not None]
        
        update_string = "update airing_anime_list set {0}=?".format(change_vals[0][0])
        substitute_items = [change_vals[0][1]]
        for item in change_vals[1:]:
            update_string = "{0}, {1}=?".format(update_string, item[0])
            substitute_items.append(item[1])
        update_string = "{0} where {1}=?".format(update_string, where_clause[0])
        substitute_items.append(int(where_clause[1]))
        self._conn.execute(update_string, tuple(substitute_items))

    @_read
    def search_show(self, term):
        """Searches the database for a particular term. 
        
        The sqlite3 database is configured to support full text search.
        
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
        cur = self._conn.execute('''select * from airing_anime_list where id in 
                        (select id from show_search where search_data match ?);''', (term,))
        output = cur.fetchall()
        output = [dict(x) for x in output]
        return output
