#!/usr/bin/env python3
import feedparser, logging
from urllib.parse import quote_plus
from aniping.plugins import SearchEngine

log = logging.getLogger(__name__)

CATEGORY_MAP = {
        "all":              0,
        "anime":            1,
        "non-english":      10,
        "manga":            3,
        "drama":            8,
        "music":            2,
        "music video":      9,
        "raws":             7,
        "hentai":           4,
        "hentai (anime)":   12,
        "hentai (manga)":   13,
        "hentai (games)":   14,
        "batch":            11,
        "JAV":              15,
        "other":            5
    }  

class TokyoToshoKan(SearchEngine):
    """Tokyo Toshokan Search Engine Plugin.
    
    This plugin implements the tokyotosho.info search engine for finding shows
    and subgroups.
    """
    def __init__(self, config, plugin_manager):
        """Initilizes the tokyotosho search plugin.
        
        Args:
            config (dict): The configuration dictionary as read by flask.
            plugin_manager (:obj:`AniPluginManager): An instance of the AniPluginManager.
        """
        super().__init__(config, plugin_manager)
        self.__name__       = "Tokyo Toshokan"
        self.__id__         = "tokyotoshokan"
        self.__author__     = "Spencer Julian <hellothere@spencerjulian.com>"
        self.__version__    = "0.01"
        
        self.config = self._config['TOKYOTOSHOKAN']
        self._name = self.config['NAME'] if 'NAME' in self.config else 'Tokyo Toshokan'
        self._category = CATEGORY_MAP[self.config['CATEGORY'].lower()] if 'CATEGORY' in self.config else "0"
        self._url = "https://www.tokyotosho.info/rss.php?type={0}&searchName=true&searchComment=true&size_min=&size_max=&username=".format(self._category)
        
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
        
        Searches tokyo toshokan for a given show and returns the results.

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
        
        Searches tokyo toshokan for a given query and returns results.
        
        Args:
            query (str): The query to search tokyo toshokan with
                
        Returns:
            list. Items from rss.
        """
        rss = feedparser.parse("{0}&terms={1}".format(self._url, quote_plus(query)))
        return rss['items']

    def _get_subgroups(self, search_results):
        """Subgroup Parsing Function.
        
        Parses the TTK search results and comes up with a list of sub groups.
        Most sub groups use a normal format of ``[group_name] show info [resolution]``,
        with other data potentially in brackets.
        
        Args:
            search_results (list): The results from a TTK search.
                
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
