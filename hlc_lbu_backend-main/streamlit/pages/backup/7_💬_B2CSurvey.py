import pandas as pd
import streamlit as st
import extra_streamlit_components as stx
import json
import itertools
from strapi import strapi

import os   
import openai

from jinja2 import Environment, FileSystemLoader
environment = Environment(loader=FileSystemLoader("templates/"))

st.set_page_config(layout="wide", page_title="B2C Project Survey", page_icon="🧮")

st.title("✍️ B2C Project Survey")
st.caption("Formulario Proyecto B2C")

back = st.button('Back ... ')

if back:
    st.switch_page(page=)    


###############################################################################

attributes = strapi.get_content_type_attributes('b2c-project-survey')

print(attributes)

df_project_survey = pd.read_csv('data/b2c-project-survey_questions.csv' )
df_project_survey['value'] = ""

content_type_name = 'b2c-project-surveys'
survey_content = strapi.get_object_by_id(content_type_name,1) 

project_ref = 1

if survey_content is None:
    survey_content = {}

with st.container():
    save_data = st.button('Guardar')

    record_data = {}
    for index,row in df_project_survey.iterrows():
        question_value = 0        
        if len(survey_content) > 0:
            question_value = survey_content['attributes'][row['slug']]
        record_data[row['slug']] = st.text_area(row['line'], value=question_value, height=3)

    if save_data:
        record_data['project_ref'] = project_ref 
        strapi.create_object("b2c-project-surveys",{'data' : record_data })


