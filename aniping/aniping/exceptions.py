#!/usr/bin/env python3

class AnipingError(Exception):
    pass
    
class NoPluginLoadedError(AnipingError):
    pass

class ObjectNotFoundError(AnipingError):
    pass
    
class BackEndNotFoundError(ObjectNotFoundError):
    pass