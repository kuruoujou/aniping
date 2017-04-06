#!/usr/bin/env python3
"""db

This submodule handles sqlite3 database access functions
for aniping. Actual read/write logic is handled here instead
of in the modules themselves to keep the functionality of the
other submodules more legible, and to simplify replacing this
with a different backend if needed.

This is a terminal submodule for the aniping package, and so should
not import any additional aniping submodules.
"""
import os,sys,sqlite3,time,logging

log = logging.getLogger(__name__)

def opendb(dbfile="db/aniping.sqlite"):
    """Database connection opener.
    
    Opens a connection to the databse.
    
    Keyword Args:
        dbfile (str): the sqlite3 database file.
        
    Returns:
        sqlite3 connection instance.
    """
    log.debug("Opening sqlite database {0}".format(dbfile))
    conn = sqlite3.connect(dbfile)
    c = conn.cursor()
    try:
        log.debug("Checking if database is populated.")
        c.execute("select * from airing_anime_list limit 1");
        conn.row_factory = sqlite3.Row
    except sqlite3.OperationalError:
        log.debug("Database needs populated.")
        conn.row_factory = sqlite3.Row
        createdb(conn)

    log.debug("database connection established.")
    return conn

def closedb(conn):
    """Database connection closer.
    
    Closes a connection to the database. Commits any changes first.
    
    Args:
        conn (sqlite3 connection instance): The connection to close.
    """
    log.debug("Committing changes to database and closing DB.")
    conn.commit()
    conn.close()

def createdb(conn, schema="schema.ddl"):
    """Database populator.
    
    If the database is brand new, this creates the tables
    necessary using schema file.
    
    Args:
        conn (sqlite3 connection instance): A database connection.
        schema (str): The schema file to execute on the database.
    """
    log.debug("Opening schema file {0} and executing script.".format(schema))
    with open(schema, 'rt') as f:
        schema = f.read()
    conn.executescript(schema)
    conn.commit()


# login_id Functions
def add_login_id(cid, expiry):
    """Session id setter.
    
    Writes a session ID for a user to the database.
    
    Args:
        cid (int): the session ID to add to the database.
        expiry (int): The expiration date and time of the session id
                      as a unix timestamp.
    """
    conn = opendb()
    conn.execute('''
        insert into cookies (cookie_id, expiration)
        values (?,?)''', (cid, expiry)
    )
    closedb(conn)

def get_login_id(cid):
    """Session id getter.
    
    Gets a session id from the database if it hasn't expired.
    Delets it if it has.
    
    Args:
        cid (int): The session id to lookup in the database.
    """
    conn = opendb()
    c = conn.cursor()
    output = None
    for row in c.execute('''select * from cookies'''):
        if int(time.time()) > row['expiration']:
            conn.execute('''delete from cookies where id=?''', (row['id'],))
        elif row['cookie_id'] == cid:
            output = row
    closedb(conn)
    return output

def delete_login_id(cid):
    """Session id deleter.
    
    Deletes a session id from the database.
    
    Args:
        cid (int): The session id to delete.
    """
    conn = opendb()
    conn.execute('''delete from cookies where cookie_id=?''', (cid,))
    closedb(conn)


# Show Table Functions
def get_all_shows():
    """Show list getter.
    
    Gets a list of all shows from the database.

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
    conn = opendb()
    c = conn.cursor()
    log.debug("Executing select statement.")
    c.execute('''select * from airing_anime_list''')
    output = c.fetchall()
    output = [dict(x) for x in output]
    closedb(conn)
    log.debug("Returning output.")
    log.debug("OUTPUT\n===================\n{0}".format(output))
    return output

def remove_show(id=None, aid=None, beid=None):
    """Show deleter.
    
    Removes a given show from the database. Only one of the
    three arguments is required, and they are handled in order:
    id, aid, beid.
    
    Keyword Args:
        id (int): The database ID for the show.
        aid (int): The scraper ID for the show.
        beid (int): The backend ID for the show.
    """
    # Must be a list of tuples to preserve order. Prefer DB ID over Scraper ID over Backend ID
    ids = [('id', id), ('aid', aid), ('beid', beid)]
    where_clause = [x for x in ids if x[1] is not None][0]
    
    conn = opendb()
    delete_string = "delete from airing_anime_list where {0}=?".format(where_clause[0])
    conn.execute(delete_string,(int(where_clause[1]),))
    closedb(conn)
    
def get_show(id=None, aid=None, beid=None):
    """Show getter
    
    Gets a given single show from the database. Only one
    of the three arguments is required, and they are handled in
    order: id, aid, beid.
    
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
    conn = opendb()
    c = conn.cursor()
    c.execute(select_string,(int(where_clause[1]),))
    output = c.fetchone()
    output = dict(output) if output is not None else None
    closedb(conn)
    return output

def add_show(aid, show_type, title, alt_title, total_episodes, next_episode,
        next_episode_date, start_date, genre, studio, description, link, image,
        airing, season_name):
    """Show adder.
    
    Adds a show to the database. All arguments are required.
    Most can be grabbed from the scraper with minimal munging.

    Args:
        aid (int): The scraper ID of the show
        show_type (str): The type of show being added (tv, ona, ova, movie, etc.)
        title (str): The show's title
        alt_title (str): The show's alternate title. May be the same as the title.
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
    conn = opendb()
    conn.execute('''
    insert into airing_anime_list
    (aid, type, title, alt_title, total_episodes, next_episode, next_episode_date,
    start_date, genre, studio, description, link, image, airing, season_name,
    starred) values
    (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,0);''', 
    (aid, show_type, title, alt_title, total_episodes, next_episode, next_episode_date,
    start_date, genre, studio, description, link, image, airing, season_name))
    closedb(conn)

def change_show(id=None, aid=None, beid=None, show_type=None, title=None, alt_title=None, 
        total_episodes=None, next_episode=None, next_episode_date=None, start_date=None, 
        genre=None, studio=None, description=None, link=None, image=None, airing=None, 
        season_name=None, starred=None):
    """Show editer.
    
    Modifies a show in the database. One of id, aid, or beid is required.
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
    
    conn = opendb()
    conn.execute(update_string, tuple(substitute_items))
    closedb(conn)

def search_show(term):
    """Show search.
    
    Searches the database for a particular term. The sqlite3 database
    is configured to support full text search.
    
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
    conn = opendb()
    c = conn.cursor()
    c.execute('''select * from airing_anime_list where id in 
                    (select id from show_search where search_data match ?);''', (term,))
    output = c.fetchall()
    output = [dict(x) for x in output]   
    closedb(conn)
    return output
