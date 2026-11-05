import requests
import json
import os
import streamlit as st

class StrapiRepository :

    # strapi_token = "6f4220aaf118063910dc6089f5b9276e323311555060c9cdbbf907ae04c8d722fd94034f915630d6247a05f1b3c6ad32dd5dfd081461f2e72f14f09b9d2b5625ef9498934702621ae12de383e0ae47e74776c693e236b8467de04a162e819e6cb4059669f47d3aa44735166a20462fcf76706b9ec2bcbe7fc8e59c50a71f4f1d"
    # strapi_token = "88f064fddabb4898812d9ec0fb96443228c5198cd890b7bcbd87ca0a6c6de3950770eec38ad97f4503ce43f30912947784657e337a998e116521145f63fd136da52429b02d5381ee32b14ea7e5817f57fae166596fa21246106d9bb85f9bbd444d68f435f7e17c9e2b056811de95f460d159518c5bd4f1d3636460e898e48511"
    strapi_token = os.environ['STRAPI_TOKEN'] if st.secrets["STRAPI_TOKEN"] is None else st.secrets["STRAPI_TOKEN"]

    base_url = f"http://{os.environ['STRAPI_HOST']}:{os.environ['STRAPI_PORT']}/api"
    headers = {"Authorization": f"Bearer {strapi_token}","Content-Type": "application/json",'accept': 'application/json' }

    def get_objects(self,content_type_name,filter):

        url = f"{self.base_url}/{content_type_name}"
        
        # Make a GET request to create the object
        field_name = next(iter(filter))
        filter_value = filter[field_name]

        filter_expression = f"filters[{field_name}][$eq]"

        response = requests.get(url,headers=self.headers,params={filter_expression : filter_value , 'populate' : '*' })
        
        # Check if the request was successful
        if response.status_code == 200:
            result = response.json()
            val = None
            if not result is None:
                if 'data' in result and len(result['data']) > 0:
                    val =  result['data']
            return val
        else:
            print(f"Failed to Fetch object. Status code: {response.status_code}")
            print(response.text)
            return None

    def get_objects_by_field(self,content_type_name,field_name,field_value):
        result = self.get_objects( content_type_name, { field_name : field_value} )
        return result

    def get_object_by_id(self,content_type_name,id):
        result = self.get_objects_by_field(content_type_name,'id',id)
        return result[0] if not result is None and len(result) > 0 else None

    def create_object(self,content_type_name, data):
        # Endpoint to create an object of a particular content type
        url = f"{self.base_url}/{content_type_name}"
        
        # Make a POST request to create the object
        response = requests.post(url,headers=self.headers,json=data)
        
        # Check if the request was successful
        if response.status_code == 200:
            print("Object created successfully.")
            return response.json()
        else:
            print(f"Failed to create object. Status code: {response.status_code}")
            print(response.text)
            return None

    def update_object(self,content_type_name, id, data):
        # Endpoint to create an object of a particular content type
        url = f"{self.base_url}/{content_type_name}/{id}"
        
        # Make a POST request to create the object
        response = requests.put(url,headers=self.headers,json=data)
        
        # Check if the request was successful
        if response.status_code == 200:
            print("Object created successfully.")
            return response.json()
        else:
            print(f"Failed to update object. Status code: {response.status_code}")
            print(response.text)
            return None


    def get_content_type_attributes(self,content_type_name):
        # Endpoint to get attributes of a particular content type
        url = f"{self.base_url}/content-type-builder/content-types/api::{content_type_name}.{content_type_name}"

        # Make a GET request to retrieve the attributes
        response = requests.get(url,headers=self.headers)
        
        # Check if the request was successful
        if response.status_code == 200:
            attributes = response.json()
            return attributes['data']['schema']['attributes']
        else:
            print(f"Failed to retrieve attributes for {content_type_name}. Status code: {response.status_code}")
            return None
    
    def generate_new_object(self,content_type_name):
        new_object = None
        generated_object = self.get_content_type_attributes(content_type_name)
        if not generated_object  is None:
            empty_object = {}
            for key, value in generated_object.items():
                default_value = ''
                if 'default' in value:
                    default_value = value['default']
                empty_object[key] = default_value
            new_object = empty_object
        return new_object
    

