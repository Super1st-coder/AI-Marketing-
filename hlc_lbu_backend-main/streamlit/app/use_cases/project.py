from jinja2 import Environment, FileSystemLoader
import requests
import pandas as pd

from app.repository.marketing import ProjectRepository, BPersonaSurveyRepository,ProductoSurveyRepository, ConsultorSurveyRepository, BrandRepository
from app.repository.marketing import PromptRepository,AgentRepository, BPersonRepository, SalesProcessRepository, ScenarioRepository,ScenarioContextRepository,ScenarioActivityRepository, ProductRepository
from app.repository.marketing import ConsultorSuggestionRepository
from app.repository.base import N8NClient
import slugify

import json

import math
import numpy as np


class PromptManager :

    promptRepository = PromptRepository()
    environment = Environment(loader=FileSystemLoader("templates/agent"))

    def make_prompt_text(self, file_name, name, data):

        t_prompt = self.environment.get_template(file_name)
        agent_name = name
        template_content  = t_prompt.render({ 'agent_name' : agent_name, 'data' : data})        

        return template_content
    
    def make_bpersona_prompt(self, current_project, bpersona): 

        df_labels = pd.DataFrame()
        if current_project['project_type'] == 'B2C':
            df_labels = pd.read_csv('data/b2c-bpersona-survey/questions_final.csv' )
        elif current_project['project_type'] == 'B2B':
            df_labels = pd.read_csv('data/b2b-bpersona-survey/questions_final.csv' )

        list_labels = df_labels.to_dict('records')

        agents_attributes = []
        for label_fields in list_labels:
            if label_fields['is_title'] == False:
                if label_fields['field'] in bpersona:
                    label_fields['value'] = bpersona[label_fields['field']]
                    agents_attributes.append(label_fields)

        definition = self.make_prompt_text('bpersona_agent.txt',bpersona['como-se-llama-tu-buyer-persona'],{'entity' : agents_attributes})
        prompt = self.new(current_project,'bperson',definition)
        return prompt

    def make_producto_prompt(self, current_project, producto): 
        df_labels = pd.DataFrame()
        if current_project['project_type'] == 'B2C':
            df_labels = pd.read_csv('data/b2c-producto-survey/questions_final.csv' )
        elif current_project['project_type'] == 'B2B':
            df_labels = pd.read_csv('data/b2b-producto-survey/questions_final.csv' )

        list_labels = df_labels.to_dict('records')
        agents_attributes = []
        for label_fields in list_labels:
            if label_fields['is_title'] == False:
                if label_fields['field'] in producto:
                    label_fields['value'] = producto[label_fields['field']]
                    agents_attributes.append(label_fields)

        definition = self.make_prompt_text('producto_agent.txt',producto['cual-es-el-nombre-de-tu-producto'],{'entity' : agents_attributes})
        prompt = self.new(current_project,'product',definition)
        return prompt

    def make_consultor_prompt(self, current_project, consultor): 
        df_labels = pd.DataFrame()
        if current_project['project_type'] == 'B2C':
            df_labels = pd.read_csv('data/b2c-consultor-survey/questions_final.csv' )
        elif current_project['project_type'] == 'B2B':
            df_labels = pd.read_csv('data/b2b-consultor-survey/questions_final.csv' )

        list_labels = df_labels.to_dict('records')
        agents_attributes = []
        for label_fields in list_labels:
            if label_fields['is_title'] == False:
                if label_fields['field'] in consultor:
                    label_fields['value'] = consultor[label_fields['field']]
                    agents_attributes.append(label_fields)

        definition = self.make_prompt_text('consultor_agent.txt',consultor['cual-es-el-nombre-del-consultor'],{'entity' : agents_attributes})
        prompt = self.new(current_project,'consultant',definition)
        return prompt

    def make_brand_prompt(self, current_project, brand): 
        df_labels = pd.DataFrame()
        df_labels = pd.read_csv('data/brand/fields.csv' )

        list_labels = df_labels.to_dict('records')
        agents_attributes = []
        for label_fields in list_labels:
            if label_fields['is_title'] == False:
                if label_fields['field'] in brand:
                    label_fields['value'] = brand[label_fields['field']]
                    agents_attributes.append(label_fields)

        definition = self.make_prompt_text('brand_agent.txt',brand['brand_name'],{'entity' : agents_attributes})
        prompt = self.new(current_project,'consultant',definition)
        return prompt

    def get_by_project(self,project):
        return self.promptRepository.get_by_project(project)

    def new(self,project,prompt_type,definition):
        prompt = self.promptRepository.new(project)
        prompt['prompt_type'] = prompt_type
        prompt['definition'] = definition
        return prompt

    def save(self,entity):
        result = None
        if 'id' in entity:
            result = self.promptRepository.update(entity) 
        else:
            result = self.promptRepository.create(entity)
        return result
    
