'''
Created on 17 dic. 2019

@author: ramon
'''
from app.tools.utils import generate_numeric_password
import datetime
from app.v1.models.constant import AUTOREGISTER, MOBILE_USER, STATUS_ACTIVE, STATUS_PENDING, STATUS_UNSUBSCRIBE
from app.v1.models.security import SecurityElement, User, PersonExtension
from app import db
from app.exceptions.base import DataAlreadyRegisteredException, DataNotFoundException, UserCurrentPasswordException,UserRepeatedPasswordException,IncorrectValidationException,RepositoryUnknownException
from app.exceptions.base import NotImplementedException
from .base import SinergiaRepository,CacheRepository
from  app.tools.email import send_account_confirmation_mail,send_reset_password_mail

import hashlib

from datetime import date

from cerberus import Validator
import yaml

from config import config
import os

from urllib.parse import quote


config_type = os.environ['CONFIG_TYPE']

class SecurityElementRepository(object):
    
    def getByAuthToken(self,token):
        security_element = SecurityElement.verify_auth_token(token)
        return security_element
    
    def getByName(self,name):
        security_element = SecurityElement.query.filter(SecurityElement.name==name.lower()).first()
        return security_element

class UserRepository(object):

    def getByName(self,name):
        user = User.query.filter(User.name==name.lower()).first()
        return user

