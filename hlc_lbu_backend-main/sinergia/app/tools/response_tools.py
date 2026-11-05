from flask.helpers import make_response
from flask import render_template

def make_template_response(response_data, template_name):
    response = make_response()
    response.content_type = 'application/json'
    response.data = render_template(template_name, data=response_data, mimetype='application/json') 
    return response