class AgentManager :

    agentRepository = AgentRepository()
    n8nClient = N8NClient()

    def generate_agent(self, current_project, prompts,entities):

        # Create the Agent to Make queries
        q_strapi_agent = self.agentRepository.get_by_project(current_project)        
        strapi_agent = None
        if len(q_strapi_agent) > 0:
            strapi_agent = q_strapi_agent[0]
        else:
            strapi_agent = self.agentRepository.new(current_project)
        
        ai_agent_name = slugify.slugify(current_project['name'])
        # join_definitions = '\n'.join([promptBPerson['definition'],promptProductoSurvey['definition'],promptConsultorSurvey['definition'],promptBrand['definition']])
        join_definitions = '\n'.join(prompts)

        deleted = True
        if not strapi_agent is None and 'id' in strapi_agent:
            deleted = self.n8nClient.delete_agent(strapi_agent['ai_platform_id'])

        agent_generated = False
        if deleted:
            ai_agent =  self.n8nClient.create_agent(ai_agent_name,join_definitions)

            if ai_agent['ok'] == 1 and 'data' in ai_agent and 'id' in ai_agent['data']:

                strapi_agent['name'] = ai_agent_name
                strapi_agent['definition'] = join_definitions
                strapi_agent['ai_platform_id'] = ai_agent['data']['id']

                strapi_agent['entities'] = entities

                if 'id' in strapi_agent:
                    self.agentRepository.update(strapi_agent)
                else:
                    self.agentRepository.create(strapi_agent)
        
        return strapi_agent


    def get_by_project(self, current_project):

        strapi_agent = None

        q_strapi_agent = self.agentRepository.get_by_project(current_project)
        if len(q_strapi_agent) > 0:
            strapi_agent = q_strapi_agent[0]

        return strapi_agent
            

class AgentInteraction:

    agentManager = AgentManager()
    n8nClient = N8NClient()

    def generate_initial_bperson(self, current_project):

        agent = self.agentManager.get_by_project(current_project)

        bpersons = []

        if not agent is None:
            platform_id = agent['ai_platform_id']
            name = agent['name']
            entities = agent['entities']

            bpersons = self.n8nClient.generate_initial_bperson(platform_id,name,entities['bperson'])
                
        return bpersons

 
    def generate_consultor(self, current_project, bPersonaSurvey, promptBPerson, productoSurvey, promptProductoSurvey):

        # agent = self.agentManager.get_by_project(current_project)

        consultors = []

        # if not agent is None:
        product_name = productoSurvey['cual-es-el-nombre-de-tu-producto']
        person_name = bPersonaSurvey['como-se-llama-tu-buyer-persona']  

        text_prompt_bperson = promptBPerson['definition']
        text_prompt_product = promptProductoSurvey['definition']

        consultors = self.n8nClient.generate_consultor(current_project, person_name, text_prompt_bperson, product_name, text_prompt_product)

        result_consultors = []
        for c in consultors:
            element = {}
            for attr in c:
                element[attr['Id Caracteristica']] = attr['Valor']
            result_consultors.append(element)

        return result_consultors


    def generate_new_bpersons_using_another(self, current_project, variation_name, variation_text):
        agent = self.agentManager.get_by_project(current_project)
        bpersons = []
        if not agent is None:
            platform_id = agent['ai_platform_id']
            name = agent['name']
            entities = agent['entities']

            bpersons = self.n8nClient.generate_new_bpersons_using_another(platform_id,name,variation_name,variation_text)

        return bpersons


    def improve_bperson_description(self, current_project,variation_name,previous_description, proposal_description):
        agent = self.agentManager.get_by_project(current_project)
        df_bpersons = pd.DataFrame()
        if not agent is None:
            platform_id = agent['ai_platform_id']
            name = agent['name']

            bpersons = self.n8nClient.improve_bperson_description(platform_id, name, variation_name, previous_description, proposal_description)

            if not bpersons is None:
                df_bpersons = pd.DataFrame.from_dict(bpersons)

        return df_bpersons

    def generate_scenarios(self, current_project, bperson, product_survey, sales_process):

        agent = self.agentManager.get_by_project(current_project)

        scenarios = []

        if not agent is None:
            platform_id = agent['ai_platform_id']
            agent_name = agent['name']

            person_name = bperson['Name']
            product_name = product_survey['cual-es-el-nombre-de-tu-producto']
            sales_process_atributes = sales_process

            scenarios = self.n8nClient.generate_scenarios(platform_id,agent_name,person_name,product_name,sales_process_atributes)
            print(scenarios)

        return scenarios

    def improve_text_scenario(self, current_project, bperson, product_survey, sales_process,scenario, old_text, new_text):

        agent = self.agentManager.get_by_project(current_project)

        scenarios = []

        if not agent is None:
            platform_id = agent['ai_platform_id']
            agent_name = agent['name']

            person_name = bperson['Name']

            scenarios = self.n8nClient.improve_text(platform_id,agent_name,old_text,new_text)

        return scenarios
    
    def improve_text_activity(self, current_project, bperson, product, scenario, activity, old_text, new_text):
        agent = self.agentManager.get_by_project(current_project)

        suggestions = []

        if not agent is None:
            platform_id = agent['ai_platform_id']
            agent_name = agent['name']

            person_name = bperson['Name']

            suggestions = self.n8nClient.improve_text(platform_id,agent_name,old_text,new_text)

        return suggestions

    def generate_new_scenario_using_another(self, current_project, bperson, product_survey, sales_process,scenario):

        agent = self.agentManager.get_by_project(current_project)

        scenarios = []

        if not agent is None:
            platform_id = agent['ai_platform_id']
            agent_name = agent['name']

            person_name = bperson['Name']
            product_name = product_survey['cual-es-el-nombre-de-tu-producto']
            sales_process_attributes = sales_process
            scenario_attributes = scenario

            # print(scenario_attributes)
            scenarios = self.n8nClient.generate_new_scenario_using_another(platform_id,agent_name,person_name,product_name,sales_process_attributes,scenario_attributes)
            # print(scenarios)

        return scenarios
    
    def generate_longtext_bperson(self, current_project, bperson, bperson_survey, product_survey):
        agent = self.agentManager.get_by_project(current_project)

        results = []

        if not agent is None:
            platform_id = agent['ai_platform_id']
            agent_name = agent['name']

            person_name = bperson['Name']
            product_name = product_survey['cual-es-el-nombre-de-tu-producto']
            bperson_survey = bperson_survey

            results = self.n8nClient.generate_longtext_bperson(platform_id,agent_name,person_name,product_name,bperson_survey)
            print(results)

        return results
    
    def generate_longtext_product(self,current_project, bperson, bperson_survey,product,product_survey):
        agent = self.agentManager.get_by_project(current_project)

        results = []

        if not agent is None:
            platform_id = agent['ai_platform_id']
            agent_name = agent['name']

            person_name = bperson['Name']
            product_name = product['Name']
            if 'Long Description' in bperson and not bperson['Long Description'] is None:
                person_description = bperson['Long Description']
            else:
                person_description = bperson['Description']

            results = self.n8nClient.generate_longtext_product(platform_id,agent_name,person_name,person_description,product_name)
            print(results)

        return results


    def improve_longtext_bperson(self, current_project, bperson, product_survey, old_text, new_text):
        agent = self.agentManager.get_by_project(current_project)

        results = []

        if not agent is None:
            platform_id = agent['ai_platform_id']
            agent_name = agent['name']

            person_name = bperson['Name']
            product_name = product_survey['cual-es-el-nombre-de-tu-producto']

            results = self.n8nClient.improve_text(platform_id,agent_name,old_text,new_text)

        return results

    def improve_longtext_product(self, current_project, bperson, product, old_text, new_text):
        agent = self.agentManager.get_by_project(current_project)

        results = []

        if not agent is None:
            platform_id = agent['ai_platform_id']
            agent_name = agent['name']

            person_name = bperson['Name']
            product_name = product['Name']

            results = self.n8nClient.improve_text(platform_id,agent_name,old_text,new_text)

        return results


    def generate_scenario_contexts(self, current_project, bperson, bperson_survey, product_survey):
        agent = self.agentManager.get_by_project(current_project)

        contexts = []

        if not agent is None:
            platform_id = agent['ai_platform_id']
            agent_name = agent['name']

            person_name = bperson['Name']
            person_description = bperson['Description']
            product_name = product_survey['cual-es-el-nombre-de-tu-producto']

            contexts = self.n8nClient.generate_scenario_contexts(platform_id,agent_name,person_name,person_description,product_name)
            # print(scenarios)

        return contexts

    def get_sales_process_using_context(self, current_project, bperson, bperson_survey, product_survey, context_scenario):
        agent = self.agentManager.get_by_project(current_project)

        answers = []

        if not agent is None:
            platform_id = agent['ai_platform_id']
            agent_name = agent['name']

            person_name = bperson['Name']
            context_description = context_scenario['Description']
            product_name = product_survey['cual-es-el-nombre-de-tu-producto']

            result = self.n8nClient.generate_answer_sales_process(platform_id,agent_name,person_name,context_description,product_name)
            if not result is None:
                answers = result
        
        return answers


    def generate_scenario_activities(self, current_project, bperson, product_survey, scenario):
        agent = self.agentManager.get_by_project(current_project)

        activities = []

        if not agent is None:

            platform_id = agent['ai_platform_id']
            agent_name = agent['name']

            person_name = bperson['Name']
            person_description = bperson['Description']
            product_name = product_survey['cual-es-el-nombre-de-tu-producto']

            scenario_title =  scenario['Name']
            scenario_description =  scenario['Description']

            activities = self.n8nClient.generate_scenario_activies(platform_id,agent_name,person_name,product_name,scenario_title,scenario_description)

        return activities