class SinergiaRepository :

    base_url = f"http://{os.environ['SINERGIA_HOST']}:{os.environ['SINERGIA_PORT']}/api/v1"
    # headers = {"Content-Type": "application/json",'accept': 'application/json',"Authorization": f"Bearer {sinergia_token}" }
    headers = {"Content-Type": "application/json",'accept': 'application/json' }

    def login(self, username, password):


        endpoint_path = '/member/login'
        url = f'{self.base_url}{endpoint_path}'

        print(url)

        data = {'username' : username, 'password' : password}

        response = requests.post(url,headers=self.headers,json=data)
        print(response.text)

        user_credentials = None
        
        # Check if the request was successful
        if response.status_code == 200:
            json_response = response.json()

            ok = json_response['ok']
            if ok == 1:
                user_credentials = json_response['data']
            else:
                # Error en el acceso al token 
                print("Failed in User Credentials:")
        else:
            print(f"Failed to Authenticate. Status code: {response.status_code}")
            print(f"Response text: {response.text}")

        return user_credentials
    
    def register(self, email, first_name, last_name, password):
        endpoint_path = '/member/signup'
        url = f'{self.base_url}{endpoint_path}'

        data = {'email' : email,  'first_name' : first_name, 'last_name' : last_name, 'password' : password}

        response = requests.post(url,headers=self.headers,json=data)

        user_registered = False
        
        # Check if the request was successful
        if response.status_code == 200:
            json_response = response.json()

            ok = json_response['ok']
            if ok == 1:
                user_registered = True
            else:
                # Error en el acceso al token 
                print("Failed in User Credentials:")
        else:
            print(f"Failed to Register. Status code: {response.status_code}")
            print(f"Response text: {response.text}")

        return user_registered

    def confirm_account(self,email,confirmation_code):
        endpoint_path = '/member/signup/finish'
        url = f'{self.base_url}{endpoint_path}'

        data = {'email' : email,  'confirmation_code' : confirmation_code }

        response = requests.put(url,headers=self.headers,json=data)

        confirmed_account = False
        
        # Check if the request was successful
        if response.status_code == 200:
            json_response = response.json()

            ok = json_response['ok']
            if ok == 1:
                confirmed_account = True
            else:
                # Error en el acceso al token 
                print("Failed in Account Confirmation:")
        else:
            print(f"Failed to Register. Status code: {response.status_code}")
            print(f"Response text: {response.text}")

        return confirmed_account


    def init_reset_password(self,email):
        endpoint_path = '/member/password/reset'
        url = f'{self.base_url}{endpoint_path}'

        data = {'email' : email }

        response = requests.post(url,headers=self.headers,json=data)

        action_confirmed = False
        
        # Check if the request was successful
        if response.status_code == 200:
            json_response = response.json()

            ok = json_response['ok']
            if ok == 1:
                action_confirmed = True
            else:
                # Error en el acceso al token 
                print("Failed in Account Confirmation:")
        else:
            print(f"Failed to Register. Status code: {response.status_code}")
            print(f"Response text: {response.text}")

        return action_confirmed

    def change_password(self,email,confirmation_code,new_password):
        endpoint_path = '/member/password/reset/finish'
        url = f'{self.base_url}{endpoint_path}'

        data = {'email' : email, 'confirmation_code' : confirmation_code, 'new_password' : new_password }

        response = requests.put(url,headers=self.headers,json=data)

        action_confirmed = False
        
        # Check if the request was successful
        if response.status_code == 200:
            json_response = response.json()

            ok = json_response['ok']
            if ok == 1:
                action_confirmed = True
            else:
                # Error en el acceso al token 
                print("Failed in Account Confirmation:")
        else:
            print(f"Failed to Register. Status code: {response.status_code}")
            print(f"Response text: {response.text}")

        return action_confirmed
    
