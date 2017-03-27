#!/usr/bin/env python3
"""Aniping.

This is the main entrypoint for the application. For full documentation on what
aniping is, please check README.rst.

All processing in the aniping package should start through the front_end submodule,
which will itself call the requisite modules. The exception is config loading,
which should be done when the server loads for the first time.

When the wsgi app is built, an apscheduler instance is attached to it to schedule
a weekly job to scrape shows from our sources.
"""
from flask import render_template, session, request, make_response, escape, jsonify, abort, redirect
from urllib.parse import unquote_plus
from aniping import front_end, config
from flask_apscheduler import APScheduler
import os, time, sys, datetime, atexit, logging

app = application = config.Flask(__name__, template_folder='views', static_folder='static')
"""Flask: WSGI Application entry point"""

app.config.from_yaml(os.environ.get('ANIPING_CONFIG', os.path.join(app.root_path, 'config/config.yml')))

if app.config["DEBUG"]:
    logging.basicConfig(level=logging.DEBUG)
    logging.debug("Debug mode active.")
else:
    logging.basicConfig(level=logging.INFO)
    
log = logging.getLogger(__name__)
"""logger: Logging endpoint"""
        
app.config["JOBS"] = [ {
    'id': 'scrape_job',
    'name': "Scrape shows from source",
    'trigger': 'interval',
    'days': 7,
    'func': 'aniping.front_end:scrape_shows',
    'args': [app.config]
} ]

app.config["SCHEDULER_API_ENABLED"] = True

scheduler = APScheduler()
"""APScheduler(): APScheduler instance to schedule occasional tasks"""
scheduler.init_app(app)
scheduler.start()

@app.route('/search')
@app.route('/')
def index():
    """Primary index function.

    This function handles searching and the main page. If ``q`` is passed in a query
    string, e.g. ``http://localhost?q=gabriel+dropout``, then a search will be performed.

    If request path is ``search``, e.g. ``http://localhost/search``, then the navigation
    menu will not be rendered.

    Should there be no shows returned from the backend, ``front_end.do_first_time_setup``
    will be called to scrape shows from the source.

    Returns:
        A rendered template, either ``first_time.html`` for the first run or ``default.html`` otherwise.
    """
    log.debug("Entering index, attempting to get shows.")
    watching, airing, specials, movies = front_end.get_shows_for_display(app.config, request.args.get('q',None))
    standalone = True if request.path.strip('/') == 'search' else False
    logged_in = front_end.check_login_id(escape(session['logged_in']), app.config) if 'logged_in' in session else False
    if not watching and not airing and not specials and not movies:
        log.debug("No shows found in any category. Starting first time startup.")
        front_end.do_first_time_setup(app.config)
        return render_template('first_time.html', logged_in=logged_in)
    return render_template('default.html', watching=watching, airing=airing, specials=specials, movies=movies, standalone=standalone, logged_in=logged_in)

@app.route('/login', methods=['POST'])
def login():
    """Login POST handler.

    Only runs when ``/login`` is hit with a POST method. There is no GET method
    equivilent, as it is handled by the navigation template. Sets the status
    code to ``401`` on login failure.

    Returns:
        JSON formatted output describing success or failure.
    """
    log.debug("Entering login, attempting to authenticate user.")
    username = request.form['signin_username']
    password = request.form['signin_password']
    log.debug("Username: {0}".format(username))
    if front_end.check_auth(username, password, app.config):
        log.debug("User authenticated. Trying to set session.")
        cid = front_end.set_login_id()
        session['logged_in'] = cid
        log.debug("Session ID: {0}, returning to user".format(cid))
        return jsonify({ "login": "success" })
    log.debug("Username or password not recognized, sending 401.")
    response.status = 401
    return jsonify({ "login": "failed" })

@app.route('/logout')
def logout():
    """Logout handler.

    Ends the client session and deletes the session ID from the database.

    Returns:
        JSON formatted output describing success.
    """
    log.debug("Entering logout, attempting to end session.")
    front_end.delete_login_id(escape(session['logged_in']))
    session.pop('logged_in', None)
    log.debug("Returning to user.")
    return jsonify({ "logout": "success" })

