import base64
from hashlib import md5
import random

def encrypt_password(password):
    m = md5.new()
    m.update(password)
    encrypt_password = m.digest()
    base64_password = base64.b64encode(encrypt_password)
    return base64_password

def generate_password():
    s = "abcdefghijklmnopqrstuvwxyz01234567890ABCDEFGHIJKLMNOPQRSTUVWXYZ!@#$%&*()?"
    passlen = 8
    p =  "".join(random.sample(s,passlen ))
    return p

def generate_alphanumeric_password():
    s = "01234567890ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    passlen = 8
    p =  "".join(random.sample(s,passlen ))
    return p

def generate_numeric_password(passlen):
    s = "0123456789"
    p =  "".join(random.sample(s,passlen ))
    return p
