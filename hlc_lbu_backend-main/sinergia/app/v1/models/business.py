'''
Created on 17 dic. 2019

@author: ramon
'''

from app import db
from flask_sqlalchemy.model import Model
from sqlalchemy import Table, Column, ForeignKey, Integer, String, Float, Boolean, DateTime, Text, Date
from sqlalchemy.orm import relationship, backref


class Empresa(db.Model):
    __tablename__ = 'empresa'
    __table_args__ = {'schema' : 'business'}

    codigo = Column(String(10), primary_key=True)
    nombre = Column(String(100)) 

