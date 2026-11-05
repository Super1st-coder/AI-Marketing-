'''
Created on 17 dic. 2019

@author: ramon
'''
import os
from configparser import ConfigParser,SafeConfigParser
import pathlib
from dotenv import load_dotenv


def load_configuration_file():
    load_dotenv()
    envName = 'dev' if not os.environ.get('CONFIG_TYPE') else os.environ.get('CONFIG_TYPE') 
    parser = SafeConfigParser(os.environ)
    configDir =  os.path.join(str(pathlib.Path.cwd()),'config')
    configFilePath =  os.path.join(configDir,'configuration-%s.cfg' % envName if envName else 'dev')
    parser.read(configFilePath)
    return parser