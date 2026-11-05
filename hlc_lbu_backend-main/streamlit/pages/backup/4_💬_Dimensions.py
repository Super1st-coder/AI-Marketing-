import pandas as pd
import streamlit as st
import extra_streamlit_components as stx
import json
import itertools

import os   
import openai

from jinja2 import Environment, FileSystemLoader
environment = Environment(loader=FileSystemLoader("templates/"))

OPENAI_KEY = 'OPENAI_API_KEY_REDACTED'

def load_openai_engine() : 
    engine = OpenAIEngine(OPENAI_KEY,{})
    return engine

class OpenAIEngine:

    def __init__(self,openai_key,data):
        self.openai_key = openai_key
        self.data = data

    def send_query(self,text): 
        # Cargar los templates de contexto
        all_files = os.listdir("training/")         
        txt_files = filter(lambda x: x[-4:] == '.txt', all_files)        
        corpus = [open(file).read() for file in [ "training/%s" % file_name for file_name in txt_files]  ]

        messages = []
        for c in corpus:
            messages.append({"role": "system", "content": c })

        #Ejecutar la consulta
        openai.api_key = self.openai_key
        messages.append({"role": "user", "content": text })

        response = openai.ChatCompletion.create(model="gpt-3.5-turbo-16k-0613", temperature=0.8,messages = messages)
        reply = response["choices"][0]["message"]["content"]        

        return reply



st.set_page_config(layout="wide", page_title="Dimensions", page_icon="🧮")

st.title("✍️ Dimensions Analysis")
st.caption("Generate new data about several dimensions of Product and Persons")


product_data = {}
person_data = {}

def get_product_data():
    df = pd.read_csv('data/product.csv' )
    df = df[df.name == 'product_name']
    json_df = df.to_json(orient='records' )
    json_object = json.loads(json_df)
    return json_object[0]['value']

def get_person_data():
    df = pd.read_csv('data/person.csv' )
    df = df[df.name == 'person_name']
    json_df = df.to_json(orient='records' )
    json_object = json.loads(json_df)
    return json_object[0]['value']

product_data = get_product_data()
person_data = get_person_data()
# model = load_llm_model()
model = load_openai_engine()

df_fears = pd.DataFrame()
df_purchase_motivations = pd.DataFrame()
df_purchase_causes = pd.DataFrame()
df_change_motivations = pd.DataFrame()
df_change_causes = pd.DataFrame()
df_privations = pd.DataFrame()
df_painpoints = pd.DataFrame()
df_people = pd.DataFrame()
df_activities = pd.DataFrame()

###############################################################################

def get_activities(product_data,person_data,model):
    print("LOADING ACTIVITIES")

    t_prompt = environment.get_template("activities.txt")
    template_content  = t_prompt.render({ 'person_name' : person_data, 'product_name' : product_data})
    
    llm_response = model.send_query(template_content)
    print(llm_response)
    json_data = json.loads(llm_response)

    df_activities = pd.DataFrame.from_records(json_data['result'])
    df_activities['active'] = False

    return df_activities


def refresh_activities(product_data,person_data,model):
    df_activities = get_activities(product_data,person_data,model)
    df_activities['active'] = False
    st.session_state.df_activities = df_activities 


###############################################################################

def get_people(product_data,person_data,model):
    print("LOADING PEOPLE")

    t_prompt = environment.get_template("people.txt")
    template_content  = t_prompt.render({ 'person_name' : person_data, 'product_name' : product_data})
    
    llm_response = model.send_query(template_content)
    json_data = json.loads(llm_response)

    df_people = pd.DataFrame.from_records(json_data['result'])
    df_people['active'] = False

    return df_people


def refresh_people(product_data,person_data,model):
    df_people = get_people(product_data,person_data,model)
    df_people['active'] = False
    st.session_state.df_people = df_people 

###############################################################################

def get_privations(product_data,person_data,model):
    print("LOADING CHANGE CAUSES")

    t_prompt = environment.get_template("privations.txt")
    template_content  = t_prompt.render({ 'person_name' : person_data, 'product_name' : product_data})
    
    llm_response = model.send_query(template_content)
    json_data = json.loads(llm_response)

    df_privations = pd.DataFrame.from_records(json_data['result'])
    df_privations['active'] = False

    return df_privations


def refresh_privations(product_data,person_data,model):
    df_privations = get_privations(product_data,person_data,model)
    df_privations['active'] = False
    st.session_state.df_privations = df_privations 