class MemberRepository(SinergiaRepository):

    def get(self,query_params,full=False):
        result = User.query.filter(User.name == self.username).first()
        return result

    def getByEmail(self,email):
        result = User.query.filter(User.name == email).first()
        return result
    
    def save(self,payload):
        user = User.query.filter(User.name == self.username).first()
        
        first_name =  payload['first_name']
        last_name =  payload['last_name']
        phone_number =  payload['phone_number']
        gender =  payload['gender']
        secondary_email =  payload['secondary_email']
        birth_date =  payload['birth_date']
    
        user.person_extension.first_name = first_name
        user.person_extension.last_name = last_name
        user.person_extension.fullname =  first_name + ' ' + last_name
        user.person_extension.phone_number = phone_number
        user.person_extension.gender = gender
        user.person_extension.secondary_email = secondary_email
        user.person_extension.birth_date = birth_date

        db.session.add(user)
        db.session.commit()
    
    def changePassword(self,payload):

        user = User.query.filter(User.name == self.username).first()

        new_password = payload['password']
        old_password = payload['old_password']        

        if not user.verify_password(old_password):
            raise UserCurrentPasswordException()
        
        if (new_password is not None) and (new_password != ''):
            new_password_hash = hashlib.md5(new_password.encode('utf-8')).hexdigest()
            if new_password_hash == user.password_hash:
                raise UserRepeatedPasswordException()
            user.hash_password(new_password)
            
        db.session.add(user)
        db.session.commit()        


    def initResetPassword(self,data):

        schema_text = '''
            email:
                type: string
                empty: False
                required: True
                regex: ^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$
        '''

        schema = yaml.safe_load(schema_text)
        v  = Validator()

        validation_result = v.validate(data, schema)

        if not validation_result:
            raise IncorrectValidationException(v.errors)

        
        user = self.getByEmail(data['email'])
        if user is None:
            raise DataNotFoundException('Email is not Registered!')
        
        cacheRepository = CacheRepository()
        confirmation_code = generate_numeric_password(6)

        key = f"reset_password_{data['email']}"
        payload = {
            'confirmation_code' : confirmation_code
        }
        cacheRepository.save(key, payload, expired_time = int(120))

        destination = data['email']
        reset_password_service_uri = config[config_type].RESET_PASSWORD_SERVICE_URI
        first_name = user.person_extension.first_name
        params = {
            "first_name" : first_name,
            "reset_link" : f'{reset_password_service_uri}?account={quote(destination)}&code={confirmation_code}'
        }

        send_reset_password_mail(destination,params) 

        return params
    
    def finishResetPassword(self,data):
        schema_text = '''
            email:
                type: string
                empty: False
                required: True
                regex: ^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$
            confirmation_code:
                type: string
                empty: False
                required: True
            new_password:
                type: string
                empty: False
                required: True                
        '''

        schema = yaml.safe_load(schema_text)
        v  = Validator()

        validation_result = v.validate(data, schema)

        if not validation_result:
            raise IncorrectValidationException(v.errors)

        user = self.getByEmail(data['email'])
        if user is None:
            raise DataNotFoundException('Email is not Registered!')
        
        cacheRepository = CacheRepository()
        key = f"reset_password_{data['email']}"
        confirmation_code = data['confirmation_code']

        stored_data = cacheRepository.getByKey(key)
        if not stored_data is None:
            if confirmation_code == stored_data['confirmation_code']:
                new_password = data['new_password']

                if (not new_password is  None) and (new_password != ''):
                    new_password_hash = hashlib.md5(new_password.encode('utf-8')).hexdigest()
                    if new_password_hash == user.password_hash:
                        raise UserRepeatedPasswordException()
                    user.hash_password(new_password)
                    
                db.session.add(user)
                db.session.commit()

                cacheRepository.deleteByKey(key)
            else:
                raise IncorrectValidationException('Incorrect Validation Code!')
        else:
            raise IncorrectValidationException('Should Init Reset Password Process!')            

        # destination = data['email']
        # params = {
        #     "confirmation_code": confirmation_code,
        # }

        return user
        
    
    def changeOperationKey(self,payload):
        # TODO: Cambiar la clave de operaciones especiales
        raise NotImplementedException()

    def resetOperationKey(self,payload):
        # TODO: Reiniciar la clave de operaciones especiales
        raise NotImplementedException()
    

    def initCreate(self,data):

        schema_text = '''
            email:
                type: string
                empty: False
                required: True
                regex: ^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$
            first_name:
                type: string
            last_name:
                type: string        
            password:
                type: string
                empty: False
                minlength: 6
                required: True
            gender:
                type: string
                maxlength: 1
            birth_date:
                type: string
            phone_number:
                type: string            
        '''


        schema = yaml.safe_load(schema_text)
        v  = Validator()

        validation_result = v.validate(data, schema)

        if not validation_result:
            raise IncorrectValidationException(v.errors)


        user = self.getByEmail(data['email'])
        if user:
            raise DataAlreadyRegisteredException('Email is Registered!')

        try:

            first_name =  data['first_name']
            last_name =  data['last_name']
            # phone_number =  data['phone_number']
            # gender =  data['gender']
            # birth_date =  data['birth_date']
            password = data['password']
            confirmation_code = generate_numeric_password(6)
        
            person = PersonExtension()
            person.email = data['email'].lower()
            person.first_name = data['first_name']
            person.last_name = data['last_name']
            person.fullname = data['first_name'] + ' ' + data['last_name'] 
            person.phone_number = '#' # phone_number
            person.gender = '-' # gender
            person.birth_date = date.today() # birth_date
            person.status = STATUS_ACTIVE
            db.session.add(person)

            user = User()
            user.person_extension = person
        
            user.hash_password(password)
            user.operation_key = confirmation_code
            user.register_date = datetime.datetime.now() 
            user.name = data['email'].lower()

            user.status = STATUS_PENDING

            user.register_mode= AUTOREGISTER
            user.type = MOBILE_USER
            
            db.session.add(user)
            db.session.commit()
    
            destination = data['email']

            confirmation_service_uri = config[config_type].ACCOUNT_CONFIRMATION_SERVICE_URI
            unsubscribe_service_uri = config[config_type].ACCOUNT_UNSUBSCRIBE_SERVICE_URI

            params = {
                "confirmation_code": confirmation_code,
                "email" : destination,
                "first_name" : first_name,
                "confirmation_link" : f'{confirmation_service_uri}?account={quote(destination)}&code={confirmation_code}',
                "unsubscribe" : f'{unsubscribe_service_uri}?account={quote(destination)}&code={confirmation_code}'
            }

            send_account_confirmation_mail(destination,params) 


        except Exception as e:
            raise RepositoryUnknownException(str(e))
            

        return user


    def finishCreate(self,data):

        schema_text = '''
            email:
                type: string
                empty: False
                required: True
                regex: ^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$
            confirmation_code:
                type: string
                empty: False
                required: True
        '''

        schema = yaml.safe_load(schema_text)
        v  = Validator()

        validation_result = v.validate(data, schema)

        if not validation_result:
            raise IncorrectValidationException(v.errors)


        user = self.getByEmail(data['email'])
    
        if user is not None:

            confirmation_code = data['confirmation_code']
            if user.status == STATUS_PENDING:
                if user.operation_key == confirmation_code:
                    user.status = STATUS_ACTIVE
                    db.session.add(user)
                    db.session.commit()            
                else:
                    raise IncorrectValidationException('Incorrect Validation Code!')
            else:
                raise IncorrectValidationException('Incorrect Status for Activation!')

        else:
            raise DataNotFoundException('Email Not Found!')
        
        return user

    def unsubscribe(self,data):

        schema_text = '''
            email:
                type: string
                empty: False
                required: True
                regex: ^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$
            confirmation_code:
                type: string
                empty: False
                required: True
        '''

        schema = yaml.safe_load(schema_text)
        v  = Validator()

        validation_result = v.validate(data, schema)

        if not validation_result:
            raise IncorrectValidationException(v.errors)


        user = self.getByEmail(data['email'])
    
        if user is not None:

            confirmation_code = data['confirmation_code']
            if user.status == STATUS_PENDING:
                if user.operation_key == confirmation_code:
                    user.status = STATUS_UNSUBSCRIBE
                    db.session.add(user)
                    db.session.commit()            
                else:
                    raise IncorrectValidationException('Incorrect Validation Code!')
            else:
                raise IncorrectValidationException('Incorrect Status for Activation!')

        else:
            raise DataNotFoundException('Email Not Found!')
        
        return user
    
    def resendConfirmation(self,data):

        schema_text = '''
            email:
                type: string
                empty: False
                required: True
                regex: ^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$
        '''

        schema = yaml.safe_load(schema_text)
        v  = Validator()

        validation_result = v.validate(data, schema)

        if not validation_result:
            raise IncorrectValidationException(v.errors)

        user = self.getByEmail(data['email'])
    
        if user is not None:

            if user.status == STATUS_PENDING:

                try:            
                    destination = data['email']
                    first_name = user.person_extension.first_name
                    confirmation_code = user.operation_key
                    confirmation_service_uri = config[config_type].ACCOUNT_CONFIRMATION_SERVICE_URI
                    unsubscribe_service_uri = config[config_type].ACCOUNT_UNSUBSCRIBE_SERVICE_URI

                    params = {
                        "confirmation_code": confirmation_code,
                        "email" : destination,
                        "first_name" : first_name,
                        "confirmation_link" : f'{confirmation_service_uri}?account={quote(destination)}&code={confirmation_code}',
                        "unsubscribe" : f'{unsubscribe_service_uri}?account={quote(destination)}&code={confirmation_code}'
                    }

                    send_account_confirmation_mail(destination,params) 

                except Exception as e:
                    raise RepositoryUnknownException(str(e))

            else:
                raise IncorrectValidationException('Incorrect Status for Resend Confirmation!')

        else:
            raise DataNotFoundException('Email Not Found!')
        
        return user


    def gerPermissionsByUsername(self,username):
        sql = '''
        select fr.actions, f."name" as function_name, f.long_name as function_long_name, r."name" as rol_name, r.id_name as rol_long_name
        from function_rol fr, rol r, "function" f, securityelement_rol sr, securityelement s 
        where fr.rol_id = r.id 
        and fr.function_id = f.id 
        and r.id = sr.rol_id 
        and sr.securityelement_id = s.id 
        and s."name" = '{username}'
        '''

        sql = sql.format(**{'username':username})
        rows = db.session.execute(sql)
        data_rows = [{column: value for column, value in rowproxy.items()} for rowproxy in rows]
        
        return data_rows
        