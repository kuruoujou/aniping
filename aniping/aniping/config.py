#!/usr/bin/env python3
"""config

This submodule handles reading the config yaml file.
Since we use flask to handle the config file, all this
submodule does is extend the existing flask modules to support
the yaml format.

This is a terminal submodule for the aniping package, and so should
not import any additional aniping submodules.
"""
import os, yaml, logging
from flask import Flask as BaseFlask, Config as BaseConfig

log = logging.getLogger(__name__)


class Config(BaseConfig):
    """Extension of the flask config class.
    
    Adds the from_yaml function to the flask Config class.
    This function was found originally at
    https://gist.github.com/mattupstate/2046115.
    """
    def from_yaml(self, config_file):
        """Yaml config getter function.
        
        Reads a yaml flask config file and generates a config
        dictionary out of it that flask and aniping can 
        both understand.
        
        Args:
            config_file (str): the path of the config file to load.
                               Can be relative or absolute.
        """
        env = os.environ.get('FLASK_ENV', 'development')
        self['ENVIRONMENT'] = env.lower()
        
        with open(config_file) as f:
            config = yaml.safe_load(f)
            
        config = config.get(env.upper(), config)
        
        for key in config.keys():
            if key.isupper():
                self[key] = config[key]
                
class Flask(BaseFlask):
    """Extenstion of the flask class.
    
    This modifies the make_config function to support
    the Config.from_yaml function.
    """
    def make_config(self, instance_relative=False):
        """Config generation function.
    
        Determines what the root path of the app is and
        returns a config instance with that in mind.
    
        Args:
            instance_relative (bool): If this is a relative instance.
        Returns:
            A config object with the determined root path.
        """
        root_path = self.root_path
        if instance_relative:
            root_path = self.instance_path
        return Config(root_path, self.default_config)