###############################################################################

def get_painpoints(product_data,person_data,model):
    print("LOADING PAIN POINTS")

    t_prompt = environment.get_template("painpoints.txt")
    template_content  = t_prompt.render({ 'person_name' : person_data, 'product_name' : product_data})
    
    llm_response = model.send_query(template_content)
    json_data = json.loads(llm_response)

    df_painpoints = pd.DataFrame.from_records(json_data['result'])
    df_painpoints['active'] = False

    return df_painpoints


def refresh_painpoints(product_data,person_data,model):
    df_painpoints = get_painpoints(product_data,person_data,model)
    df_painpoints['active'] = False
    st.session_state.df_painpoints = df_painpoints 

###############################################################################

def get_change_causes(product_data,person_data,model):
    print("LOADING CHANGE CAUSES")

    t_prompt = environment.get_template("change_causes.txt")
    template_content  = t_prompt.render({ 'person_name' : person_data, 'product_name' : product_data})
    
    llm_response = model.send_query(template_content)
    json_data = json.loads(llm_response)

    df_change_causes = pd.DataFrame.from_records(json_data['result'])
    df_change_causes['active'] = False

    return df_change_causes


def refresh_change_causes(product_data,person_data,model):
    df_change_causes = get_change_causes(product_data,person_data,model)
    df_change_causes['active'] = False
    st.session_state.df_change_causes = df_change_causes 

###############################################################################

def get_change_motivations(product_data,person_data,model):
    print("LOADING CHANGE MOTIVATIONS")

    t_prompt = environment.get_template("change_motivations.txt")
    template_content  = t_prompt.render({ 'person_name' : person_data, 'product_name' : product_data})
    
    llm_response = model.send_query(template_content)
    json_data = json.loads(llm_response)

    df_change_motivations = pd.DataFrame.from_records(json_data['result'])
    df_change_motivations['active'] = False

    return df_change_motivations

def refresh_change_motivations(product_data,person_data,model):
    df_change_motivations = get_change_motivations(product_data,person_data,model)
    df_change_motivations['active'] = False
    st.session_state.df_change_motivations = df_change_motivations 

###############################################################################

def get_purchase_causes(product_data,person_data,model):
    print("LOADING PURCHASE CAUSES")

    t_prompt = environment.get_template("purchase_causes.txt")
    template_content  = t_prompt.render({ 'person_name' : person_data, 'product_name' : product_data})
    
    llm_response = model.send_query(template_content)
    json_data = json.loads(llm_response)

    df_purchase_causes = pd.DataFrame.from_records(json_data['result'])
    df_purchase_causes['active'] = False

    return df_purchase_causes


def refresh_purchase_causes(product_data,person_data,model):
    df_purchase_causes = get_purchase_causes(product_data,person_data,model)
    df_purchase_causes['active'] = False
    st.session_state.df_purchase_causes = df_purchase_causes 

###############################################################################

def get_purchase_motivations(product_data,person_data,model):
    print("LOADING PURCHASE MOTIVATIONS")

    t_prompt = environment.get_template("purchase_motivations.txt")
    template_content  = t_prompt.render({ 'person_name' : person_data, 'product_name' : product_data})
    
    llm_response = model.send_query(template_content)
    json_data = json.loads(llm_response)

    df_purchase_motivations = pd.DataFrame.from_records(json_data['result'])
    df_purchase_motivations['active'] = False

    return df_purchase_motivations

def refresh_purchase_motivations(product_data,person_data,model):
    df_purchase_motivations = get_purchase_motivations(product_data,person_data,model)
    df_purchase_motivations['active'] = False
    st.session_state.df_purchase_motivations = df_purchase_motivations 

###############################################################################

def get_fears(product_data,person_data,model):
    print("LOADING FEARS")

    t_prompt = environment.get_template("fears.txt")
    template_content  = t_prompt.render({ 'person_name' : person_data, 'product_name' : product_data})
    
    llm_response = model.send_query(template_content)
    json_data = json.loads(llm_response)

    df_fears = pd.DataFrame.from_records(json_data['result'])
    df_fears['active'] = False

    return df_fears

def refresh_fears(product_data,person_data,model):
    df_fears = get_fears(product_data,person_data,model)
    df_fears['active'] = False
    st.session_state.df_fears = df_fears 

###############################################################################

