'''
Created on 17 dic. 2019

@author: ramon
'''
from app.v1.models.security import User, PersonExtension, Rol, Privilege, function_rol_table
from app.v1.models.business import Empresa
from app.v1.models.constant import * 
from app import db 
from app.exceptions.base import ParametersNotFoundException,DataNotFoundException,\
    DatabaseException,DataAlreadyRegisteredException,IncorrectValidationException
from app.v1.repository.base import SinergiaRepository, CacheRepository
from config import config
from app.tools.utils import generate_numeric_password
from app.tools.email import send_account_confirmation_mail

import pandas as pd 
import datetime
import os
import yaml

from urllib.parse import quote

from sqlalchemy import text, select, exc
from cerberus import Validator

config_type = os.environ['CONFIG_TYPE']

class MemberRepository(SinergiaRepository):

    def get(self,query_params):
        sql = '''
        SELECT DISTINCT s.*
        FROM securityelement s
        JOIN "user" u 
        ON s.id = u.id 
        JOIN personextension pe
        ON u.person_extension_id = pe.id
        LEFT JOIN securityelement_rol sr 
        ON s.id = sr.securityelement_id 
        LEFT JOIN rol r 
        ON sr.rol_id = r.id  
        {conditions}
        {order_by}
        {limits_offset}
        '''

        count_sql = '''
        SELECT COUNT(DISTINCT s.*) count_rows
        FROM securityelement s
        JOIN "user" u 
        ON s.id = u.id 
        JOIN personextension pe
        ON u.person_extension_id = pe.id
        LEFT JOIN securityelement_rol sr 
        ON s.id = sr.securityelement_id 
        LEFT JOIN rol r 
        ON sr.rol_id = r.id  
        {conditions}
        '''

        parameters = {'conditions' : '', 'order_by': '', 'limits_offset': ''}

        limit = 10  
        offset = 0        
        if len(query_params) > 0:

            if 'filter' in query_params:
                filter_conditions = query_params['filter']

                if len(filter_conditions) > 0 :

                    conditions = []         

                    if 'account' in filter_conditions:
                        conditions.append("s.name  LIKE  '%{account}%' ")

                    if 'cedula' in filter_conditions:
                        conditions.append("pe.id_number LIKE '%{cedula}%' ")

                    if 'first_name' in filter_conditions:
                        conditions.append("pe.first_name LIKE '%{first_name}%' ")

                    if 'last_name' in filter_conditions:
                        conditions.append("pe.last_name LIKE '%{last_name}%' ")

                    if 'rolname' in filter_conditions:
                        if type(filter_conditions['rolname']) == str:
                            conditions.append("r.name = '{rolname}' ")
                        else:
                            if type(filter_conditions['rolname'] is list) and len(filter_conditions['rolname']) > 1:
                                filter_conditions['rolname'] = tuple(filter_conditions['rolname'])    
                                conditions.append('r.name IN {rolname}')
                            else:
                                filter_conditions['rolname'] = (filter_conditions['rolname'][0])
                                conditions.append("r.name = '{rolname}' ")

                    if 'status' in filter_conditions:
                        conditions.append("s.status  LIKE  '%{status}%' ")

                    if 'user_type' in filter_conditions:
                        conditions.append("u.type = '{user_type}' ")

                    if 'user_accounts' in filter_conditions:
                        conditions.append("s.name in {user_accounts} ")
                    
                    if len(conditions) > 0: 
                        if len(conditions) > 1:
                            where_clausule = 'WHERE ' + ' AND '.join(conditions)
                            where_clausule = where_clausule.format(**filter_conditions)
                        else:
                            where_clausule = 'WHERE ' + ' '.join(conditions)
                            where_clausule = where_clausule.format(**filter_conditions)

                        parameters['conditions'] = where_clausule
                    else:
                        parameters['conditions'] = ''

            # Definiendo order
            if 'order' in query_params:
                order_criteria = query_params['order']
                new_order_criteria = [s.replace('account', 'name') for s in order_criteria]
                order_fields = ','.join(new_order_criteria)
                parameters['order_by'] = 'ORDER BY ' + order_fields


        # Definiendo los Rangos de Paginacion
        query_range = [0,10]
        if 'range' in query_params:
            query_range = query_params['range']
            if len(query_range) >= 2:
                low_limit = query_range[0] 
                high_limit = query_range[1] 
            else:
                low_limit = query_range[0]
                high_limit = query_range[0] 
            limit = (high_limit - low_limit) + 1
            offset = low_limit 
        parameters['limits_offset'] = ' LIMIT %s OFFSET %s ' % (limit,offset)

        sql = sql.format(**parameters)
        print(sql)

        try:

            textual_sql = text(sql)
            rows = db.session.query(User).from_statement(textual_sql).all()
            count_result_rows = len(rows)

            count_sql = count_sql.format(**parameters)
            count_df = pd.read_sql_query(count_sql,con=db.engine)
            result_count = count_df.to_dict('records')
            count_all_rows = result_count[0]['count_rows']

            return { 'count': count_result_rows, 'total':  count_all_rows  ,'data' : rows} 

        except exc.DatabaseError as err:
            # pass exception to function
            error_description = '%s' % (err)
            raise DatabaseException(text=error_description)


    def getByUsername(self,p_username):
        user = User.query.filter(User.name == p_username).first()
        if user is None:
            raise DataNotFoundException('User Not Found!')
        return user
    
    def deleteByUsername(self,p_username):
        user = self.getByUsername(p_username)        
        user.status = STATUS_INACTIVE

        db.session.add(user)
        db.session.commit()

        return user
    
    def getByUsernameAndType(self,p_username,p_type = REGULAR_USER):
        user = User.query.filter(User.name == p_username, User.type == p_type).first()
        if user is None:
            raise DataNotFoundException('User Not Found!')
        return user
    
    def deleteByUsernameAndType(self,p_username,p_type = REGULAR_USER):
        user = self.getByUsernameAndType(p_username,p_type)        
        user.status = STATUS_INACTIVE

        db.session.add(user)
        db.session.commit()

        return user
    
    def reactivateByUsernameAndType(self,p_username,p_type = REGULAR_USER):
        user = self.getByUsernameAndType(p_username,p_type)  

        if user.status != STATUS_INACTIVE:
            raise DataNotFoundException('Invalid User Status!')

        user.status = STATUS_PENDING
        confirmation_code = generate_numeric_password(6)
        user.operation_key = confirmation_code
        db.session.add(user)
        db.session.commit()

        # Enviar email para confirmar usuario
        destination = user.name
        first_name = user.person_extension.first_name
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

        return user
    
    def dropByUsername(self,p_username):
        user = self.getByUsername(p_username)

        db.session.delete(user)
        db.session.commit()

        return user

    def get_roles(self,payload):
        roles_list = []
        if 'roles' in payload:
            ids_roles = payload['roles']
            roles_list = Rol.query.filter(Rol.id.in_(ids_roles)).all()
        return roles_list

    def new(self,payload, user_type = REGULAR_USER):
        username = payload['email'].lower() if 'email' in payload else None

        if username:
            #Se chequea que el usuario NO exista previamente 
            user = User.query.filter(User.name == username).first()
            if not user is None:
                #Se arroja excepcion, el usuario ya esta creado
                raise DataAlreadyRegisteredException('Email is Registered!')

            confirmation_code = generate_numeric_password(6)

            user = User()
            user.name = username
            user.register_date = datetime.datetime.now()
            user.operation_key = confirmation_code
            user.status = STATUS_PENDING
            user.register_mode = FROM_BACKOFFICE
            user.type = user_type

            first_name =  payload['first_name'] if 'first_name' in payload else ''
            last_name =  payload['last_name'] if 'last_name' in payload else ''

            user.person_extension = PersonExtension()
            user.person_extension.email = username
            user.person_extension.first_name = first_name
            user.person_extension.last_name = last_name
            user.person_extension.fullname =  first_name + ' ' + last_name
            user.person_extension.phone_number = '#' # phone_number
            user.person_extension.gender = '-' # gender
            user.person_extension.birth_date = datetime.date.today() # birth_date
            user.person_extension.status = STATUS_ACTIVE

            #Se procesan los Roles del Usuario
            roles = self.get_roles(payload) 
            if len(roles):
                user.roles = [r for r in roles]

            db.session.add(user)
            db.session.commit()

            # Enviar email para confirmar usuario
            destination = username

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

            return user

        else:
            #No se proporciono el username o la contrasena, es obligatorio 
            raise ParametersNotFoundException('El nombre de usuario es obligatorio')

    def save(self,payload):
        username = payload['name'] if 'name' in payload else None
        password = payload['password'] if 'password' in payload else None         

        if username:
            #Se chequea que el usuario NO exista previamente 
            user = User.query.filter(User.name == username).first()
            if user is None:
                #Se arroja excepcion, el usuario ya esta creado
                raise DataNotFoundException()

            if not password:
                raise ParametersNotFoundException('Debe proporcionar una contrasena de Usuario')

            user.hash_password(password)
            user.register_date = datetime.datetime.now() 

            user.status = STATUS_ACTIVE
            user.register_mode = FROM_BACKOFFICE
            user.type = CONSOLE_USER

            #Se Verifica si el usuario es un trabajador asociado a RH
            if 'extra_info' in payload:
                id_number = payload['extra_info']['id_number'] if 'id_number' in payload['extra_info'] else ''
                first_name =  payload['extra_info']['first_name'] if 'first_name' in payload['extra_info'] else ''
                last_name =  payload['extra_info']['last_name'] if 'last_name' in payload['extra_info'] else ''
                phone_number =  payload['extra_info']['phone_number'] if 'phone_number' in payload['extra_info'] else ''
                gender =  payload['extra_info']['gender'] if 'gender' in payload['extra_info'] else ''
                email =  payload['extra_info']['email'] if 'email' in payload['extra_info'] else ''

                # Actualizar la empresa si viniera en el Payload / Esto es Opcional
                if 'empresa' in payload['extra_info'] \
                    and 'codigo' in payload['extra_info']['empresa'] :
                    empresa_id = payload['extra_info']['empresa']['codigo']
                    empresa = Empresa.query.filter(Empresa.codigo == empresa_id).first()
                    if not empresa is None:
                        user.person_extension.empresa_id = empresa_id
                    else:
                        user.person_extension.empresa_id = None

               
                user.person_extension.id_number = id_number
                user.person_extension.first_name = first_name
                user.person_extension.last_name = last_name
                user.person_extension.fullname =  first_name + ' ' + last_name
                user.person_extension.phone_number = phone_number
                user.person_extension.email = email
                user.person_extension.gender = gender

            #Se procesan los Roles del Usuario
            roles = self.get_roles(payload) 
            if len(roles):
                user.roles = [r for r in roles] 
            
            db.session.add(user)
            db.session.commit()            
        else:
            #No se proporciono el username o la contrasena, es obligatorio 
            raise ParametersNotFoundException()

    def update(self,payload):
        username = payload['email'].lower() if 'email' in payload else None
        user_type = payload['user_type'] if 'user_type' in payload else REGULAR_USER

        if username:
            #Se chequea que el usuario exista previamente 
            user = self.getByUsernameAndType(username, user_type)

            first_name =  payload['first_name'] if 'first_name' in payload else ''
            last_name =  payload['last_name'] if 'last_name' in payload else ''

            user.person_extension.first_name = first_name
            user.person_extension.last_name = last_name
            user.person_extension.fullname =  first_name + ' ' + last_name

            #Se procesan los Roles del Usuario
            roles = self.get_roles(payload) 
            if len(roles):
                user.roles = [r for r in roles] 
            
            db.session.add(user)
            db.session.commit()

            return user          
        else:
            #No se proporciono el username, es obligatorio 
            raise ParametersNotFoundException('El nombre de usuario es obligatorio')
        
    def sendInvite(self,payload):
        username = payload['email'].lower() if 'email' in payload else None
        user_type = payload['user_type'] if 'user_type' in payload else REGULAR_USER

        if username:
            #Se chequea que el usuario NO exista previamente 
            user = self.getByUsernameAndType(username, user_type)

            if user.status != STATUS_PENDING:
                raise DataNotFoundException('Invalid User Status!')

            confirmation_code = generate_numeric_password(6)

            user.operation_key = confirmation_code

            db.session.add(user)
            db.session.commit()

            # Enviar email para confirmar usuario
            destination = username
            first_name = user.person_extension.first_name

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

            return user

        else:
            #No se proporciono el username o la contrasena, es obligatorio 
            raise ParametersNotFoundException('El nombre de usuario es obligatorio')
        
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
            password:
                type: string
                empty: False
                minlength: 6
                required: True
            confirm_password:
                type: string
                empty: False
                minlength: 6
                required: True
        '''

        schema = yaml.safe_load(schema_text)
        v  = Validator()

        validation_result = v.validate(data, schema)

        if not validation_result:
            raise IncorrectValidationException(v.errors)
        
        if data['password'] != data['confirm_password']:
            raise IncorrectValidationException('Password does not match!')


        user = self.getByUsername(data['email'])
    
        if user is not None:

            confirmation_code = data['confirmation_code']
            password = data['password']
            if user.status == STATUS_PENDING:
                if user.operation_key == confirmation_code:
                    user.hash_password(password)
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

class RolRepository(SinergiaRepository):

    def get_privileges(self,payload):
        privileges_list = []
        if 'privileges' in payload:
            ids_privileges = payload['privileges']
            privileges_list = Privilege.query.filter(Privilege.name.in_(ids_privileges)).all()
        return privileges_list    

    def get(self,query_params):
        if _is_root(self.username):
            rows = Rol.query.order_by(Rol.id).all()
        else:
            rows = Rol.query.filter(Rol.id_name != ROLE_HILUCA_ADMIN).order_by(Rol.id).all()

        count_result_rows = len(rows)
        count_all_rows = Rol.query.count()
        return { 'count': count_result_rows, 'total':  count_all_rows  ,'data' : rows} 

    def save(self,payload):
        rol_name = payload['name'] if 'name' in payload else None
        if rol_name:
            rol = Rol.query.filter(Rol.name == rol_name).first()
            if rol is None:
                raise DataNotFoundException() 

            privileges = self.get_privileges(payload)
            if len(privileges):
                rol.privileges = [p for p in privileges] 

            db.session.add(rol)
            db.session.commit()
        else:
            raise DataNotFoundException()
        
    def getById(self, role_id):
        role = Rol.query.filter(Rol.id == role_id).first()
        if role is None:
            raise DataNotFoundException('Role Not Found!')
        
        for function in role.functions:
            rows = db.session.execute(select(function_rol_table.c)
                                      .where(function_rol_table.c.function_id == function.id)
                                      .where( function_rol_table.c.rol_id == role.id))
            for row in rows:
                function.actions = row.actions

        return {'data': role}

def _is_root(username):
    cacheRepository = CacheRepository()
    stored_data = cacheRepository.getByKey(f"{username}{SUFFIX_PERMISSION}")
    
    if not stored_data:
        return False
    
    for p in stored_data:
        if p['rol_long_name'] == ROLE_HILUCA_ADMIN:
            return True  
    
    return False
