import streamlit as st
import os
from app.repository.marketing import ProjectRepository, AccountRepository,SurveyRepository,BPersonaSurveyRepository, ConsultorSurveyRepository, ProductoSurveyRepository, BrandRepository
from app.use_cases.project import ProjectManager,PromptManager
import pandas as pd
from app.models.entity import contentlist_to_pandas
from streamlit_modal import Modal

from streamlit_extras.add_vertical_space import add_vertical_space 

from menu import menu_with_redirect

menu_with_redirect()

cancel_operation = st.button(' Back ')
if cancel_operation:
    st.switch_page('pages/dashboard.py')

st.title("Project")
st.caption("Project Definition")

projectManager = ProjectManager()

account = None
if 'account' in st.session_state:
    account = st.session_state.account
else:
    menu_with_redirect()

current_project = None
if 'current_project' in st.session_state and not st.session_state['current_project'] is None:
    current_project = st.session_state['current_project']     

cols_row1 = st.columns([3,2,1])
with cols_row1[0]:
    current_project['name'] = st.text_input(value=current_project['name'], label='Nombre')

with cols_row1[1]:
    project_types = ("B2B", "B2C")
    sel_project_type = project_types.index(current_project['project_type'])
    current_project['project_type'] = st.selectbox('Tipo', project_types,sel_project_type, disabled=True)

with cols_row1[2]:
    save_object = st.button(' Update ')
    if save_object:
        projectManager.save(current_project)

add_vertical_space(2)

message_area = st.empty()
###################################################################

try: 
    bPersonaSurvey = projectManager.get_bperson_survey(current_project)
    productoSurvey = projectManager.get_product_survey(current_project)
    consultorSurvey = projectManager.get_consultor_survey(current_project)
    brand = projectManager.get_brand(current_project)
except Exception as e:
    menu_with_redirect()

st.session_state['bpersona_survey'] = bPersonaSurvey
st.session_state['producto_survey'] = productoSurvey
st.session_state['consultor_survey'] = consultorSurvey
st.session_state['brand'] = brand

#############################################################################################      

columns_contents  = st.columns(3)
with columns_contents[0]:

    container_izq = st.container(border=True)
    with container_izq:
        st.markdown("### Surveys")

        columns_cuestionarios  = st.columns(3)
        with columns_cuestionarios[0]:
            view_bpersona = st.button('Buyer Person')
        with columns_cuestionarios[1]:
            view_producto = st.button('Product')
        with columns_cuestionarios[2]:
            view_consultor = st.button('Consultant')

#############################################################################################      

with columns_contents[1]:
    container_central = st.container(border=True)
    with container_central:
        st.markdown("### Customization")
        view_brand = st.button('Brand Voice')

with columns_contents[2]:
    container_der = st.container(border=True)
    with container_der:
        st.markdown("### Agents")
        view_build_agent = st.button('Build Project Agent')

container_operaciones = st.container(border=True)
with container_operaciones:
    st.markdown("### Herosphere")
    columns_operaciones  = st.columns(6)

    with columns_operaciones[0]:
        execute_journey_bpersona = st.button('Make BPerson Journey')


#############################################################################################      

if view_bpersona:
    st.session_state['bpersona_survey'] = bPersonaSurvey
    if current_project['project_type'] == 'B2C':
        st.switch_page('pages/b2c_bpersona_survey.py')
    elif current_project['project_type'] == 'B2B':
        st.switch_page('pages/b2b_bpersona_survey.py')

if view_producto:
    st.session_state['producto_survey'] = productoSurvey
    if current_project['project_type'] == 'B2C':
        st.switch_page('pages/b2c_producto_survey.py')
    elif current_project['project_type'] == 'B2B':
        st.switch_page('pages/b2b_producto_survey.py')

if view_consultor:
    st.session_state['consultor_survey'] = consultorSurvey
    if current_project['project_type'] == 'B2C':
        st.switch_page('pages/b2c_consultor_survey.py')
    elif current_project['project_type'] == 'B2B':
        st.switch_page('pages/b2b_consultor_survey.py')

if view_brand:
    st.session_state['brand'] = brand
    st.switch_page('pages/brand.py')

#############################################################################################      

import time

if view_build_agent: 
    # Check if is possible generate agents for the project 
    if projectManager.can_generate_agents(current_project): 
        try: 
            projectManager.generate_agent(current_project)
            st.toast('Agents are Ready', icon="✅")
            time.sleep(.5)
        except Exception as e:
            message_area.error('Error Desconocido - Favor contactar con el Administrador del Sistema')
    else:
        message_area.error('NO se pueden generar los Agentes, esto se debe a que no ha guardado los cuestionarios de Buyer Persona, Producto, Consultor o Marca, tambien es posible que ya halla iniciado un proceso de generacion de contenido para BPerson Journey')

if execute_journey_bpersona:
    if projectManager.can_make_bperson_journey(current_project):
        st.switch_page('pages/make_bperson_journey.py')
    else:
        message_area.error('NO se pueden iniciar el proceso de generacion de contenido para BPerson Journey, revise que los agentes esten generados y que los cuestionarios de Buyer Persona,Producto, Consultor y Marca esten completados')


