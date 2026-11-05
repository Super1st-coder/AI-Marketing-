'''
Created on 17 dic. 2019

@author: ramon
'''
from app.v1.repository.application import ApplicationRepository, CoinRepository

class GetApplicationUseCase(object):
    def execute(self,security_credentials):
        data = ApplicationRepository(username=security_credentials['username']).get()
        return data.__dict__ 

class GetDefaultCoinUseCase(object):
    def execute(self,security_credentials):
        data = CoinRepository(username=security_credentials['username']).getDefault()
        return data.__dict__ 
    
class GetCoinBySymbolUseCase(object):
    def execute(self,security_credentials,query_params):
        data = CoinRepository(username=security_credentials['username']).getBySymbol(query_params['symbol'])
        return data.__dict__         