class ProjectManager:

    promptManager = PromptManager()
    agentManager = AgentManager()

    projectRepository = ProjectRepository()
    bPersonaSurveyRepository = BPersonaSurveyRepository() 
    productoSurveyRepository = ProductoSurveyRepository() 
    consultorSurveyRepository = ConsultorSurveyRepository() 
    brandRepository = BrandRepository() 
    bPersonRepository = BPersonRepository()
    salesProcessRepository = SalesProcessRepository()
    scenarioRepository =  ScenarioRepository()
    productRepository =  ProductRepository()
    scenarioContextRepository =  ScenarioContextRepository()
    scenarioActivityRepository =  ScenarioActivityRepository()
    consultorSuggestionRepository =  ConsultorSuggestionRepository()
    

    agentInteraction = AgentInteraction()


    def generate_consultor(self,current_project):
        bPersonaSurvey = self.get_bperson_survey(current_project)
        productoSurvey = self.get_product_survey(current_project)

        promptBPerson = self.promptManager.make_bpersona_prompt(current_project,bPersonaSurvey)        
        promptProductoSurvey = self.promptManager.make_producto_prompt(current_project,productoSurvey)        

        # Save al Prompts ang Create the OpenAI Agents
        self.promptManager.save(promptBPerson)
        self.promptManager.save(promptProductoSurvey)

        consultor_suggestions = self.agentInteraction.generate_consultor(current_project, bPersonaSurvey, promptBPerson, productoSurvey, promptProductoSurvey)

        df_consultor_suggestions = pd.DataFrame()
        if not consultor_suggestions is None and len(consultor_suggestions) > 0:
            df_consultor_suggestions = pd.DataFrame.from_dict(consultor_suggestions)
        self.save_dataframe_consultor_suggestions(current_project,df_consultor_suggestions)
        return df_consultor_suggestions 

    def save_dataframe_consultor_suggestions(self,current_project,df) :
        df = df.drop(['parent_ref'], axis=1, errors='ignore')
        df_entities = df.T.to_dict().values()
        for row in df_entities:
            self.save_consultor_suggestion(current_project,row) 


    def save_consultor_suggestion(self,current_project,row):
        result = None
        if not current_project is None and 'id' in current_project:
            row['parent_ref'] = current_project['id']
            if 'id' in row :
                result = self.consultorSuggestionRepository.update(row) 
            else:
                result = self.consultorSuggestionRepository.create(row)
        return result
    

    def get_consultor_suggestions(self,parent):
        consultorSuggestionsQ = self.consultorSuggestionRepository.get_by_project(parent)
        df_consultor_suggestions = pd.DataFrame()
        if not consultorSuggestionsQ is None and len(consultorSuggestionsQ) > 0:
            consultorSuggestions = []
            for e in consultorSuggestionsQ:

                export_item = e
                export_item['id'] = e['id'] 
                export_item['parent_ref'] = parent['id']

                consultorSuggestions.append(export_item)  
        
            df_consultor_suggestions = pd.DataFrame.from_dict(consultorSuggestions)

        return df_consultor_suggestions


    def autofill_consultor_survey(self,current_project,current_row_data):
        consultorSurvey = self.get_consultor_survey(current_project)
        for key, value in  current_row_data.items():
            if not key in ('id','parent_ref','createdAt','updatedAt','publishedAt'):
                consultorSurvey[key] = value 
        self.save_consultor_survey(current_project,consultorSurvey)



    def save_consultor_survey(self,current_project,row):
        result = None
        if not current_project is None and 'id' in current_project:
            row['parent_ref'] = current_project['id']
            if 'id' in row :
                result = self.consultorSurveyRepository.update(row) 
            else:
                result = self.consultorSurveyRepository.create(row)
        return result

    def get_bperson_survey(self,current_project):
        bPersonaSurvey = None
        bPersonaSurveyQ = self.bPersonaSurveyRepository.get_by_project(current_project)
        if len(bPersonaSurveyQ) > 0  :
            bPersonaSurvey = bPersonaSurveyQ[0]
            bPersonaSurvey['parent_ref'] = current_project['id']
        else:
            bPersonaSurvey = self.bPersonaSurveyRepository.new(current_project)
        return bPersonaSurvey
    
    def get_product_survey(self,current_project):
        productoSurvey = None
        productoSurveyQ = self.productoSurveyRepository.get_by_project(current_project)
        if len(productoSurveyQ) > 0  :
            productoSurvey = productoSurveyQ[0]
            productoSurvey['parent_ref'] = current_project['id']
        else:
            productoSurvey = self.productoSurveyRepository.new(current_project)
        return productoSurvey
    
    def get_consultor_survey(self,current_project):
        consultorSurvey = None
        consultorSurveyQ = self.consultorSurveyRepository.get_by_project(current_project)
        if len(consultorSurveyQ) > 0  :
            consultorSurvey = consultorSurveyQ[0]
            consultorSurvey['parent_ref'] = current_project['id']
        else:
            consultorSurvey = self.consultorSurveyRepository.new(current_project)
        return consultorSurvey
    
    def get_sales_process_survey(self,bperson):
        salesProcessSurvey = None
        salesProcessSurveyQ = self.salesProcessRepository.get_by_bperson(bperson)
        if len(salesProcessSurveyQ) > 0  :
            salesProcessSurvey = salesProcessSurveyQ[0]
            salesProcessSurvey['parent_ref'] = bperson['id']
        else:
            salesProcessSurvey = self.salesProcessRepository.new(bperson)
        return salesProcessSurvey
    
    def get_scenarios_from_aiagent(self, current_project, bperson, product, salesProcess):
        scenarios_ai = self.agentInteraction.generate_scenarios(current_project, bperson, product, salesProcess)
        df_scenarios = pd.DataFrame()
        if not scenarios_ai is None and len(scenarios_ai) > 0:
            for b in scenarios_ai:
                b['is_favorite'] =  False
                b['was_improved'] = False
                b['from_another'] = False
            df_scenarios = pd.DataFrame.from_dict(scenarios_ai)
        print(df_scenarios) 
        self.save_dataframe_scenarios(bperson,df_scenarios)
        return df_scenarios 

    def generate_new_scenario_using_another(self, current_project, bperson, product, salesProcess, scenario ):
        dict_scenario = scenario.to_dict()        

        new_scenarioQ = self.agentInteraction.generate_new_scenario_using_another(current_project, bperson, product, salesProcess, dict_scenario )

        if not new_scenarioQ is None and len(new_scenarioQ) > 0 :
            new_scenario = new_scenarioQ[0]
            if 'Description' in new_scenario and 'Name' in new_scenario:
                dict_scenario['Name'] = new_scenario['Name']
                dict_scenario['Description'] = new_scenario['Description']

                del dict_scenario['id']

                # print('*************** TO SAVE *********************')
                # print(dict_scenario)
                self.save_scenario(bperson,dict_scenario)

        return dict_scenario 


    def improve_text_scenario(self, current_project, bperson, product, salesProcess, scenario, old_text, new_text):
        text_improved = self.agentInteraction.improve_text_scenario(current_project, bperson, product, salesProcess,scenario, old_text, new_text)

        dict_scenario = scenario.to_dict()
        if not text_improved is None and len(text_improved) > 0 :
            new_text = text_improved[0]
            if 'Text' in new_text:
                dict_scenario['Description'] = new_text['Text']
                # print(dict_scenario)
                self.save_scenario(bperson,dict_scenario)

        return dict_scenario 
    

    def improve_text_activity(self, current_project,bperson,product,scenario,activity,old_text,new_text):
        text_improved = self.agentInteraction.improve_text_activity(current_project, bperson, product, scenario, activity, old_text, new_text)

        dict_activity = activity
        if not type(activity) is dict: 
            dict_activity = activity.to_dict()

        if not text_improved is None and len(text_improved) > 0 :
            new_text = text_improved[0]
            if 'Text' in new_text:
                activity['Description'] = new_text['Text']
                self.save_scenario_activity(scenario,activity)

        return dict_activity 

    def generate_longtext_bperson(self, current_project, bperson, bperson_survey, product):
        long_text = self.agentInteraction.generate_longtext_bperson(current_project, bperson, bperson_survey, product)

        dict_bperson = bperson
        if type(bperson) != dict:
            dict_bperson = bperson.to_dict()


        new_text = {'Text' : ''}
        if not long_text is None and len(long_text) > 0 :
            new_text = long_text[0]
            if 'Text' in new_text:
                dict_bperson['Long Description'] = new_text['Text']
                # print(dict_scenario)
                self.save_bperson(current_project,dict_bperson)

        return new_text 

    def improve_longtext_bperson(self, current_project, bperson, product, old_text, new_text):
        text_improved = self.agentInteraction.improve_longtext_bperson(current_project, bperson, product, old_text, new_text)

        dict_bperson = bperson
        if type(bperson) != dict:
            dict_bperson = bperson.to_dict()

        new_text = {'Text' : ''}
        if not text_improved is None and len(text_improved) > 0 :
            new_text = text_improved[0]
            if 'Text' in new_text:
                dict_bperson['Long Description'] = new_text['Text']
                self.save_bperson(current_project,dict_bperson)

        return text_improved 
    
    def improve_longtext_product(self, current_project, bperson, product, old_text, new_text):
        text_improved = self.agentInteraction.improve_longtext_product(current_project, bperson, product, old_text, new_text)

        dict_product = product
        if type(product) != dict:
            dict_product = product.to_dict()

        new_text = {'Text' : ''}
        if not text_improved is None and len(text_improved) > 0 :
            new_text = text_improved[0]
            if 'Text' in new_text:
                dict_product['Long Description'] = new_text['Text']
                self.save_product(bperson,dict_product)

        return new_text 

    
    def save_dataframe_scenario_contexts(self,parent,df):
        df = df.drop(['parent_ref'], axis=1, errors='ignore')
        df_entities = df.T.to_dict().values()
        for row in df_entities:
            self.save_scenario_context(parent,row) 

    def generate_scenario_contexts(self, current_project, bperson, bperson_survey,product):
        scenario_contexts = self.agentInteraction.generate_scenario_contexts(current_project, bperson, bperson_survey, product)

        df_scenario_contexts = pd.DataFrame()
        if not scenario_contexts is None and len(scenario_contexts) > 0:
            for b in scenario_contexts:
                b['is_favorite'] =  False
                b['was_improved'] = False
                b['from_another'] = False
            df_scenario_contexts = pd.DataFrame.from_dict(scenario_contexts)
        # print(df_scenario_contexts) 
        self.save_dataframe_scenario_contexts(bperson,df_scenario_contexts)
        return df_scenario_contexts 
    
    def generate_longtext_product(self, current_project, bperson, bperson_survey,product,productSurvey):
        long_text = self.agentInteraction.generate_longtext_product(current_project, bperson, bperson_survey,product,productSurvey)

        dict_product = product
        if type(product) != dict:
            dict_product = product.to_dict()

        new_text = {'Text' : ''}
        if not long_text is None and len(long_text) > 0 :
            new_text = long_text[0]
            if 'Text' in new_text:
                dict_product['Long Description'] = new_text['Text']
                self.save_product(bperson,dict_product)

        return new_text 
        

    def get_scenarios(self,parent):
        bPersonScenariosQ = self.scenarioRepository.get_by_bperson(parent)
        df_scenarios = pd.DataFrame()
        if not bPersonScenariosQ is None and len(bPersonScenariosQ) > 0:
            bPersonScenariosResult = []
            for e in bPersonScenariosQ:

                export_item = e['definition']

                export_item['id'] = e['id'] 
                # export_item['name'] = e['name']

                export_item['is_favorite'] =  e['is_favorite']
                export_item['was_improved'] = e['was_improved']
                export_item['from_another'] = e['from_another']

                export_item['parent_ref'] = parent['id']

                bPersonScenariosResult.append(export_item)  
        
            df_scenarios = pd.DataFrame.from_dict(bPersonScenariosResult)

        return df_scenarios
    
    def get_scenario_contexts(self,parent):
        scenarioContextsQ = self.scenarioContextRepository.get_by_bperson(parent)
        df_scenario_contexts = pd.DataFrame()
        if not scenarioContextsQ is None and len(scenarioContextsQ) > 0:
            scenarioContextsResult = []
            for e in scenarioContextsQ:

                export_item = e['definition']

                export_item['id'] = e['id'] 
                # export_item['name'] = e['name']

                export_item['is_favorite'] =  e['is_favorite']
                export_item['was_improved'] = e['was_improved']
                export_item['from_another'] = e['from_another']

                export_item['parent_ref'] = parent['id']

                scenarioContextsResult.append(export_item)  
        
            df_scenario_contexts = pd.DataFrame.from_dict(scenarioContextsResult)

        return df_scenario_contexts

    def new_scenario_actitiy(self,parent):
        new_activity = { 'Name' : '',  'Description': '' }
        new_activity['is_favorite'] = False
        new_activity['was_improved'] = False
        new_activity['from_another'] = False

        if not parent is None and 'id' in parent:
            new_activity['parent_ref'] = parent['id']

        return new_activity

    def get_product(self,bperson):
        productEntity = None
        productQ = self.productRepository.get_by_bperson(bperson)
        if len(productQ) > 0  :
            e = productQ[0]
            e['parent_ref'] = bperson['id']

            productEntity = e['definition']

            productEntity['id'] = e['id'] 

            productEntity['is_favorite'] =  e['is_favorite']
            productEntity['was_improved'] = e['was_improved']
            productEntity['from_another'] = e['from_another']

            productEntity['parent_ref'] = e['id']

        else:
            productEntity = { 'Name' : '',  'Long Description': '' }
            productEntity['is_favorite'] = False
            productEntity['was_improved'] = False
            productEntity['from_another'] = False

            current_project_id = bperson['parent_ref']

            current_project = self.get_project_by_id(current_project_id);

            product_survey = self.get_product_survey(current_project)

            productEntity['Name'] = product_survey['cual-es-el-nombre-de-tu-producto']


            if not bperson is None and 'id' in bperson:
                productEntity['parent_ref'] = bperson['id']
            
        return productEntity


    def get_scenario_activities(self,parent):
        scenarioActivitiesQ = self.scenarioActivityRepository.get_by_scenario(parent)
        df_scenario_activities = pd.DataFrame()
        if not scenarioActivitiesQ is None and len(scenarioActivitiesQ) > 0:
            scenarioActivitiesResult = []
            for e in scenarioActivitiesQ:

                export_item = e['definition']

                export_item['id'] = e['id'] 

                export_item['is_favorite'] =  e['is_favorite']
                export_item['was_improved'] = e['was_improved']
                export_item['from_another'] = e['from_another']

                export_item['parent_ref'] = parent['id']

                scenarioActivitiesResult.append(export_item)  
        
            df_scenario_activities = pd.DataFrame.from_dict(scenarioActivitiesResult)

        return df_scenario_activities


    def autofill_sales_process_using_context(self, current_project, bperson, bperson_survey,product, context_scenario, sales_process):
        answers = self.agentInteraction.get_sales_process_using_context(current_project, bperson, bperson_survey, product, context_scenario)
        print(answers)
        for a in answers:
            sales_process[a['Id Pregunta']] = a['Respuesta'] 
        print(sales_process)
        self.save_sales_process(bperson,sales_process)


    def save_dataframe_scenarios(self,parent,df) :
        df = df.drop(['parent_ref'], axis=1, errors='ignore')
        df_entities = df.T.to_dict().values()
        for row in df_entities:
            self.save_scenario(parent,row) 

    def save_scenario(self,parent,row):
        result = None
        entity = self.convert_row_to_scenario(parent,row)
        if 'id' in entity:
            result = self.scenarioRepository.update(entity) 
        else:
            result = self.scenarioRepository.create(entity)
        return result

    def save_product(self,parent,row):
        result = None
        entity = self.convert_row_to_product(parent,row)
        if 'id' in entity:
            result = self.productRepository.update(entity) 
        else:
            result = self.productRepository.create(entity)
        return result

    def save_scenario_context(self,parent,row):
        result = None
        entity = self.convert_row_to_scenario_context(parent,row)
        # print(entity)
        if 'id' in entity:
            result = self.scenarioContextRepository.update(entity) 
        else:
            result = self.scenarioContextRepository.create(entity)
        return result

    def get_brand(self, current_project):
        brand = None
        brandQ = self.brandRepository.get_by_project(current_project)
        if len(brandQ) > 0  :
            brand = brandQ[0]
            brand['parent_ref'] = current_project['id']
        else:
            brand = self.brandRepository.new(current_project)
        return brand
    
    def save(self,entity):
        result = None
        if 'id' in entity:
            result = self.projectRepository.update(entity) 
        else:
            result = self.projectRepository.create(entity)
        return result
    
    def save_sales_process(self,bperson,row):
        result = None
        if 'id' in row:
            result = self.salesProcessRepository.update(row) 
        else:
            result = self.salesProcessRepository.create(row)
        return result    
    
    def save_bperson(self,current_project,row):
        result = None
        entity = self.convert_row_to_bperson(current_project,row)
        if 'id' in entity:
            result = self.bPersonRepository.update(entity) 
        else:
            result = self.bPersonRepository.create(entity)
        return result

    def save_scenario_activity(self,scenario,row):
        result = None
        entity = self.convert_row_to_scenario_activity(scenario,row)
        print(entity)
        if 'id' in entity:
            result = self.scenarioActivityRepository.update(entity) 
        else:
            result = self.scenarioActivityRepository.create(entity)
        return result

    def convert_row_to_bperson(self,current_project,row):
        return self.convert_row_to_strapi_entity(current_project,row,'bperson')

    def convert_row_to_sales_process(self,bperson,row):
        return self.convert_row_to_strapi_entity(bperson,row,'sales_process')

    def convert_row_to_scenario(self,bperson,row):
        return self.convert_row_to_strapi_entity(bperson,row,'scenario')
    
    def convert_row_to_product(self,bperson,row):
        return self.convert_row_to_strapi_entity(bperson,row,'product')

    def convert_row_to_scenario_context(self,bperson,row):
        return self.convert_row_to_strapi_entity(bperson,row,'scenario_context')

    def convert_row_to_scenario_activity(self,scenario,row):
        return self.convert_row_to_strapi_entity(scenario,row,'scenario_activity')

    def convert_row_to_strapi_entity(self,parent,row,strapi_entity_name):
        entity = None
        if not strapi_entity_name is None:
            if strapi_entity_name == 'bperson':
                entity = self.bPersonRepository.new(parent)
            elif strapi_entity_name == 'sales_process':
                entity = self.salesProcessRepository.new(parent)
            elif strapi_entity_name == 'scenario':
                entity = self.scenarioRepository.new(parent)
            elif strapi_entity_name == 'scenario_context':
                entity = self.scenarioContextRepository.new(parent)
            elif strapi_entity_name == 'scenario_activity':
                entity = self.scenarioActivityRepository.new(parent)
            elif strapi_entity_name == 'product':
                entity = self.productRepository.new(parent)

            if not entity is None:

                if not row is None and 'id' in row:
                    if not math.isnan(row['id']):
                        entity['id'] = row['id']
                    del row['id']

                if not row is None and 'parent_ref' in row:
                    del row['parent_ref']

                name = row['Name']
                # json_definition = json.loads(json.dumps(entity))

                entity['name'] = name
                entity['definition'] = row
                        
                entity['parent_ref'] = parent['id']

                entity['is_favorite'] = row['is_favorite']
                entity['was_improved'] = row['was_improved']
                entity['from_another'] = row['from_another']

        return entity

    def get_bpersons_from_aiagent(self, current_project):
        bpersons_ai = self.agentInteraction.generate_initial_bperson(current_project)
        df_bpersons = pd.DataFrame()
        if not bpersons_ai is None and len(bpersons_ai) > 0:
            for b in bpersons_ai:
                b['is_favorite'] =  False
                b['was_improved'] = False
                b['from_another'] = False
            df_bpersons = pd.DataFrame.from_dict(bpersons_ai)
            self.save_dataframe_bperson(current_project,df_bpersons)
        return df_bpersons 
    
    def generate_scenario_activities(self, current_project, bperson, product_survey, scenario):
        activities = self.agentInteraction.generate_scenario_activities(current_project,bperson,product_survey,scenario)
        df_activities = pd.DataFrame()
        if not activities is None and len(activities) > 0:
            for a in activities:
                a['is_favorite'] =  False
                a['was_improved'] = False
                a['from_another'] = False
            df_activities = pd.DataFrame.from_dict(activities)
            self.save_dataframe_scenario_activities(scenario,df_activities)
        return df_activities 
    

    def generate_new_bpersons_using_another(self,current_project,bperson):  

        variation_name  = bperson['Name']

        text_attributes = [f"{key}: {value}" for key,value in bperson.items()]
        variation_text  = "\n".join(text_attributes)


        variations = self.agentInteraction.generate_new_bpersons_using_another(current_project,variation_name,variation_text)        
        df_bpersons = pd.DataFrame()
        if not variations is None and len(variations) > 0:
            for v in variations:
                v['is_favorite'] =  False
                v['was_improved'] = False
                v['from_another'] = True
            df_bpersons = pd.DataFrame.from_dict(variations)
            self.save_dataframe_bperson(current_project,df_bpersons)


        # print('------- BPersons Generated by AI --------')
        # print(df_bpersons)

        return df_bpersons 
    
    def improve_bperson(self,current_project,old_person,new_bperson):
        variation_name  = old_person['Name']

        text_attributes = [f"{key}: {value}" for key,value in old_person.items()]
        original_text  = "\n".join(text_attributes)

        text_attributes = [f"{key}: {value}" for key,value in new_bperson.items()]
        new_text  = "\n".join(text_attributes)

        variations = self.agentInteraction.improve_bperson_description(current_project,variation_name, original_text, new_text)

        variation = None
        if not variations.empty:
            list_variations = variations.to_dict('records') 
            if len(list_variations) > 0 :
                variation = list_variations[0]

                variation['is_favorite'] =  old_person['is_favorite']
                variation['was_improved'] = old_person['was_improved']
                variation['from_another'] = old_person['from_another']

                if 'id' in old_person:
                    variation['id'] = old_person['id']

                variation['parent_ref'] = current_project['id']


        return variation

    def save_dataframe_bperson(self,current_project,df) :
        df = df.drop(['parent_ref'], axis=1, errors='ignore')
        df_entities = df.T.to_dict().values()
        for row in df_entities:
            self.save_bperson(current_project,row) 

    def save_dataframe_scenario_activities(self,scenario,df):
        df = df.drop(['parent_ref'], axis=1, errors='ignore')
        df_entities = df.T.to_dict().values()
        for row in df_entities:
            self.save_scenario_activity(scenario,row) 


    def set_fav_bperson(self,current_project,row):
        result = None
        if 'id' in row:
            row['is_favorite'] = True
            print(row)
            result = self.save_bperson(current_project,row) 
        return result

    def unset_fav_bperson(self,current_project,row):
        result = None
        if 'id' in row:
            row['is_favorite'] = False
            result = self.save_bperson(current_project,row) 
        return result
    
    def set_fav_scenario_context(self,bperson,row):
        result = None
        if 'id' in row:
            row['is_favorite'] = True
            result = self.save_scenario_context(bperson,row) 
        return result

    def unset_fav_scenario_context(self,bperson,row):
        result = None
        if 'id' in row:
            row['is_favorite'] = False
            result = self.save_scenario_context(bperson,row) 
        return result

    
    def get_bpersons(self,current_project):
        bPersonsResult = []
        df_bpersons = pd.DataFrame()
        bPersonsQ = self.bPersonRepository.get_by_project(current_project)
        if len(bPersonsQ) > 0 :
            for e in bPersonsQ:

                export_item = e['definition']

                export_item['id'] = e['id'] 
                # export_item['name'] = e['name']

                export_item['is_favorite'] =  e['is_favorite']
                export_item['was_improved'] = e['was_improved']
                export_item['from_another'] = e['from_another']

                export_item['parent_ref'] = current_project['id']

                bPersonsResult.append(export_item)  
        
            df_bpersons = pd.DataFrame.from_dict(bPersonsResult)
            df_bpersons = df_bpersons.replace(np.nan, '')

        return df_bpersons
    
    def get_bperson_by_id(self,bperson_id):
        bpersonQ = self.bPersonRepository.get_by_id(bperson_id)
        export_item = None 
        if not bpersonQ is None and len(bpersonQ) > 0:
            bperson = bpersonQ[0]
            # print(bperson)

            export_item = bperson['definition']

            export_item['id'] = bperson['id'] 
            # export_item['name'] = e['name']

            export_item['is_favorite'] =  bperson['is_favorite']
            export_item['was_improved'] = bperson['was_improved']
            export_item['from_another'] = bperson['from_another']

            export_item['parent_ref'] = bperson['parent_ref']['data']['id']
        return export_item
    
    def get_project_by_id(self,project_id):
        projectQ = self.projectRepository.get_by_id(project_id)
        export_item = None 
        if not projectQ is None and len(projectQ) > 0:
            export_item = projectQ[0]

        return export_item


    def get_favorite_bpersons(self,current_project):
        bPersonsResult = []
        bPersonsQ = self.bPersonRepository.get_by_project(current_project)
        if len(bPersonsQ) > 0 :
            for e in bPersonsQ:
                if current_project['is_favorite']:
                    e['parent_ref'] = current_project['id']
                    bPersonsResult.append(e)  
        return bPersonsResult
    
    def count_activities(self,current_scenario):
        activities = self.get_scenario_activities(current_scenario)
        return len(activities)

    
    def can_make_bperson_journey(self,current_project):
        can_make = True

        bPersonaSurvey = self.get_bperson_survey(current_project)
        productoSurvey = self.get_product_survey(current_project)
        consultorSurvey = self.get_consultor_survey(current_project)
        brand = self.get_brand(current_project)

        if bPersonaSurvey is None or not 'id' in bPersonaSurvey or bPersonaSurvey['id'] is None:
           can_make = False     
        elif productoSurvey is None or not 'id' in productoSurvey or productoSurvey['id'] is None:
            can_make = False 
        elif consultorSurvey is None or not 'id' in consultorSurvey or consultorSurvey['id'] is None:
            can_make = False 
        elif brand is None or not 'id' in brand or brand['id'] is None:
            can_make = False 

        return can_make

    
    def can_generate_agents(self,current_project):
        can_generate = True

        bPersonaSurvey = self.get_bperson_survey(current_project)
        productoSurvey = self.get_product_survey(current_project)
        consultorSurvey = self.get_consultor_survey(current_project)
        brand = self.get_brand(current_project)

        if bPersonaSurvey is None or not 'id' in bPersonaSurvey or bPersonaSurvey['id'] is None:
           can_generate = False     
        elif productoSurvey is None or not 'id' in productoSurvey or productoSurvey['id'] is None:
            can_generate = False 
        elif consultorSurvey is None or not 'id' in consultorSurvey or consultorSurvey['id'] is None:
            can_generate = False 
        elif brand is None or not 'id' in brand or brand['id'] is None:
            can_generate = False 

        bpersons_project = self.get_bpersons(current_project)
        if len(bpersons_project) > 0:
            can_generate = False 

        return can_generate

    def generate_agent(self,current_project):
        bPersonaSurvey = self.get_bperson_survey(current_project)
        productoSurvey = self.get_product_survey(current_project)
        consultorSurvey = self.get_consultor_survey(current_project)
        brand = self.get_brand(current_project)

        promptBPerson = self.promptManager.make_bpersona_prompt(current_project,bPersonaSurvey)        
        promptProductoSurvey = self.promptManager.make_producto_prompt(current_project,productoSurvey)        
        promptConsultorSurvey = self.promptManager.make_consultor_prompt(current_project,consultorSurvey)        
        promptBrand = self.promptManager.make_brand_prompt(current_project,brand) 

        # Save al Prompts ang Create the OpenAI Agents
        self.promptManager.save(promptBPerson)
        self.promptManager.save(promptProductoSurvey)
        self.promptManager.save(promptConsultorSurvey)
        self.promptManager.save(promptBrand)

        entities = { 
            'bperson' : bPersonaSurvey['como-se-llama-tu-buyer-persona'],
            'product' : productoSurvey['cual-es-el-nombre-de-tu-producto'],
            'consultant' : consultorSurvey['cual-es-el-nombre-del-consultor'],
            'brand' : brand['brand_name']
        }


        prompts = [promptBPerson['definition'],promptProductoSurvey['definition'],promptConsultorSurvey['definition']]

        agent_generated = self.agentManager.generate_agent(current_project,prompts,entities)

        return agent_generated 
    



