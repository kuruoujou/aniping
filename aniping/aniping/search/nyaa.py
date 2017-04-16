#!/usr/bin/env python3
import feedparser, logging
from urllib.parse import quote_plus
from aniping.plugins import SearchEngine

log = logging.getLogger(__name__)

FILTER_MAP = {
    "show all":         0,
    "filter remakes":   1,
    "trusted only":     2,
    "a+ only":          3
    }
CATEGORY_MAP = {
    "all categories":                       "0_0",
    "anime":                                "1_0",
    "anime - anime music video":            "1_32",
    "anime - english-translated":           "1_37",
    "anime - non-english-translated":       "1_38",
    "anime - raw":                          "1_11",
    "audio":                                "3_0",
    "audio - lossless":                     "3_14",
    "audio - lossy":                        "3_15",
    "literature":                           "2_0",
    "literature - english-translated":      "2_12",
    "literature - non-english-translated":  "2_39",
    "literature - raw":                     "2_13",
    "live action":                          "5_0",
    "live action - english-translated":     "5_19",
    "live action = idol/promotion video":   "5_22",
    "live action - non-english-translated": "5_21",
    "live_action - raw":                    "5_20",
    "pictures":                             "4_0",
    "picutres - graphics":                  "4_18",
    "pictures - photos":                    "4_17",
    "software":                             "6_0",
    "software - applications":              "6_23",
    "software - games":                     "6_24"
    }  

class Nyaa(SearchEngine):
    """Nyaa Search Engine Plugin.
    
    This plugin implements the nyaa.se search engine for finding shows
    and subgroups.
    """
    def __init__(self, config, plugin_manager):
        """Initilizes the nyaa search plugin.
        
        Args:
            config (dict): The configuration dictionary as read by flask.
            plugin_manager (:obj:`AniPluginManager): An instance of the AniPluginManager.
        """
        super().__init__(config, plugin_manager)
        self.__name__       = "Nyaa Torrents"
        self.__id__         = "nyaa"
        self.__author__     = "Spencer Julian <hellothere@spencerjulian.com>"
        self.__version__    = "0.01"
        
        self.config = self._config['NYAA']
        self._name = self.config['NAME'] if 'NAME' in self.config else 'Nyaa Torrents'
        self._filter = FILTER_MAP[self.config['FILTER'].lower()] if 'FILTER' in self.config else 0
        self._category = CATEGORY_MAP[self.config['CATEGORY'].lower()] if 'CATEGORY' in self.config else "0_0"
        self._url = "https://www.nyaa.se/?page=rss&cats={0}&filter={1}".format(self._category, self._filter)
        
    @property 
    def name(self) -> str:
        """str. Returns the name of the plugin."""
        return self._name
    
    @property 
    def url(self) -> str:
        """str. Returns the RSS url we are parsing from."""
        return self._url
        
    @property
    def category(self) -> str:
        """str. Returns the category ID we are looking at in Nyaa."""
        return self._category
        
    @property
    def filter(self) -> int:
        """int. Returns the filter ID we are looking at in nyaa."""
        return self._filter
        
    def results(self, query):
        """Result gathering function.
        
        Searches nyaa for a given show and returns the results.

        Args:
            query (string): The show title to search for.
                
        Returns:
            tuple. Contains two lists.
                
                * groups - A list of sub groups parsed from the results.
                * results - A list of raw results.
        """
        results = self._query(query)
        groups = self._get_subgroups(results)
        return groups, results
        
    def _query(self, query):
        """Query search function.
        
        Searches nyaa for a given query and returns results.
        
        Args:
            query (str): The query to search nyaa with
                
        Returns:
            list. Items from rss.
        """
        rss = feedparser.parse("{0}&term={1}".format(self._url, quote_plus(query)))
        return rss['items']

    def _get_subgroups(self, search_results):
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