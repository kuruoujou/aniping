#!/usr/bin/env python3
import feedparser, logging
from urllib.parse import quote_plus
from aniping import db

log = logging.getLogger(__name__)

def query(query):
        """Searches nyaa for a given query.
        
        Args:
                query: The query to search nyaa with
        Returns:
                A list of items from rss.
        """
        rss = feedparser.parse("https://www.nyaa.se/?page=rss&cats=1_37&filter=2&term={0}".format(quote_plus(query)))
        return rss['items']

def results(id):
        """Searches nyaa for a given show and returns the results.

        Args:
                id: The ID of the show to search for.
        Returns:
                A list of sub groups from the results, along with a list of raw results, in a tuple (in that order).
        """
        show = db.get_show(id=id)
        results = query(show['title'])
        groups = get_subgroups(results)
        return groups, results

def get_subgroups(search_results):
        """Parses the nyaa search results and comes up with a list of sub groups.
        
        Args:
                search_results: The results from a nyaa search.
        Returns:
                A list of sub groups listed in the results.
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