import os,sys,sqlite3,time,logging

log = logging.getLogger(__name__)


# DB access functions
def opendb(dbfile="db/aniping.sqlite"):
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
    log.debug("Committing changes to database and closing DB.")
    conn.commit()
    conn.close()

def createdb(conn, schema="schema.ddl"):
    log.debug("Opening schema file {0} and executing script.".format(schema))
    with open(schema, 'rt') as f:
        schema = f.read()
    conn.executescript(schema)
    conn.commit()


# login_id Functions
def add_login_id(cid, expiry):
    conn = opendb()
    conn.execute('''
        insert into cookies (cookie_id, expiration)
        values (?,?)''', (cid, expiry)
    )
    closedb(conn)

def get_login_id(cid):
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
    conn = opendb()
    conn.execute('''delete from cookies where cookie_id=?''', (cid,))
    closedb(conn)


# Show Table Functions
def get_all_shows():
    """Gets all shows from the database.

    Returns:
        A list of dictionaries describing shows from the scraper.
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
    """Removes a show from the database.
    """
    # Must be a list of tuples to preserve order. Prefer DB ID over Scraper ID over Backend ID
    ids = [('id', id), ('aid', aid), ('beid', beid)]
    where_clause = [x for x in ids if x[1] is not None][0]
    
    conn = opendb()
    delete_string = "delete from airing_anime_list where {0}=?".format(where_clause[0])
    conn.execute(delete_string,(int(where_clause[1]),))
    closedb(conn)
    
def get_show(id=None, aid=None, beid=None):
    """Gets a given show from the database.

    Returns:
        A dict describing the show as defined in schema.ddl if it exists.
        None otherwise.
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
    """Adds a show to the database.

    Args:
        aid: The scrper ID of the show
        show_type: The type of show being added (tv, ona, ova, movie, etc.)
        title: The show's title
        alt_title: The show's alternate title. May be the same as the title.
        total_episodes: The show's total number of episodes
        next_episode: The next airing episode
        next_episode_date: The next airing episode's scheduled date
        start_date: The date the show starts or started.
        genre: A comma-separated list of genres for the show
        studio: The show's primary studio
        description: A brief description or synopsis for the show
        link: A link to more info - anilist, mal, etc.
        image: The locally cached link to the image for the show.
        airing: The airing status of the show.
        season_name: The season string of the show (winter, spring, summer, fall)
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
    """Changes a show in the database.
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
    """Searches the database for a particular term.
    """
    conn = opendb()
    c = conn.cursor()
    c.execute('''select * from airing_anime_list where id in 
                    (select id from show_search where search_data match ?);''', (term,))
    output = c.fetchall()
    output = [dict(x) for x in output]   
    closedb(conn)
    return output
