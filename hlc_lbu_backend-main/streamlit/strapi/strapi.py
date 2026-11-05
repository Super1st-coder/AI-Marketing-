import requests
import json


#TODO: Create a configuration file to store this
strapi_token = "6f4220aaf118063910dc6089f5b9276e323311555060c9cdbbf907ae04c8d722fd94034f915630d6247a05f1b3c6ad32dd5dfd081461f2e72f14f09b9d2b5625ef9498934702621ae12de383e0ae47e74776c693e236b8467de04a162e819e6cb4059669f47d3aa44735166a20462fcf76706b9ec2bcbe7fc8e59c50a71f4f1d"
# Define the base URL of your Strapi server
base_url = "http://localhost:1337/api"

headers = {"Authorization": f"Bearer {strapi_token}","Content-Type": "application/json",'accept': 'application/json' }

def get_content_type_attributes(content_type_name):
    # Endpoint to get attributes of a particular content type
    url = f"{base_url}/content-type-builder/content-types/api::{content_type_name}.{content_type_name}"

    # Make a GET request to retrieve the attributes
    response = requests.get(url,headers=headers)
    
    # Check if the request was successful
    if response.status_code == 200:
        attributes = response.json()
        return attributes['data']['schema']['attributes']
    else:
        print(f"Failed to retrieve attributes for {content_type_name}. Status code: {response.status_code}")
        print(response.text)
        return None

def get_objects(content_type_name,filter):
    url = f"{base_url}/{content_type_name}"
    
    # Make a GET request to create the object
    response = requests.get(url,headers=headers,params={"filter" : filter, 'populate' : '*' })
    
    # Check if the request was successful
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to Fetch object. Status code: {response.status_code}")
        print(response.text)
        return None

def get_object_by_field(content_type_name,field_name,field_value):
    # Endpoint to create an object of a particular content type
    url = f"{base_url}/{content_type_name}"
    
    # Make a GET request to create the object
    # filters[username][$eq]
    field_name = 'project_ref'
    response = requests.get(url,headers=headers,params={f"filters[{field_name}][$eq]" :  field_value , 'populate' : '*' } )
    # response = requests.get(url,headers=headers,params={ "filters" :  [ { field_name : {  '$eq' :  field_value } } ]  , 'populate' : '*' } )
    
    print(response.request.url) 

    # Check if the request was successful
    if response.status_code == 200:
        result = response.json()
        val = None
        if not result is None:
            if 'data' in result and len(result['data']) > 0:
                val =  result['data'][0]
        return val
    else:
        print(f"Failed to Fetch object. Status code: {response.status_code}")
        print(response.text)
        return None

def get_object_by_id(content_type_name,id):
    result = get_object_by_field(content_type_name,'id',id)
    return result

def create_object(content_type_name, data):
    # Endpoint to create an object of a particular content type
    url = f"{base_url}/{content_type_name}"
    
    # Make a POST request to create the object
    response = requests.post(url,headers=headers,json=data)
    
    # Check if the request was successful
    if response.status_code == 201:
        print("Object created successfully.")
        return response.json()
    else:
        print(f"Failed to create object. Status code: {response.status_code}")
        return None

# Example usage
if __name__ == "__main__":
    # content_type_name = 'b2c-project-surveys'
    # content = get_object_by_id(content_type_name,1)
    # print(content)

    # content_type_name = 'account'
    # account = get_object_by_field(content_type_name,'email','ramon.valera@gmail.com')
    # print(account)

    content_type_name = 'b2c-project-surveys'
    survey = get_object_by_field(content_type_name,'project_ref','4')

    # print(survey)

    # content_type_name = "b2c-project-survey"  
    # attributes = get_content_type_attributes(content_type_name)
    # if attributes:
    #     print(json.dumps(attributes,indent=4))
