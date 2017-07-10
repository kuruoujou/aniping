.. _quick-start:

Quick Start Guide
=================

Installation
------------
Right now, the fastest way to get going is using Docker_. If you're unfamiliar with Docker
or don't want to set it up, head over to the :ref:`tutorial` for instructions on setting up using
a virtual environment.

There are plans to set up the repository to be able to deploy in Heroku_, but they aren't yet
implemented.

To deploy using Docker, make sure you docker downloaded and installed according to the 
`Docker installation instructions`_. If you have a more complicated setup, using something like 
Kubernetes, Docker Swarm, or Mesos, great! Setting those up is outside the scope of this guide,
unfortunately, but you should be able to figure out the settings you need based on this guide.

The run command is pretty straightforward::

    docker run -d -v /etc/localtime:/etc/localtime:ro -v /etc/timezone:/etc/timezone:ro -v $LOCAL_CONFIG:/app/config -p 80:80 kuroshi/aniping

Let's step through it:

- ``-d`` runs the container in a deamonized mode, as a service.
- ``-v /etc/localtime:/etc/localtime:ro`` maps your local time into the container as a read-only volume.
- ``-v /etc/timezone/etc/timezone:ro`` maps your timezone into the container as a read-only volume.
- ``-v $LOCAL_CONFIG:/app/config`` Replace ``$LOCAL_CONFIG`` with the directory you will store the ``config.yml`` file, and that will be mapped in appropriately.
- ``-p 80:80`` maps port 80 in the container to port 80 outside the container.
- ``kuroshi/aniping`` is the container you're downloading from the dockerhub.

Configuration
-------------
Now that you've got the docker container running, you'll need to make a config file. In your 
``$LOCAL_CONFIG`` directory, place a file called ``config.yml`` with the following::

		SONARR:
			URL: https://my.sonarr.url
			API_KEY: my-sonarr-api-key
			QUALITY_PROFILE: HD - 720p/1080p
			LIBRARY_PATH: /path/to/sonarrs/library
		NYAA:
			FILTER: Trusted Only
			CATEGORY: Anime - English-translated
		ANILIST:
			CLIENT_ID: anilist_client_id
			CLIENT_SECRET: anilist_client_secret
		SQLITE:
			FILE: db/aniping.sqlite
			SCHEMA: schema.ddl
		BACK_END: Sonarr
		DATABASE: Sqlite
		SEARCH:
			- Nyaa
		SCRAPER:
			- Anilist
		SECRET_KEY: this is a totally random string and can be whatever you want
		IMAGE_CACHE: static/images/cache

	
**Spacing is important!** The file will not be read correctly if it is not indented, with spaces, like
it is above. You will need to change the values above to suit your needs. Defaults you don't need to change but you may want to change include ``BACK_END``, ``DATABASE``, ``SEARCH``, ``SCRAPER``, ``SQLITE``-> ``FILE``, ``SONARR``-> ``QUALITY_PROFILE``, and both options under ``NYAA``. You absolutely should not change ``SQLITE``-> ``SCHEMA`` unless you are using a different database, nor should you change ``IMAGE_CACHE`` unless you really know what you're doing. Everything else you will need to change.

.. _Docker: https://docker.com
.. _Heroku: https://heroku.com
.. _Docker installation instructions: https://docs.docker.com/engine/installation/
.. _Anilist Developer Page: https://anilist.co/settings/developer
