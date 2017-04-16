.. _plugins:

Plugin Development
==================

Pluggable Framework
-------------------
Aniping is written as a pluggable framework. There are four major plugin categories:
``back_end``, ``search``, ``scraper``, and ``db``. Each one performs a different task,
and aniping is basically the glue that puts them together. You can extend aniping
pretty easily just by building one of these plugins.

This page currently just has a high-level explanation of what these plugins are,
but building them is fairly easy. Most of the documentation is handled in the 
plugins module in this guide, and you can use the existing plugins as templates,
though some are more complicated then they perhaps should be.

There are three things to do when developing plugins for aniping:

- Put them in the correct directory.
- Make sure the extend the correct class described in the plugins module.
- Ensure they override the functions defined in the extended class.

That's all you need to do - the functions in the extended class will cause an
exception if they aren't overridden.

Backend
-------
In the default install, the backend for aniping is sonarr. The backend is the plugin
that handles downloading or watching of shows. These shows should not be licensed
in your country, of course.

Search
------
In the default install, the search engine for aniping is Nyaa. The search engine is
the plugin that handles finding the release groups for the show - other plugins
may use it to find specific results, however.

Scraper
-------
In the default install, the scraper for aniping is anilist. The scraper is a bit
of a misnomer, it's actually the repository of information for specific shows airing
this season. Another popular example is MyAnimeList.

DB
--
In the default install, the database for aniping is sqlite3. The database is where
the information from the scraper is held, as well as session ids, watching information,
and other details. It is a necessary component of aniping.
