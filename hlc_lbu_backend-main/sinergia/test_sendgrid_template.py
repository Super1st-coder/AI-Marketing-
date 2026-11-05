
'''
Created on 12 nov. 2019

@author: ramon
'''
import json
import os
import sendgrid
import urllib
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import *
import urllib

SENDGRID_APIKEY = 'SENDGRID_API_KEY_REDACTED'
sg = sendgrid.SendGridAPIClient(SENDGRID_APIKEY)
  
def personalize():
    emails = ["valera.ramon@gmail.com"]
    personalization = Personalization()
    template_data = {
        "confirmation_code": "1234-5678-9022",
    }
    personalization.dynamic_template_data = template_data    

    for email in emails:
      personalization.add_to(Email(email))
    return personalization

def main():
    mail = Mail()
    mail.from_email = Email("valera.ramon@gmail.com")
    mail.template_id = "d-ed0c72bca2e6455db05fac1142322338"
    mail.add_personalization(personalize())
    
    try:
        response = sg.client.mail.send.post(request_body=mail.get())
        print(response.status_code)
        print(response.body)
        print(response.headers)                
    except urllib.error.HTTPError as e:
        print(e)
    except Exception as ex:
        print(ex)


if __name__ == '__main__':
    main()
    
