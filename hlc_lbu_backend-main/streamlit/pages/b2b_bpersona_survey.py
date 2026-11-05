import streamlit as st
import os
from app.repository.marketing import ProjectRepository, AccountRepository,B2BBPersonaSurveyRepository
from app.use_cases.project import ProjectManager,AgentManager
import pandas as pd
from app.models.entity import contentlist_to_pandas
from streamlit_modal import Modal

from streamlit_extras.add_vertical_space import add_vertical_space 

from menu import menu_with_redirect

menu_with_redirect()

cancel_operation = st.button(' Back ')
if cancel_operation:
    st.switch_page('pages/project.py')


st.title("B2B Buyer Person Survey")
st.caption("B2B Buyer Person")
add_vertical_space(2)

surveyRepository = B2BBPersonaSurveyRepository() 
agentManager = AgentManager()

account = None
if 'account' in st.session_state :
    account = st.session_state.account
else:
    menu_with_redirect()

current_project = None
if 'current_project' in st.session_state and not st.session_state['current_project'] is None:
    current_project = st.session_state['current_project']     
else:
    menu_with_redirect()

current_survey = None
if 'bpersona_survey' in st.session_state and not st.session_state['bpersona_survey'] is None:
    current_survey = st.session_state['bpersona_survey']     
else:
    menu_with_redirect()

df_survey = pd.read_csv('data/b2b-bpersona-survey/questions_final.csv' )
mandatory_fields = []

record_data = {}
if 'id' in current_survey:
    record_data['id'] = current_survey['id']

record_data['parent_ref'] = current_survey['parent_ref']

columns_buttons1 = st.columns(5)
with columns_buttons1[0]:
    save_object1 = st.button(' Save ',key='save1')

message_area = st.empty()

agentEntity = agentManager.get_by_project(current_project)
canEdit = (agentEntity == None)

for index,row in df_survey.iterrows():
    question_value = 0

    if row['is_title'] == False:
        if len(current_survey) > 0:
            question_value = current_survey[row['field']]
        mandatory = row['mandatory']
        if mandatory:
            mandatory_fields.append(row['field'])
        record_data[row['field']] = st.text_area(row['label'], value=question_value, height=3, max_chars=255,disabled=not canEdit)
    else:
        st.markdown('### '+ row['label'])

columns_buttons2  = st.columns(5)
with columns_buttons2[0]:
    save_object2 = st.button(' Save ',key='save2')

if save_object1 or save_object2:    
    # Check mandatory fields 
    is_correct = True
    for f in mandatory_fields:
        if f in record_data:
            if record_data[f] is None or record_data[f].strip() == '':
                is_correct = False
    if is_correct:
        try: 
            if 'id' in record_data:
                surveyRepository.update(record_data)    
            else:
                surveyRepository.create(record_data)    
            st.switch_page('pages/project.py')
        except Exception as e:
            message_area.error('Error Desconocido - Favor contactar con el Administrador del Sistema')
    else: 
        message_area.error('Por favor revise los datos de Formulario, No se han llenado alguno de los datos obligatorios. (Nombre del Buyer Persona) ')

