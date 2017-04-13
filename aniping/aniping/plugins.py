#/usr/bin/env python3

import logging, os, importlib, sys
from typing import Optional

_logger = logging.getLogger(__name__)

CATEGORIES={
    "back_end": {"directory": "back_end", "multiload": False, "class": "BackEnd", "config": "BACK_END"},
    "scraper": {"directory": "scraper", "multiload": True, "class": "Scraper", "config": "SCRAPER"},
    "db": {"directory": "db", "multiload": False, "class":"DataBase", "config": "DATABASE"},
    "search":{"directory": "search", "multiload": True, "class": "SearchEngine", "config": "SEARCH"}
    }

class AniPluginManager(object):
    def __init__(self, config):
        self._config = config
        self._available_plugins = {cat:[] for cat,v in CATEGORIES.items()}
        self._loaded_plugins = {cat:[] for cat,v in CATEGORIES.items()}
        
    @property
    def available_plugins(self) -> dict:
        return self._available_plugins
        
    @property
    def loaded_plugins(self) -> dict:
        out={}
        for cat,clses in self._loaded_plugins.items():
            out[cat] = []
            for cls in clses:
                out[cat].append(cls)
        return out
        
    @property
    def plugin_categories(self) -> list:
        return list(CATEGORIES.keys())
        
    def scan_for_plugins(self):
        for category,info in CATEGORIES.items():
            for module in os.listdir(os.path.join(os.path.dirname(__file__),info["directory"])):
                if module == "__init__.py" or module[-3:] != ".py":
                    continue
                importlib.import_module("aniping.{0}.{1}".format(info["directory"], module[:-3]))
                self._available_plugins[category].append(module[:-3])
        return self._available_plugins
        
    def load_plugins(self):
        for category,catinfo in CATEGORIES.items():
            if catinfo["config"] in self._config:
                plugins_to_load = self._config[catinfo["config"]] if isinstance(self._config[catinfo["config"]], list) else [self._config[catinfo["config"]]]
                for cls in eval(catinfo["class"]).__subclasses__():
                    if not any(isinstance(x, cls) for x in self._loaded_plugins[category]):
                        if catinfo["multiload"] and cls.__name__ in plugins_to_load:
                            self._loaded_plugins[category].append(cls(self._config, self))
                        elif not catinfo["multiload"] and cls.__name__ == plugins_to_load[0]:
                            self._loaded_plugins[category].append(cls(self._config, self))
        return self._loaded_plugins
        
    def plugin_category_function(self, category, func, *args, **kwargs):
        for cls in self._loaded_plugins[category]:
            return getattr(cls,func)(*args, **kwargs)
    
    def plugin_function(self, plugin, func, *args, **kwargs):
        for category, classes in self._loaded_plugins.items():
            for cls in classes:
                if cls.__id__ == plugin:
                    return getattr(cls,func)(*args, **kwargs)

    
class AniPlugin(object):
    def __init__(self, config, plugin_manager):
        self.__name__       = None
        self.__id__         = None
        self.__author__     = None
        self.__version__    = None
        
        self._config = config
        self.apm = plugin_manager
        
    @classmethod
    def back_end(self, func, *args, **kwargs):
        pass
        
    @classmethod
    def scraper(self, func, *args, **kwargs):
        pass
        
    @classmethod
    def db(self, func, *args, **kwargs):
        pass
        
    @classmethod
    def search(self, func, *args, **kwargs):
        pass
        
class BackEnd(AniPlugin):
    @property
    def name(self) -> Optional[str]:
        return None
    
    @property
    def url(self) -> str:
        return None
    
    @property
    def api_key(self) -> Optional[str]:
        return None
        
    @property
    def username(self) -> Optional[str]:
        return None
        
    @property
    def password(self) -> Optional[str]:
        return None
        
    def check_auth(self, username, password):
        raise NotImplementedError()
        
    def check_for_login(self):
        raise NotImplementedError()
        
    def search(self, title):
        raise NotImplementedError()
        
    def get_show(self, id):
        raise NotImplementedError()
    
    def get_watching_shows(self):
        raise NotImplementedError()
        
    def add_update_show(self):
        raise NotImplementedError()
        
    def remove_show(self, id):
        raise NotImplementedError()
        
    def subgroup_selected(self, id):
        raise NotImplementedError()
        
    def fanart(self, shows):
        raise NotImpelmentedError()
        
class SearchEngine(AniPlugin):
    @property
    def name(self) -> Optional[str]:
        return None
    
    @property
    def url(self) -> str:
        return None
               
    def get_show(self, query):
        raise NotImplementedError()