'''
Created on 17 dic. 2019

@author: ramon
'''
from datetime import datetime
from app import db
from flask_sqlalchemy.model import Model
from sqlalchemy import Table, Column, ForeignKey, Integer, String, Float, Boolean, DateTime, Text, Date
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship, backref
from passlib.apps import custom_app_context as pwd_context
from itsdangerous import (TimedJSONWebSignatureSerializer
                          as Serializer, BadSignature, SignatureExpired)
import hashlib
from app.v1.models.constant import STATUS_ACTIVE, configuration
from app.v1.models.payment import Bank


securityelement_rol_table = Table('securityelement_rol', db.Model.metadata,
    Column('securityelement_id', Integer, ForeignKey('public.securityelement.id')),
    Column('rol_id', Integer, ForeignKey('public.rol.id'))
)

rol_privilege_table = Table('rol_privilege', db.Model.metadata,
    Column('rol_id', Integer, ForeignKey('public.rol.id')),
    Column('privilege_id', Integer, ForeignKey('public.privilege.id'))
)    

function_rol_table = Table('function_rol', db.Model.metadata,
    Column('rol_id', Integer, ForeignKey('public.rol.id')),
    Column('function_id', Integer, ForeignKey('public.function.id')),
    Column('actions', JSONB)
)


class Privilege(db.Model):
    __tablename__ = 'privilege'
    __table_args__ = {'schema' : 'public'}

    id = Column(Integer, primary_key=True)
    short_name = Column(String(5), unique=True)
    name = Column(String(32))
        

class Function(db.Model):
    __tablename__ = 'function'
    __table_args__ = {'schema' : 'public'}

    id = Column(Integer, primary_key=True)
    name = Column(String(50))
    long_name = Column(String(100))
    link = Column(String(50))
    icon = Column(String(50))
    is_container = Column(Boolean, default=False)
    parent_id = Column(Integer, ForeignKey('public.function.id'))
    order = Column(Integer())
    children = relationship("Function")
    status = Column(String(1))


class Rol(db.Model):
    __tablename__ = 'rol'
    __table_args__ = {'schema' : 'public'}

    id = Column(Integer, primary_key=True)
    name = Column(String(32))
    id_name = Column(String(32))
    status = Column(String(1))
    icon = Column(String(32))
    privileges = relationship("Privilege", secondary=rol_privilege_table)
    functions = relationship("Function", secondary=function_rol_table)


class PersonExtension(db.Model):
    __tablename__ = 'personextension'
    __table_args__ = {'schema' : 'public'}

    id = Column(Integer, primary_key=True)
    type = Column(String(1))   
    id_number = Column(String(25))
    first_name = Column(String(100))
    last_name = Column(String(100))
    fullname = Column(String(100))
    birth_date = Column(DateTime)
    gender = Column(String(1))
    address = Column(String(250)) 
    phone_number = Column(String(25))
    email = Column(String(128))
    secondary_email = Column(String(128))
    
    bank_id = Column(Integer, ForeignKey('public.bank.id'))
    bank = relationship("Bank")
    
    account_number = Column(String(50))
    status = Column(String(1))

    #Modificacion realizada para asociar un usuario con la empresa / Es posible que el usuario no tenga empresa asociada
    empresa_id = Column('empresa_id',String(10), ForeignKey('business.empresa.codigo'))
    empresa = relationship("Empresa")

    __mapper_args__ = {
        'polymorphic_identity':'personextension'
    }

class SecurityElement(db.Model):
    __tablename__ = 'securityelement'
    __table_args__ = {'schema' : 'public'}
    
    id = Column(Integer, primary_key=True)

    name = Column(String(128), unique=True)
    password_hash = Column(String(128))

    roles = relationship("Rol", secondary=securityelement_rol_table,cascade="save-update")                                    
    
    status = Column(String(1), default=STATUS_ACTIVE)

    def hash_password(self, password):
        self.password_hash = pwd_context.encrypt(password)

    def verify_password(self, password):
        return pwd_context.verify(password, self.password_hash)

    def generate_auth_token(self, expiration=86400):
        s = Serializer(configuration.get('SECURITY', 'SECRET_KEY'), expires_in=expiration)
        return s.dumps({'id': self.id})
    
    discriminator = Column(String)

    __mapper_args__ = {
        'polymorphic_on':'discriminator',
    }    

    @staticmethod
    def verify_auth_token(token):
        s = Serializer(configuration.get('SECURITY', 'SECRET_KEY'))
        try:
            data = s.loads(token)
        except SignatureExpired:
            return None  # valid token, but expired
        except BadSignature:
            return None  # invalid token
        element = SecurityElement.query.get(data['id'])
        return element
    
class User(SecurityElement):
    __tablename__ = 'user'
    __table_args__ = {'schema' : 'public'}

    id = Column(Integer, ForeignKey('public.securityelement.id'), primary_key=True)
    
    person_extension_id = Column(Integer, ForeignKey('public.personextension.id'))
    person_extension = relationship("PersonExtension",cascade="all,delete")
    
    operation_key = Column(String(128))
    register_mode = Column(String(1))
    register_date = Column(DateTime)
    type = Column(String(1))

    def hash_operation_key(self, operation_key):
        self.operation_key = hashlib.md5(operation_key).hexdigest()

    def verify_operation_key(self, operation_key):
        return hashlib.md5(operation_key).hexdigest() == self.operation_key

    __mapper_args__ = {
        'polymorphic_identity':'user'
    }
    
class Device(SecurityElement):
    __tablename__ = 'device'
    __table_args__ = {'schema' : 'public'}

    id = Column(Integer, ForeignKey('public.securityelement.id'), primary_key=True)

    serial = Column(String(128))
    serial2 = Column(String(128))
    
    __mapper_args__ = {
        'polymorphic_identity':'device'
    }

