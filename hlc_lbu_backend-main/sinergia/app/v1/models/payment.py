'''
Created on 17 dic. 2019

@author: ramon
'''
from app import db
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship, backref
from sqlalchemy import Table, Column, ForeignKey, Integer, String, Float, Boolean, DateTime, Text
import datetime

from app.v1.models.constant import STATUS_ACTIVE


class Bank(db.Model):
    __tablename__ = 'bank'
    __table_args__ = {'schema' : 'public'}

    id = Column(Integer, primary_key=True)
    name =  Column(String(150))
    status = Column(String(1))

class Application(db.Model):
    __tablename__ = 'application'
    id = Column(Integer, primary_key=True)
    name = Column(String(50))
    app_key = Column(String(64))
    app_iv  = Column(String(64))
    status = Column(String(1), default = STATUS_ACTIVE)

    default_fiat_coin_id = Column(Integer, ForeignKey('coin.id'))
    default_fiat_coin = relationship("Coin", foreign_keys="Application.default_fiat_coin_id")
    
    default_crypto_coin_id = Column(Integer, ForeignKey('coin.id'))
    default_crypto_coin = relationship("Coin", foreign_keys="Application.default_crypto_coin_id")
    
class Coin(db.Model):
    __tablename__ = 'coin'
    id = Column(Integer, primary_key=True)
    name = Column(String(50))
    description = Column(String(128))
    creation_date = Column(DateTime, default=datetime.datetime.now())
    diminutive = Column(String(5))
    th_separator = Column(String(1))
    dec_separator = Column(String(1))
    status = Column(String(1), default = STATUS_ACTIVE)
    
    blockchain_address = Column(String(128))
    
    application_id = Column(Integer, ForeignKey('application.id'))
    application  = relationship("Application", foreign_keys="Coin.application_id")