class N8NClient :

    base_url = f"http://{os.environ['N8N_HOST']}:{os.environ['N8N_PORT']}"
    headers = {"Content-Type": "application/json",'accept': 'application/json' }

    def create_agent(self,name,definition):
        endpoint_path = '/webhook/project-agent'
        url = f'{self.base_url}{endpoint_path}'

        data = {'name' : name,  'definition' : definition}


        response = requests.post(url,headers=self.headers,json=data)

        json_response = None
        # Check if the request was successful
        if response.status_code == 200:
            json_response = response.json()
            ok = json_response['ok']
            if ok == 0:
                # print(json_response)
                json_response = None
        else:
            print(f"Failed to Create Agent. Status code: {response.status_code}")
            print(f"Response text: {response.text}")

        return json_response
    
    def delete_agent(self,id):
        endpoint_path = '/webhook/project-agent'
        url = f'{self.base_url}{endpoint_path}'

        params = {'id' : id}

        response = requests.delete(url,headers=self.headers,params=params)

        execute_action = False
        # Check if the request was successful
        if response.status_code == 200:
            
            json_response = response.json()
            ok = json_response['ok']
            if ok == 1:
                execute_action = True 
            else:
                print("Error Deleting Project Agent")
        else:
            print(f"Failed to Delete Agent. Status code: {response.status_code}")
            print(f"Response text: {response.text}")

        return execute_action
    
    def get_system_agents(self):
        endpoint_path = '/webhook/project-agent'
        url = f'{self.base_url}{endpoint_path}'

        response = requests.get(url,headers=self.headers)

        agent_list = []
        # Check if the request was successful
        if response.status_code == 200:            
            json_response = response.json()
            ok = json_response['ok']
            if ok == 1:
                agent_list = json_response['data'] 
            else:
                print("Error Getting Project Agents")
        else:
            print(f"Failed to Get Agents. Status code: {response.status_code}")
            print(f"Response text: {response.text}")

        return agent_list    

    def generate_initial_bperson(self, agent_id, agent_name, entity_name ):
        endpoint_path = '/webhook/project-agent/bperson/generate'
        url = f'{self.base_url}{endpoint_path}'

        data = {'agent_id' : agent_id,  'agent_name' : agent_name, 'entity_name' : entity_name}
        response = requests.post(url,headers=self.headers,json=data)

        new_json_response = None
        # Check if the request was successful
        if response.status_code == 200:
            json_response = response.json()

            # print(json_response)
            # print('---------------------------------------------------------')                    
            if 'ok' in json_response:
                ok = json_response['ok']
                if ok == 1:
                    new_json_response = json.loads(json_response['data'],strict=False)
                    # print(new_json_response)                    
                    # print('---------------------------------------------------------')                    
        else:
            print(f"Failed to Generate Content. Status code: {response.status_code}")
            print(f"Response text: {response.text}")

        return new_json_response
    
    def generate_consultor(self, current_project, person_name, promptBPerson, product_name, promptProductoSurvey ):
        endpoint_path =  '/webhook/project-agent/consultor/generate'  
        url = f'{self.base_url}{endpoint_path}'

        print(url)

        data = {  'prompt_product' : promptProductoSurvey 
                , 'prompt_bperson' :  promptBPerson 
                , 'product_name' : product_name  
                , 'person_name' : person_name }
        response = requests.post(url,headers=self.headers,json=data)

        new_json_response = None
        # Check if the request was successful
        if response.status_code == 200:
            json_response = response.json()

            # print(json_response)
            # print('---------------------------------------------------------')                    
            if 'ok' in json_response:
                ok = json_response['ok']
                if ok == 1:
                    new_json_response = json.loads(json_response['data'],strict=False)
                    # print(new_json_response)                    
                    # print('---------------------------------------------------------')                    
        else:
            print(f"Failed to Generate Content. Status code: {response.status_code}")
            print(f"Response text: {response.text}")

        return new_json_response


    def generate_new_bpersons_using_another(self, agent_id, agent_name, variation_name,variation_text):
        endpoint_path = '/webhook/project-agent/bperson/generate-variation'
        url = f'{self.base_url}{endpoint_path}'

        data = {'agent_id' : agent_id,  'agent_name' : agent_name, 'variation_name' : variation_name, 'variation_text' : variation_text}
        response = requests.post(url,headers=self.headers,json=data)

        new_json_response = None
        # Check if the request was successful
        if response.status_code == 200:
            json_response = response.json()

            # print(json_response)
            # print('---------------------------------------------------------')                    
            if 'ok' in json_response:
                ok = json_response['ok']
                if ok == 1:
                    new_json_response = json.loads(json_response['data'],strict=False)

                    # print(new_json_response)                    
                    # print('---------------------------------------------------------')                    
        else:
            print(f"Failed to Generate Content. Status code: {response.status_code}")
            print(f"Response text: {response.text}")

        return new_json_response


    def improve_bperson_description(self, agent_id, agent_name, bperson_name, previous_description, proposal_description):
        endpoint_path = '/webhook/project-agent/bperson/improve'
        url = f'{self.base_url}{endpoint_path}'

        data = {'agent_id' : agent_id,  'agent_name' : agent_name, 'entity_name': bperson_name, 'original_text' : previous_description, 'updated_text' : proposal_description}
        response = requests.post(url,headers=self.headers,json=data)

        new_json_response = None
        # Check if the request was successful
        if response.status_code == 200:
            json_response = response.json()

            # print(json_response)
            # print('---------------------------------------------------------')                    
            if 'ok' in json_response:
                ok = json_response['ok']
                if ok == 1:
                    new_json_response = json.loads(json_response['data'],strict=False)

                    # print(new_json_response)
                    # print('---------------------------------------------------------')                    


        else:
            print(f"Failed to Improve Content. Status code: {response.status_code}")
            print(f"Response text: {response.text}")

        return new_json_response
    
    def generate_scenarios(self,agent_id,agent_name,person_name,product_name,sales_process_atributes):
        endpoint_path = '/webhook/project-agent/bperson/scenario/generate'
        url = f'{self.base_url}{endpoint_path}'

        data = {'agent_id' : agent_id,  'agent_name' : agent_name, 'person_name' : person_name, 'product_name' : product_name, 'sales_process' : sales_process_atributes }
        response = requests.post(url,headers=self.headers,json=data)

        new_json_response = None
        # Check if the request was successful
        if response.status_code == 200:
            json_response = response.json()

            # print(json_response)
            # print('---------------------------------------------------------')                    
            if 'ok' in json_response:
                ok = json_response['ok']
                if ok == 1:
                    new_json_response = json.loads(json_response['data'],strict=False)
        else:
            print(f"Failed to Generate Content. Status code: {response.status_code}")
            print(f"Response text: {response.text}")

        return new_json_response

    def improve_text(self,agent_id,agent_name,old_text,new_text):
        endpoint_path = '/webhook/project-agent/improve-text'
        url = f'{self.base_url}{endpoint_path}'

        data = {'agent_id' : agent_id,  'agent_name' : agent_name, 'old_text' : old_text, 'new_text' : new_text  }
        response = requests.post(url,headers=self.headers,json=data)

        new_json_response = None
        # Check if the request was successful
        if response.status_code == 200:
            json_response = response.json()

            print('------  J S O N     R E S P O N S E  ------')                    
            print(json_response)
            print('---------------------------------------------------------')                    
            if 'ok' in json_response:
                ok = json_response['ok']
                if ok == 1:
                    new_json_response = json.loads(json_response['data'],strict=False)
                    print('------  N E W    J S O N     R E S P O N S E  ------')                    
                    print(new_json_response)
                    print('---------------------------------------------------------')                    

        else:
            print(f"Failed to Generate Content. Status code: {response.status_code}")
            print(f"Response text: {response.text}")

        return new_json_response
    

    def generate_new_scenario_using_another(self, agent_id,agent_name,person_name,product_name,sales_process_attributes,scenario_attributes):
        endpoint_path = '/webhook/project-agent/bperson/scenario/improve'

        
        url = f'{self.base_url}{endpoint_path}'

        data = {'agent_id' : agent_id,  'agent_name' : agent_name, 'person_name' : person_name, 'product_name' : product_name, 'scenario_attributes' : scenario_attributes  }
        response = requests.post(url,headers=self.headers,json=data)

        new_json_response = None
        # Check if the request was successful
        if response.status_code == 200:
            json_response = response.json()

            # print('------  J S O N     R E S P O N S E  ------')                    
            # print(json_response)
            # print('---------------------------------------------------------')                    
            if 'ok' in json_response:
                ok = json_response['ok']
                if ok == 1:
                    new_json_response = json.loads(json_response['data'],strict=False)
                    # print('------  N E W    J S O N     R E S P O N S E  ------')                    
                    # print(new_json_response)
                    # print('---------------------------------------------------------')                    

        else:
            print(f"Failed to Generate Content. Status code: {response.status_code}")
            print(f"Response text: {response.text}")

        return new_json_response
    
    def generate_longtext_bperson(self,agent_id,agent_name,person_name,product_name,bperson_survey):
        endpoint_path = '/webhook/project-agent/bperson/long-text/generate'

        url = f'{self.base_url}{endpoint_path}'

        data = {'agent_id' : agent_id,  'agent_name' : agent_name, 'person_name' : person_name, 'product_name' : product_name, 'bperson_survey' : bperson_survey }
        response = requests.post(url,headers=self.headers,json=data)

        new_json_response = None
        # Check if the request was successful
        if response.status_code == 200:
            json_response = response.json()
            if 'ok' in json_response:
                ok = json_response['ok']
                if ok == 1:
                    new_json_response = json.loads(json_response['data'],strict=False)
        else:
            print(f"Failed to Generate Content. Status code: {response.status_code}")
            print(f"Response text: {response.text}")

        return new_json_response

    def generate_longtext_product(self,agent_id,agent_name,person_name,person_description,product_name):
        endpoint_path = '/webhook/project-agent/bperson/product/long-text/generate'

        url = f'{self.base_url}{endpoint_path}'

        data = {'agent_id' : agent_id,  
                'agent_name' : agent_name, 
                'person_name' : person_name, 
                'product_name' : product_name, 
                'person_description' : person_description }
        response = requests.post(url,headers=self.headers,json=data)

        new_json_response = None
        # Check if the request was successful
        if response.status_code == 200:
            json_response = response.json()
            if 'ok' in json_response:
                ok = json_response['ok']
                if ok == 1:
                    new_json_response = json.loads(json_response['data'],strict=False)
        else:
            print(f"Failed to Generate Content. Status code: {response.status_code}")
            print(f"Response text: {response.text}")

        return new_json_response

    def generate_scenario_contexts(self,agent_id,agent_name,person_name,person_description,product_name):
        endpoint_path = '/webhook/project-agent/bperson/context/generate'
        url = f'{self.base_url}{endpoint_path}'

        data = {'agent_id' : agent_id,  'agent_name' : agent_name, 'person_name' : person_name, 'person_description' : person_description, 'product_name' : product_name }
        response = requests.post(url,headers=self.headers,json=data)

        new_json_response = None
        # Check if the request was successful
        if response.status_code == 200:
            json_response = response.json()

            print(json_response)
            print('---------------------------------------------------------')                    
            if 'ok' in json_response:
                ok = json_response['ok']
                if ok == 1:
                    new_json_response = json.loads(json_response['data'],strict=False)

                    print(new_json_response)
                    print('---------------------------------------------------------')                    

        else:
            print(f"Failed to Generate Content. Status code: {response.status_code}")
            print(f"Response text: {response.text}")

        return new_json_response
    
    def generate_answer_sales_process(self,agent_id,agent_name,person_name,context_description,product_name):
        endpoint_path = '/webhook/project-agent/bperson/process-sales/autofill'
        url = f'{self.base_url}{endpoint_path}'

        data = {'agent_id' : agent_id,  'agent_name' : agent_name, 'person_name' : person_name, 'context_description' : context_description, 'product_name' : product_name }
        response = requests.post(url,headers=self.headers,json=data)

        new_json_response = None
        # Check if the request was successful
        if response.status_code == 200:
            json_response = response.json()

            print(json_response)
            print('---------------------------------------------------------')                    
            if 'ok' in json_response:
                ok = json_response['ok']
                if ok == 1:
                    new_json_response = json.loads(json_response['data'],strict=False)

                    print(new_json_response)
                    print('---------------------------------------------------------')                    

        else:
            print(f"Failed to Generate Content. Status code: {response.status_code}")
            print(f"Response text: {response.text}")

        return new_json_response


    def generate_scenario_activies(self,agent_id,agent_name,person_name,product_name,scenario_title,scenario_description):
        endpoint_path = '/webhook/project-agent/bperson/scenario/activity/generate'

        url = f'{self.base_url}{endpoint_path}'

        data = {'agent_id' : agent_id,  'agent_name' : agent_name, 'person_name' : person_name, 'product_name' : product_name, 'scenario_title' :  scenario_title, 'scenario_description' : scenario_description }
        
        response = requests.post(url,headers=self.headers,json=data)

        new_json_response = None
        # Check if the request was successful
        if response.status_code == 200:
            json_response = response.json()

            print(json_response)
            print('---------------------------------------------------------')                    
            if 'ok' in json_response:
                ok = json_response['ok']
                if ok == 1:
                    new_json_response = json.loads(json_response['data'],strict=False)

                    print(new_json_response)
                    print('---------------------------------------------------------')                    

        else:
            print(f"Failed to Generate Content. Status code: {response.status_code}")
            print(f"Response text: {response.text}")

        return new_json_response
