from jinja2 import Environment, FileSystemLoader
import requests
import pandas as pd
from app.repository.base import SinergiaRepository
from app.repository.marketing import AccountRepository

class SecurityManager:

    sinergiaRepository = SinergiaRepository()
    accountRepository = AccountRepository()

    def login(self,username,password):
        account = self.accountRepository.get_by_email(username)
        logged_user = None
        if not account is None :
            credentials = self.sinergiaRepository.login(username,password)
            if not credentials is None:
                logged_user = account
        return logged_user
    
    def register(self, email, first_name, last_name, password):
        name = f'{first_name} {last_name}'

        registered = False

        strapi_account = self.accountRepository.get_by_email(email)
        if strapi_account is None:
            strapi_account = self.accountRepository.new(email,name)
            self.accountRepository.create(strapi_account)
            registered_strapi_account = self.accountRepository.get_by_email(email)
            if not registered_strapi_account is None:
                registered = self.sinergiaRepository.register(email, first_name, last_name, password)

        return registered
    
    def confirm_account(self, email, confirmation_code):
        return self.sinergiaRepository.confirm_account(email, confirmation_code)    
    

    def init_reset_password(self, email):
        action_executed  = False

        strapi_account = self.accountRepository.get_by_email(email)
        if not strapi_account is None:
            #  Iniciar el proceso de reinicio de contrasena
            action_executed = self.sinergiaRepository.init_reset_password(email)

        return action_executed
    
    def change_password(self, email, confirmation_code,new_password):
        return self.sinergiaRepository.change_password(email, confirmation_code,new_password)    
