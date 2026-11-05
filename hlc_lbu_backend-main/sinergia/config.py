import os
import tempfile
from configparser import ConfigParser
import pathlib
from app.tools.config import load_configuration_file

basedir = os.path.abspath(os.path.dirname(__file__))
configuration = load_configuration_file()

class Config(object):
    DEBUG = True
    TESTING = False
    
    SECRET_KEY = configuration.get('SECURITY','SECRET_KEY')
    JWT_SECRET_KEY = SECRET_KEY
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = configuration.get('DB','DATABASE_URI')
    
    REDIS_URL = configuration.get('REDIS','DATABASE_URI') 

    CELERY_BROKER_URL = configuration.get('CELERY','BROKER_URL')
    CELERY_RESULT_BACKEND = configuration.get('CELERY','RESULT_BACKEND')
    CELERY_TASK_IGNORE_RESULT = configuration.get('CELERY','TASK_IGNORE_RESULT')
    CELERY_IMPORTS = configuration.get('CELERY','IMPORTS')

    MONGO_URI = configuration.get('MONGODB','DATABASE_URI') 

    SENDGRID_API_KEY = configuration.get('SENDGRID','SECRET_KEY')
    ACCOUNT_CONFIRMATION_TEMPLATE = configuration.get('SENDGRID','ACCOUNT_CONFIRMATION_TEMPLATE')
    RESET_PASSWORD_TEMPLATE = configuration.get('SENDGRID','RESET_PASSWORD_TEMPLATE')
    EMAIL_FROM = configuration.get('SENDGRID','EMAIL_FROM')

    N8N_SERVICE_URI = configuration.get('N8N','SERVICE_URI')
    
    STRAPI_URL = configuration.get('STRAPI', 'STRAPI_URL')
    STRAPI_TOKEN = configuration.get('STRAPI', 'STRAPI_TOKEN')


    JWT_BLACKLIST_ENABLED = True
    JWT_BLACKLIST_TOKEN_CHECKS = ['access', 'refresh']

    MASTER_APP_ID = configuration.get('DOCFABRIC','MASTER_APP_ID') 

    UPLOAD_FOLDER = configuration.get('FLASK','UPLOAD_FOLDER') 
    MAX_CONTENT_LENGTH = 65 * 1024 * 1024

    ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}

    ACCOUNT_CONFIRMATION_SERVICE_URI = configuration.get('ACCOUNT_CONFIRMATION','SERVICE_URI')
    RESET_PASSWORD_SERVICE_URI = configuration.get('RESET_PASSWORD','SERVICE_URI')
    ACCOUNT_UNSUBSCRIBE_SERVICE_URI = configuration.get('ACCOUNT_UNSUBSCRIBE','SERVICE_URI')

    IMAGE_LIBRARY_URL = configuration.get('IMAGE_LIBRARY', 'SERVICE_URI')
    IMAGE_LIBRARY_TOKEN = configuration.get('IMAGE_LIBRARY', 'SERVICE_TOKEN')

    FONT_BUCKET = configuration.get('BRAND', 'FONT_BUCKET')
    DOCS_BUCKET = configuration.get('BRAND', 'DOCS_BUCKET')
    REGION_BUCKET = configuration.get('BRAND', 'REGION_BUCKET')

    ABYSSALE_URL = configuration.get('ABYSSALE', 'SERVICE_URI')
    ABYSSALE_TOKEN = configuration.get('ABYSSALE', 'SERVICE_TOKEN')

    FURY_URL = configuration.get('FURY', 'SERVICE_URI')
    FURY_SERVICE_API_KEY = configuration.get('FURY', 'SERVICE_API_KEY')

    GCS_BUCKET = os.environ.get('GCS_BUCKET_NAME', '')
    GCS_SIGNED_URL_EXPIRATION = int(os.environ.get('GCS_SIGNED_URL_EXPIRATION', 900))

    PSD_RESIZE_URL = os.environ.get('PSD_RESIZE_URL', '')

#     def __init__(self):
#         CONFIG_FILE = self.load_file()
#         self.SQLALCHEMY_DATABASE_URI = CONFIG_FILE.get('db','DATABASE_URI')
    

class DevelopmentConfig(Config):
    DEBUG = True
#     SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'db_dev.db')
# REDIS_URL = "redis://:password@localhost:6379/0"


class TestingConfig(Config):
    TESTING = True
# REDIS_URL = "redis://:password@localhost:6379/0"
#     SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'db_test.db')
    #SECRET_KEY = 'testing'
    # SQLALCHEMY_DATABASE_URI = 'sqlite://'
    # SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, tempfile.mktemp(dir='.', suffix='.db'))
    # tempfile.mktemp(dir=basedir, suffix='.db')


class ProductionConfig(Config):
    pass
#     DATABASE_URI = os.environ.get('DATABASE_URI')
#     SECRET_KEY = os.environ.get('SECRET_KEY')
#     JWT_SECRET_KEY = SECRET_KEY


config = {
    'dev': DevelopmentConfig,
    'test': TestingConfig,
    'prod': ProductionConfig
}

