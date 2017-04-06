Aniping
========

.. image:: https://img.shields.io/docker/automated/kuroshi/aniping.svg   
   :target: https://hub.docker.com/r/kuroshi/aniping/
.. image:: https://readthedocs.org/projects/aniping/badge/?version=latest
   :target: http://aniping.readthedocs.io/en/latest/?badge=latest

Aniping is a front-end for `Sonarr <https://sonarr.tv/>`_ which collects the current
season's airing shows from `Anilist <https://anilist.co/>`_ and makes it easy to
select and download whatever shows you want to see.

Check out the installation guide below to get started.

Features
--------

- Uses Sonarr's login so you don't have to build a new account.
- Automatically determines groups subtitling the show to select from.
- Highlight shows to check out later, or add and remove shows from Sonarr.
- Self-hosted, your data isn't stored in some random server somewhere.

Installation
------------

Aniping is written in python using flask, but has a docker container for quick
setup. To setup the docker container and run, make sure you have docker installed
and just do this::

    docker run -d -v /etc/localtime:/etc/localtime:ro -v /etc/timezone:/etc/timezone:ro -v $LOCAL_CONFIG:/app/config -p 80:80 kuroshi/aniping

Change $LOCAL_CONFIG to a directory on your system where you will store the config
file. This will download and run the container for you, but it won't work yet! 
Some basic configuration is necessary to get going, described below.

You can additionally add ``/app/static/images/cache`` for poster images and 
``/app/db`` for aniping's db as volumes in the above command.

Configuration
-------------

Setup a config.yml in your configuration directory (by default aniping/config)
that looks like the following, changing your values as appropriate::

    LIBRARY_PATH: /path/to/sonarrs/library
    SONARR:
        URL: https://my.sonarr.url
        API_KEY: my-sonarr-api-key
        QUALITY_PROFILE: HD - 720p/1080p
    ANILIST:
        CLIENT_ID: anilist_client_id
        CLIENT_SECRET: anilist_client_secret
    SECRET_KEY: this is a totally random string and can be whatever you want
    IMAGE_CACHE: static/images/cache
    
Change the values above with the appropriate items. Do not change the ``IMAGE_CACHE``
value unless you know what you are doing! 

For instructions on getting your sonarr API key, check `the Sonarr docs 
<https://github.com/Sonarr/Sonarr/wiki/API#api-key>`_, and for instructions on 
getting your anilist client id and secret, check `the Anilist docs 
<https://anilist-api.readthedocs.io/en/latest/introduction.html#creating-a-client>`_ 
on the matter.

Finally, LIBRARY_PATH is the path that **Sonarr** uses to get to your library,
*not* aniping. Aniping has no real concept of your library, that's handled by
Sonarr.

Contribute
----------
This project is still in it's early stages! There are a few things I'd like to do
still, such as:

- Improve debug logging
- Improve documentation with Sphinx and RTD, or maybe GH-Pages
- Create a test framework (nose?) and implement a CI process using travis
- Modularize the aniping module, so that sonarr and anilist and other pieces can
  be swapped out with simple config file changes

So if you want to help out, please do! If you find a bug or something, please go
ahead and make an issue, or if you want to jump in and make a PR, there's nothing
stopping you!

- Issue Tracker: `<https://github.com/kuruoujou/aniping/issues>`_
- Source Code: `<https://github.com/kuruoujou/aniping>`_

Support
-------

If you are having issues, please let me know.
The best way to get support is by making an issue in github:
`<https://github.com/kuruoujou/aniping/issues>`_

License
-------

The project is licensed under the GNU LGPLv3 License.
