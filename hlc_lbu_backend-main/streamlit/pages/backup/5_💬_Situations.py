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



st.set_page_config(layout="wide", page_title="Situations", page_icon="🧮")

st.title("✍️ Situation Generation")
st.caption("Generate situations using selected Dimensions")


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

df_selected_dimensions = pd.DataFrame()
df_situations = pd.DataFrame()

def load_dimensions() : 
    df = pd.read_csv('intermediate/dimensions.csv' )
    df['active'] = False
    st.session_state.df_selected_dimensions = df     
    return df

###############################################################################

# if not 'df_selected_dimensions' in st.session_state:
df_selected_dimensions = load_dimensions()
st.session_state.df_selected_dimensions = df_selected_dimensions 
# else:
#     df_selected_dimensions = st.session_state.df_selected_dimensions

if not 'df_situations' in st.session_state:
    df_situations = pd.DataFrame()
    st.session_state.df_situations = df_situations 
else:
    df_situations = st.session_state.df_situations

def transform_list(l_description):
    if type(l_description) == list:
        list_elements = ['- %s' % s for s in l_description]
        return '\n'.join(list_elements)
    else:
        return str(l_description)

def get_situations(product_data,person_data,model,df):
    print("LOADING SITUATIONS")

    if not df is None:

        df_filtered = df[df['active'] == True]
        if not df_filtered.empty:

            json_entity = df_filtered.to_json(orient='records')       
            json_object = json.loads(json_entity)     


            t_prompt = environment.get_template("situations.txt")
            template_content  = t_prompt.render({ 'person_name' : person_data, 'product_name' : product_data, 'dimensions' : json_object})

            print(template_content)

            llm_response = model.send_query(template_content)

            print(llm_response)
            json_data = json.loads(llm_response)

            df_situations = pd.DataFrame.from_records(json_data['result'])

            df_situations['description'] = df_situations['description'].apply(lambda l_description: transform_list(l_description) )
            df_situations['active'] = False

            return df_situations

        else:
            return pd.DataFrame() 
    else:
        return pd.DataFrame()

def generate_situations(product_data,person_data,model,df):
    df_situations = get_situations(product_data,person_data,model,df)
    st.session_state.df_situations = df_situations 

def save_situations(df_results):
    # if not df_results is None and not df_results.empty:
    if not df_results is None:
        df_results.to_csv('intermediate/situations.csv',header=True,encoding='utf-8',index=False)


st.subheader('Selected Dimensions')
with st.container():
    annotated_selected_dimensions = st.data_editor(df_selected_dimensions,key = 'annotated_selected_dimensions') 
with st.container():
    c1_1, c2_1 = st.columns([6,6])
    btn_refresh_dimensions = c1_1.button('Refresh Dimensions', key="refresh_dimensions" , on_click=load_dimensions  )
    btn_generate_situations = c2_1.button('Generate Situations', key="generate_situations" , on_click=generate_situations , args = (product_data,person_data,model,annotated_selected_dimensions) )
# CREATED SITUATIONS         
st.subheader('Created Situations')
with st.container():
    annotated_situations = st.data_editor(df_situations,key = 'annotated_situations') 
    # with c2_0:0
st.button('Save Situations', key="save_situations" , on_click=save_situations , args = (annotated_situations,) )
