#!/usr/bin/env python3
"""search

This submodule handles functions to call out to the
search engine. Currently, this engine is nyaa.
We primarily use the search engine for gathering
information about subgroups currently working on a show.
"""
import feedparser, logging
from urllib.parse import quote_plus
from aniping import db

log = logging.getLogger(__name__)

def query(query):
        """Query search function.
        
        Searches nyaa for a given query and returns results.
        
        Args:
            query (str): The query to search nyaa with
                
        Returns:
            list. Items from rss.
        """
        rss = feedparser.parse("https://www.nyaa.se/?page=rss&cats=1_37&filter=2&term={0}".format(quote_plus(query)))
        return rss['items']

def results(id):
        """Result gathering function.
        
        Searches nyaa for a given show and returns the results.

        Args:
            id (int): The database id of the show to search for.
                
        Returns:
            tuple. Contains two lists.
                
                * groups - A list of sub groups parsed from the results.
                * results - A list of raw results.
        """
        show = db.get_show(id=id)
        results = query(show['title'])
        groups = get_subgroups(results)
        return groups, results

def get_subgroups(search_results):
        """Subgroup Parsing Function.
        
        Parses the nyaa search results and comes up with a list of sub groups.
        Most sub groups use a normal format of ``[group_name] show info [resolution]``,
        with other data potentially in brackets.
        
        Args:
            search_results (list): The results from a nyaa search.
                
        Returns:
            list. Subgroups listed in the results.
        """
        groups = set()
        for result in search_results:
                title = result['title']
                if '[' in title and ']' in title:
                        group = title.split('[')[1].split(']')[0]
                else:
                        continue
                #Just some checks for things commonly in brackets that aren't subgroups...
                if '720' in group:
                        continue
                if 'x264' in group:
                        continue
                if 'AAC' in group:
                        continue
                if '1080' in group:
                        continue
                if '8bit' in group or '8 bit' in group or '10bit' in group or '10 bit' in group:
                        continue
                if '480' in group:
                        continue
                groups.add(group)
        groups = list(groups)
        groups.sort()
        return groups