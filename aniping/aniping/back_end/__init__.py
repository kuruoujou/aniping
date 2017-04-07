#!/usr/bin/env python3

_logger = logging.getLogger(__name__)

class BackEnd(object):
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