@app.route('/star')
def star():
    """Starring/Highlighting handler.

    Attempts to toggle a star/highlight on a particular show. The show ID must
    be passed in the ``id`` query string. If the user is unauthenticated, the
    function is aborted with a ``404`` message to hide the page.

    Returns:
        JSON formatted output describing success and the ID of the show starred.
    """
    log.debug("Entering star, trying to toggle star.")
    if front_end.check_login_id(escape(session['logged_in']), app.config):
        log.debug("Sending show ID {0} to function".format(request.args['id']))
        front_end.star_show(request.args['id'])
        log.debug("Returning to user.")
        return jsonify({ "star": "success", "id": request.args['id'] })
    log.debug("User cannot be authenticated, send 404 to hide page.")
    abort(404)
    
@app.route('/rm')
def drop_show():
    """Show removal handler.

    Attempts to remove a show from the backend system. The show ID must
    be passed in the ``id`` query string. If the user if unauthenticated, the
    function is aborted with a ``404`` message to hide the page.

    Returns:
        An HTTP redirect to the home page, to refresh.
    """
    log.debug("Entering drop_show, trying to remove show from list.")
    if front_end.check_login_id(escape(session['logged_in']), app.config):
       log.debug("Sending show ID {0} to function".format(request.args['id']))
       front_end.remove_show(request.args['id'], app.config)
       log.debug("Refreshing user's page.")
       return redirect('/')
    log.debug("User cannot be authenticated, send 404 to hide page.")
    abort(404)

@app.route('/edit', methods=['GET', 'POST'])
@app.route('/add', methods=['GET', 'POST'])
def update_show():
    """Show add and edit handler.

    Either displays a template allowing the user to edit or add a show, or attempts
    to edit or add the show, depending on if the method is GET or POST. The function
    is aborted with a ``404`` message to hide the page if the user is not authenticated.

    GET method:
        Requires ``id`` to be passed as the ID of the show in a query string. If
        the show can't be found, abort with a ``404`` message. Otherwise, lookup
        the show in the db, as well as sub groups subtitling the show and the selected
        sub group if there is one, and some fanart to render on the background.
    
    POST method:
        Requires ``id``, ``beid``, and ``subgroup`` to be passed as form parameters.
        ``id`` is the DB id of the show, ``beid`` is the backend ID of the show, and
        ``subgroup`` is the subgroup the user has selected. This will attempt to add
        the show to the backend.

    Returns:
        A rendered template with a form on the GET method.
        A redirect to the home as a refresh on the POST method.
    """
    log.debug("Entering update_show, trying to {0} show".format(request.path.strip('/')))
    logged_in = front_end.check_login_id(escape(session['logged_in']), app.config)
    if logged_in and request.method == 'POST':
       log.debug("Request method is POST, so sending results to function.")
       subgroup = request.form['subgroup']
       id = request.form['dbid']
       beid = request.form['beid']
       log.debug("Got SG: {0} ID: {1} and BEID: {2} from form.".format(subgroup, id, beid))
       front_end.add_update_show(id, beid, subgroup, app.config)
       log.debug("Refreshing user's page.")
       return redirect('/')
    elif logged_in and request.method == 'GET':
        log.debug("Request method is GET, so showing page to user.")
        if 'id' in request.args:
            id = request.args['id']
            log.debug("Attempting to operate on id {0}".format(id))
            sonarr_show = front_end.search_show_from_backend(id, app.config)
            if not sonarr_show:
                log.debug("Could not find show from backend with ID {0}".format(id))
                abort(404)
            db_show = front_end.get_show_from_db(id)
            subgroups = front_end.get_subgroups(id)
            selected_group = front_end.get_selected_group(sonarr_show['beid'], app.config)
            fanart = front_end.get_fanart(sonarr_show)
            log.debug("Rendering form for user")
            return render_template("add.html", id=id, title=db_show['title'], subgroups=subgroups, selectedGroup=selected_group, sonarr=sonarr_show, logged_in=logged_in, fanart=fanart, action=request.path.strip('/'))
        log.debug("No ID sent with request, so just refresh user's page to the home.")
        return redirect('/')
    log.debug("User cannot be authenticated, send 404 to hide page.")
    abort(404)

if __name__=="__main__":
    app.run(host="0.0.0.0",port="8081",debug=True)
