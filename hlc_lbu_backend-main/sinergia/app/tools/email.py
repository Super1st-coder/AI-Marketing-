import sendgrid
import urllib
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import *
from config import config
import os

config_type = os.environ['CONFIG_TYPE']

def personalize_mail(destination,params):
    emails = [destination]
    personalization = Personalization()
    params['destination'] = destination
    template_data = params
    personalization.dynamic_template_data = template_data    

    for email in emails:
      personalization.add_to(Email(email))

    return personalization

from python_http_client.exceptions import HTTPError

def send_mail(template_id,destination,params):
    try:
        SENDGRID_API_KEY = config[config_type].SENDGRID_API_KEY    
        sg = sendgrid.SendGridAPIClient(SENDGRID_API_KEY)

        mail = Mail()

        mail.from_email = Email(config[config_type].EMAIL_FROM)
        mail.template_id = template_id 
        mail.add_personalization(personalize_mail(destination,params))

        response = sg.client.mail.send.post(request_body=mail.get())
    except urllib.error.HTTPError as e:
        print(e)
    except HTTPError as e:
        print(e.to_dict)        
    except Exception as ex:
        print(ex)

def send_account_confirmation_mail(destination,params):
    ACCOUNT_CONFIRMATION_TEMPLATE = config[config_type].ACCOUNT_CONFIRMATION_TEMPLATE
    send_mail(ACCOUNT_CONFIRMATION_TEMPLATE,destination,params)

def send_reset_password_mail(destination,params):
    RESET_PASSWORD_TEMPLATE = config[config_type].RESET_PASSWORD_TEMPLATE
    send_mail(RESET_PASSWORD_TEMPLATE,destination,params)