def save_dimensions(df_purchase_causes,df_purchase_motivations,df_change_causes,df_change_motivations,df_fears,df_privations,df_painpoints,df_people,df_activities):
    dimensions = []
    if not df_purchase_causes is None and not df_purchase_causes.empty:
        df_purchase_causes.to_csv('intermediate/purchase_causes.csv',header=True,encoding='utf-8',index=False)
        df_purchase_causes_m = df_purchase_causes
        df_purchase_causes_m['dimension'] = "Purchase Cause"        
        dimensions.append(df_purchase_causes_m)
    if not df_purchase_motivations is None and not df_purchase_motivations.empty:
        df_purchase_motivations.to_csv('intermediate/purchase_motivations.csv',header=True,encoding='utf-8',index=False)
        df_purchase_motivations_m = df_purchase_motivations
        df_purchase_motivations_m['dimension'] = "Purchase Motivation"        
        dimensions.append(df_purchase_motivations_m)
    if not df_change_causes is None and not df_change_causes.empty:
        df_change_causes.to_csv('intermediate/change_causes.csv',header=True,encoding='utf-8',index=False)
        df_change_causes_m = df_change_causes
        df_change_causes_m['dimension'] = "Change Cause"        
        dimensions.append(df_change_causes_m)
    if not df_change_motivations is None and not df_change_motivations.empty:
        df_change_motivations.to_csv('intermediate/change_motivations.csv',header=True,encoding='utf-8',index=False)
        df_change_motivations_m = df_change_motivations
        df_change_motivations_m['dimension'] = "Change Motivation"        
        dimensions.append(df_change_motivations_m)
    if not df_fears is None and not df_fears.empty:
        df_fears.to_csv('intermediate/fears.csv',header=True,encoding='utf-8',index=False)
        df_fears_m = df_fears
        df_fears_m['dimension'] = "Fear"        
        dimensions.append(df_fears_m)
    if not df_privations is None and not df_privations.empty:
        df_privations.to_csv('intermediate/privations.csv',header=True,encoding='utf-8',index=False)
        df_privations_m = df_privations
        df_privations_m['dimension'] = "Privation"        
        dimensions.append(df_privations_m)
    if not df_painpoints is None and not df_painpoints.empty:
        df_painpoints.to_csv('intermediate/painpoints.csv',header=True,encoding='utf-8',index=False)
        df_painpoints_m = df_painpoints
        df_painpoints_m['dimension'] = "Pain Point"        
        dimensions.append(df_painpoints_m)
    if not df_people is None and not df_people.empty:
        df_people.to_csv('intermediate/people.csv',header=True,encoding='utf-8',index=False)
        df_people_m = df_people
        df_people_m['dimension'] = "People"        
        dimensions.append(df_people_m)
    if not df_activities is None and not df_activities.empty:
        df_activities.to_csv('intermediate/activities.csv',header=True,encoding='utf-8',index=False)
        df_activities_m = df_activities
        df_activities_m['dimension'] = "People"        
        dimensions.append(df_activities_m)

    if len(dimensions) > 0:
        df_dimensions = pd.concat(dimensions)
        df_dimensions_filtered = df_dimensions[df_dimensions['active'] == True]
        df_dimensions_filtered.to_csv('intermediate/dimensions.csv',header=True,encoding='utf-8',index=False)

    st.info("Data Saved")

if not 'df_fears' in st.session_state:
    df_fears = pd.DataFrame()
    st.session_state.df_fears = df_fears 
else:
    df_fears = st.session_state.df_fears

if not 'df_purchase_causes' in st.session_state:
    df_purchase_causes = pd.DataFrame()
    st.session_state.df_purchase_causes = df_purchase_causes 
else:
    df_purchase_causes = st.session_state.df_purchase_causes

if not 'df_purchase_motivations' in st.session_state:
    df_purchase_motivations = pd.DataFrame()
    st.session_state.df_purchase_motivations = df_purchase_motivations 
else:
    df_purchase_motivations = st.session_state.df_purchase_motivations

if not 'df_change_causes' in st.session_state:
    df_change_causes = pd.DataFrame()
    st.session_state.df_change_causes = df_change_causes 
else:
    df_change_causes = st.session_state.df_change_causes

if not 'df_change_motivations' in st.session_state:
    df_change_motivations = pd.DataFrame()
    st.session_state.df_change_motivations = df_change_motivations 
