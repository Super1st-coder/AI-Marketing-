import pandas as pd
import streamlit as st
import extra_streamlit_components as stx
import json
import itertools

import os   
import openai

OPENAI_KEY = 'OPENAI_API_KEY_REDACTED'

from jinja2 import Environment, FileSystemLoader
environment = Environment(loader=FileSystemLoader("templates/"))

# from llama_index import StorageContext, load_index_from_storage

# def load_llm_model() : 
#     # rebuild storage context
#     storage_context = StorageContext.from_defaults(persist_dir='./storage')
#     # load index
#     index = load_index_from_storage(storage_context)
#     query_engine_loaded = index.as_query_engine()
#     return query_engine_loaded

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



st.set_page_config(layout="wide", page_title="Discovery", page_icon="🧮")

st.title("✍️ Interests Discovery Process")
st.caption("Discover new data about person interests")

# if 'df_interest0' not in st.session_state:
#     st.session_state.df_interest0 = pd.DataFrame()
df_interest0 = pd.DataFrame()
df_interest1 = pd.DataFrame()
df_interest2 = pd.DataFrame()

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


def get_data_level_0(product_data,person_data,model):
    print("LOADING LEVEL 0 ...")

    t_prompt = environment.get_template("general_interests.txt")
    template_content  = t_prompt.render({ 'person_name' : person_data})
    
    # llm_response = model.query(template_content)
    llm_response = model.send_query(template_content)
    print(llm_response)
    json_data = json.loads(llm_response)

    df_interest0 = pd.DataFrame.from_records(json_data['result'])
    df_interest0['active'] = False

    return df_interest0

def get_data_level_1(product_data,person_data,model,df):
    print("LOADING LEVEL 1 ...")

    if not df.empty:
        df_filtered = df[df['active'] == True]
        all_results = []
        for index, row in df_filtered.iterrows():
            print(row)
            t_prompt = environment.get_template("subinterests.txt")
            general_interest = row['title']
            template_content  = t_prompt.render({ 'person_name' : person_data, 'general_interest' : general_interest})
        
            # llm_response = model.query(template_content)
            llm_response = model.send_query(template_content)
            print(llm_response)
            json_data = json.loads(llm_response)

            print(".")

            for json_o in json_data['result']:
                json_o['general_interest'] = general_interest

            all_results.append(json_data['result'])

        if (len(all_results) > 0):
            all_json = list(itertools.chain.from_iterable(all_results))
            df_interest1 = pd.DataFrame.from_records(all_json)            
            df_interest1['active'] = False
        else:
            df_interest1 = pd.DataFrame()
    else:         
        df_interest1 = pd.DataFrame()

    return df_interest1

def get_data_level_2(product_data,person_data,model,df):
    print("LOADING LEVEL 2 ...")

    if not df.empty:
        df_filtered = df[df['active'] == True]
        all_results = []
        for index, row in df_filtered.iterrows():
            print(row)
            t_prompt = environment.get_template("interests_products.txt")
            general_interest = row['general_interest']
            subinterest = row['title']
            template_content  = t_prompt.render({ 'person_name' : person_data, 'subinterest' : subinterest, 'product_name' : product_data })
        
            # llm_response = model.query(template_content)
            llm_response = model.send_query(template_content)
            json_data = json.loads(llm_response)

            for json_o in json_data['result']:
                json_o['general_interest'] = general_interest
                json_o['subinterest'] = subinterest

            print(".")
            all_results.append(json_data['result'])

        if (len(all_results) > 0):
            all_json = list(itertools.chain.from_iterable(all_results))
            df_interest2 = pd.DataFrame.from_records(all_json)            
            df_interest2['active'] = False
        else:
            df_interest2 = pd.DataFrame()
    else:         
        df_interest2 = pd.DataFrame()
    
    return df_interest2


def refresh_level_0(product_data,person_data,model):
    df_interest0 = get_data_level_0(product_data,person_data,model)
    df_interest0['active'] = False
    st.session_state.df_interest0 = df_interest0 

    df_interest1 = pd.DataFrame()
    st.session_state.df_interest1 = df_interest1

    df_interest2 = pd.DataFrame()
    st.session_state.df_interest2 = df_interest2 


def refresh_level_1(product_data,person_data,model,df):
    df_interest1 = get_data_level_1(product_data,person_data,model,df)
    st.session_state.df_interest1 = df_interest1 

    df_interest2 = pd.DataFrame()
    st.session_state.df_interest2 = df_interest2 


def refresh_level_2(product_data,person_data,model,df):
    df_interest2 = get_data_level_2(product_data,person_data,model,df)
    st.session_state.df_interest2 = df_interest2 

def save_interests(df_level0,df_level1,df_level2):
    df_level0.to_csv('intermediate/general_interests.csv',header=True,encoding='utf-8')
    df_level1.to_csv('intermediate/subinterests.csv',header=True,encoding='utf-8')
    df_level2.to_csv('intermediate/interests_product.csv',header=True,encoding='utf-8')


###### LEVEL 0 ###### 
st.subheader('General Interests')

if not 'df_interest0' in st.session_state:
    # df_interest0 = get_data_level_0(product_data,person_data,model)
    df_interest0 = pd.DataFrame()
    st.session_state.df_interest0 = df_interest0 
else:
    df_interest0 = st.session_state.df_interest0

c1_0, c2_0 = st.columns(2)

with st.container():
    annotated_interest0 = st.data_editor(df_interest0,key = 'annotated_interest0') 

with st.container():
    btn_load_interest0 = c1_0.button('Refresh General Interests', key="load_interest0" , on_click=refresh_level_0 , args = (product_data,person_data,model,) )

###### LEVEL 1 ###### 
st.subheader('Sub Interests')
if not 'df_interest1' in st.session_state:
    df_interest1 = get_data_level_1(product_data,person_data,model,annotated_interest0)
    st.session_state.df_interest1 = df_interest1 
else:
    df_interest1 = st.session_state.df_interest1
# df_interest0 = st.session_state.df_interest0

c1_1, c2_1 = st.columns(2)
with st.container():
    annotated_interest1 = st.data_editor(df_interest1,key = 'annotated_interest1') 

with st.container():
    btn_load_interest1 = c1_1.button('Refresh Sub Interests', key="load_interest1" , on_click=refresh_level_1 , args = (product_data,person_data,model,annotated_interest0,) )

###### LEVEL 2 ###### 
st.subheader('Interests by Product')
if not 'df_interest2' in st.session_state:
    df_interest2 = get_data_level_2(product_data,person_data,model,annotated_interest1)
    st.session_state.df_interest2 = df_interest2 
else:
    df_interest2 = st.session_state.df_interest2
# df_interest0 = st.session_state.df_interest0
# df_interest1 = st.session_state.df_interest1

c1_2, c2_2 = st.columns(2)
with st.container():
    annotated_interest2 = st.data_editor(df_interest2) 

with st.container():    
    btn_load_interest2 = c1_2.button('Interests by Product', key="load_interest2" , on_click=refresh_level_2 , args = (product_data,person_data,model,annotated_interest1,) )
    btn_save_interests = c2_2.button('Save - Interests by Product', key="save_interest2" , on_click=save_interests , args = (annotated_interest0,annotated_interest1,annotated_interest2,) )
