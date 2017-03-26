import os, yaml, logging
from flask import Flask as BaseFlask, Config as BaseConfig

log = logging.getLogger(__name__)


class Config(BaseConfig):
    """https://gist.github.com/mattupstate/2046115"""
    def from_yaml(self, config_file):
        env = os.environ.get('FLASK_ENV', 'development')
        self['ENVIRONMENT'] = env.lower()
        
        with open(config_file) as f:
            config = yaml.safe_load(f)
            
        config = config.get(env.upper(), config)
        
        for key in config.keys():
            if key.isupper():
                self[key] = config[key]
                
class Flask(BaseFlask):
    def make_config(self, instance_relative=False):
        root_path = self.root_path
        if instance_relative:
            root_path = self.instance_path
        return Config(root_path, self.default_config)