else:
    df_change_motivations = st.session_state.df_change_motivations

if not 'df_privations' in st.session_state:
    df_privations = pd.DataFrame()
    st.session_state.df_privations = df_privations 
else:
    df_privations = st.session_state.df_privations

if not 'df_painpoints' in st.session_state:
    df_painpoints = pd.DataFrame()
    st.session_state.df_painpoints = df_painpoints 
else:
    df_painpoints = st.session_state.df_painpoints

if not 'df_people' in st.session_state:
    df_people = pd.DataFrame()
    st.session_state.df_people = df_people 
else:
    df_people = st.session_state.df_people

if not 'df_activities' in st.session_state:
    df_activities = pd.DataFrame()
    st.session_state.df_activities = df_activities 
else:
    df_activities = st.session_state.df_activities


c1_0, c2_0 = st.columns([6,6])

with st.container():
    with c1_0:
        # PURCHASE CAUSES         
        st.subheader('Purchase Causes')
        with st.container():
            annotated_purchase_causes = st.data_editor(df_purchase_causes,key = 'annotated_purchase_causes') 
        with st.container():
            btn_purchase_causes = st.button('Refresh Purchase Causes', key="load_purchase_causes" , on_click=refresh_purchase_causes , args = (product_data,person_data,model,) )
        # PURCHASE MOTIVATIONS         
        st.subheader('Purchase Motivations')
        with st.container():
            annotated_purchase_motivations = st.data_editor(df_purchase_motivations,key = 'annotated_purchase_motivations') 
        with st.container():
            btn_purchase_motivations = st.button('Refresh Purchase Motivations', key="load_purchase_motivations" , on_click=refresh_purchase_motivations , args = (product_data,person_data,model,) )
        # CHANGE CAUSES         
        st.subheader('Change  Causes')
        with st.container():
            annotated_change_causes = st.data_editor(df_change_causes,key = 'annotated_change_causes') 
        with st.container():
            btn_change_causes = st.button('Refresh Change Causes', key="load_change_causes" , on_click=refresh_change_causes , args = (product_data,person_data,model,) )
        # CHANGE MOTIVATIONS         
        st.subheader('Change Motivations')
        with st.container():
            annotated_change_motivations = st.data_editor(df_change_motivations,key = 'annotated_change_motivations') 
        with st.container():
            btn_change_motivations = st.button('Refresh Change Motivations', key="load_change_motivations" , on_click=refresh_change_motivations , args = (product_data,person_data,model,) )
        # FEARS 
        st.subheader('Fears')
        with st.container():
            annotated_fears = st.data_editor(df_fears,key = 'annotated_fears') 
        with st.container():
            btn_load_fears = st.button('Refresh Fears', key="load_fears" , on_click=refresh_fears , args = (product_data,person_data,model,) )
        # PRIVATIONS 
        st.subheader('Privations')
        with st.container():
            annotated_privations = st.data_editor(df_privations,key = 'annotated_privations') 
        with st.container():
            btn_load_privations = st.button('Refresh Privations', key="load_privations" , on_click=refresh_privations , args = (product_data,person_data,model,) )
        # PAIN POINTS 
        st.subheader('Pain Points')
        with st.container():
            annotated_painpoints = st.data_editor(df_painpoints,key = 'annotated_painpoints') 
        with st.container():
            btn_load_painpoints = st.button('Refresh Pain Points', key="load_painpoints" , on_click=refresh_painpoints , args = (product_data,person_data,model,) )
        # PEOPLE 
        st.subheader('People')
        with st.container():
            annotated_people = st.data_editor(df_people,key = 'annotated_people') 
        with st.container():
            btn_load_people = st.button('Refresh People', key="load_people" , on_click=refresh_people , args = (product_data,person_data,model,) )
        # ACTIVITIES 
        st.subheader('Activities')
        with st.container():
            annotated_activities = st.data_editor(df_activities,key = 'annotated_activities') 
        with st.container():
            btn_load_activities = st.button('Refresh Activities', key="load_activities" , on_click=refresh_activities , args = (product_data,person_data,model,) )
    with c2_0:    
        st.button('Save Dimensions', key="save_dimensions" , on_click=save_dimensions , args = (annotated_purchase_causes,annotated_purchase_motivations, annotated_change_causes, annotated_change_motivations, annotated_fears, annotated_privations,annotated_painpoints, annotated_people, annotated_activities) )
