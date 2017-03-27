#!/usr/bin/env python3
from flask import render_template, session, request, make_response, escape, jsonify, abort, redirect
from urllib.parse import unquote_plus
from aniping import front_end, config
from flask_apscheduler import APScheduler
import os, time, sys, datetime, atexit, logging

app = application = config.Flask(__name__, template_folder='views', static_folder='static')
app.config.from_yaml(os.environ.get('ANIPING_CONFIG', os.path.join(app.root_path, 'config/config.yml')))

if app.config["DEBUG"]:
    logging.basicConfig(level=logging.DEBUG)
    logging.debug("Debug mode active.")
else:
    logging.basicConfig(level=logging.INFO)
    
log = logging.getLogger(__name__)
        
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
scheduler.init_app(app)
scheduler.start()

@app.route('/search')
@app.route('/')
def index():
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
    log.debug("Entering logout, attempting to end session.")
    front_end.delete_login_id(escape(session['logged_in']))
    session.pop('logged_in', None)
    log.debug("Returning to user.")
    return jsonify({ "logout": "success" })

@app.route('/star')
def star():
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
