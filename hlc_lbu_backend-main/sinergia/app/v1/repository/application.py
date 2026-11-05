from getpass import getuser
from app.exceptions.base import DataNotFoundException, DatabaseException
from app.tools.substrate import Substrate
from app.v1.models.constant import STATUS_ACTIVE
from app.v1.models.payment import Application, Coin
from app.v1.models.security import SecurityElement, User, PersonExtension
from app.v1.models.business import Empresa
from app import redis_client, db
import json
import requests
from requests.auth import HTTPBasicAuth
from requests.exceptions import HTTPError
from .base import SinergiaRepository, SubstrateRepository
from config import config
from sqlalchemy.sql.expression import and_, asc

class ApplicationRepository(SinergiaRepository):

    def get(self):
        app_id = config['dev'].MASTER_APP_ID
        app = Application.query.filter(Application.id == app_id).first()
        print(app)
        return app


class CoinRepository(SinergiaRepository):
    
    def getDefault(self):
        app_id = config['dev'].MASTER_APP_ID
        status = STATUS_ACTIVE
        coin = Coin.query.filter(and_( Coin.status == status, Coin.application_id == app_id, Coin.blockchain_address != None )).first()
        return coin

    def getBySymbol(self,symbol):
        coin = Coin.query.filter(Coin.diminutive == symbol).first()
        return coin
