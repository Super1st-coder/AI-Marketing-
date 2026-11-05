'''
Created on 19 ene. 2020

@author: ramon
'''
from datetime import datetime
# current date and time

now = datetime.now()
timestamp = datetime.timestamp(now)
print("timestamp =", timestamp)