#!/usr/bin/env python3
import feedparser, logging
from urllib.parse import quote_plus
from aniping.plugins import SearchEngine

log = logging.getLogger(__name__)

class Rss(SearchEngine):
    """Generic RSS Search Engine Plugin.
    
    This plugin implements a generic RSS search engine for finding subgroups.
    Parsing assumes the subgroup name is in brackets.
    """
    def __init__(self, config, plugin_manager):
        """Initilizes the rss search plugin.
        
        Args:
            config (dict): The configuration dictionary as read by flask.
            plugin_manager (:obj:`AniPluginManager): An instance of the AniPluginManager.
        """
        super().__init__(config, plugin_manager)
        self.__name__       = "Generic RSS Search"
        self.__id__         = "rss"
        self.__author__     = "Spencer Julian <hellothere@spencerjulian.com>"
        self.__version__    = "0.01"
        
        self.config = self._config['RSS']
        self._name = self.config['NAME'] if 'NAME' in self.config else 'Generic RSS Search'
        self._urls = self.config['URL']
        
    @property 
    def name(self):
        """str. Returns the name of the plugin."""
        return self._name
    
    @property 
    def url(self):
        """str. Returns the RSS urls we are parsing from."""
        return self._urls
        
    def results(self, query):
        """Result gathering function.
        
        Searches rss for a given show and returns the results.

        Args:
            query (string): The show title to search for.
                
        Returns:
            tuple. Contains two lists.
                
                * groups - A list of sub groups parsed from the results.
                * results - A list of raw results.
        """
        rss_all = []
        for url in self._urls:
            rss_all.append(feedparser.parse(url)['items'])
        # Flatten above list of lists, because we really don't care what feed we use.
        rss = [item for sublist in rss_all for item in sublist]
        results = []
        # Ignore spaces and case. Sometimes it's different between groups.
        tempquery = query.replace(" ", "").lower()
        for item in rss:
            temptitle = item['title'].replace(" ", "").lower()
            if tempquery in temptitle:
                results.append(item) 
        groups = self._get_subgroups(results)
        return groups, results

    def _get_subgroups(self, search_results):
        """Subgroup Parsing Function.
        
        Parses the nyaa search results and comes up with a list of sub groups.
        Most sub groups use a normal format of ``[group_name] show info [resolution]``,
        with other data potentially in brackets.
        
        Args:
            search_results (list): The results from a search.
                
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
