#!/usr/bin/env python3
import feedparser, logging
from urllib.parse import quote_plus
from aniping.plugins import SearchEngine

log = logging.getLogger(__name__)

FILTER_MAP = {
    "show all":         0,
    "filter remakes":   2,
    "trusted":          3,
    "a+":               4
    }
CATEGORY_MAP = {
    "all categories":                       "_",
    "anime":                                "3_",
    "anime - anime music video":            "3_12",
    "anime - english-translated":           "3_5",
    "anime - non-english-translated":       "3_13",
    "anime - raw":                          "3_6",
    "audio":                                "2_",
    "audio - lossless":                     "2_3",
    "audio - lossy":                        "2_4",
    "literature":                           "4_",
    "literature - english-translated":      "4_7",
    "literature - non-english-translated":  "4_14",
    "literature - raw":                     "4_8",
    "live action":                          "5_",
    "live action - english-translated":     "5_9",
    "live action = idol/promotion video":   "5_10",
    "live action - non-english-translated": "5_18",
    "live_action - raw":                    "5_11",
    "pictures":                             "6_",
    "picutres - graphics":                  "6_15",
    "pictures - photos":                    "6_16",
    "software":                             "1_",
    "software - applications":              "1_1",
    "software - games":                     "1_2"
    }  

class NyaaPantsu(SearchEngine):
    """Nyaa Search Engine Plugin.
    
    This plugin implements the nyaa.pantsu.cat search engine for finding shows
    and subgroups.
    """
    def __init__(self, config, plugin_manager):
        """Initilizes the nyaa search plugin.
        
        Args:
            config (dict): The configuration dictionary as read by flask.
            plugin_manager (:obj:`AniPluginManager): An instance of the AniPluginManager.
        """
        super().__init__(config, plugin_manager)
        self.__name__       = "NyaaPantsu Torrents"
        self.__id__         = "nyaapantsu"
        self.__author__     = "Spencer Julian <hellothere@spencerjulian.com>"
        self.__version__    = "0.01"
        
        self.config = self._config['NYAAPANTSU']
        self._name = self.config['NAME'] if 'NAME' in self.config else 'NyaaPantsu Torrents'
        self._filter = FILTER_MAP[self.config['FILTER'].lower()] if 'FILTER' in self.config else 0
        self._category = CATEGORY_MAP[self.config['CATEGORY'].lower()] if 'CATEGORY' in self.config else "_"
        self._url = "https://nyaa.pantsu.cat/search?c={0}&s={1}&limit=300&userID=0".format(self._category, self._filter)
        
    @property 
    def name(self):
        """str. Returns the name of the plugin."""
        return self._name
    
    @property 
    def url(self):
        """str. Returns the RSS url we are parsing from."""
        return self._url
        
    @property
    def category(self):
        """str. Returns the category ID we are looking at in Nyaa."""
        return self._category
        
    @property
    def filter(self):
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
