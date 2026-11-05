import streamlit as st
import os
from app.repository.marketing import ProjectRepository, AccountRepository,B2CBPersonaSurveyRepository
from app.use_cases.project import ProjectManager
import pandas as pd
from app.models.entity import contentlist_to_pandas
from streamlit_modal import Modal

from streamlit_extras.add_vertical_space import add_vertical_space 

from menu import menu_with_redirect

menu_with_redirect()

cancel_operation = st.button(' Back ')
if cancel_operation:
    st.switch_page('pages/build_bperson.py')

st.title("Sales Process Survey")
st.caption("Sales Process Survey")
add_vertical_space(2)

projectManager = ProjectManager() 

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
if 'sales_process_survey' in st.session_state and not st.session_state['sales_process_survey'] is None:
    current_survey = st.session_state['sales_process_survey']     
else:
    menu_with_redirect()

current_bperson = None
original_bperson = None
if 'current_bperson' in st.session_state and not st.session_state['current_bperson'] is None:
    current_bperson = st.session_state['current_bperson']     
    original_bperson = current_bperson.copy()
else:
    menu_with_redirect()


########################################################################################

df_survey = pd.read_csv('data/sales-process/questions_final.csv' )
mandatory_fields = []

record_data = {}
if 'id' in current_survey:
    record_data['id'] = current_survey['id']

record_data['parent_ref'] = current_survey['parent_ref']


columns_buttons1 = st.columns(5)
with columns_buttons1[0]:
    save_object1 = st.button(' Save ',key='save1')

message_area = st.empty()

for index,row in df_survey.iterrows():
    question_value = 0

    if row['is_title'] == False:
        if len(current_survey) > 0:
            question_value = current_survey[row['field']]

        mandatory = row['mandatory']
        if mandatory:
            mandatory_fields.append(row['field'])

        record_data[row['field']] = st.text_area(row['label'], value=question_value, height=3)
    else:
        st.markdown('### '+ row['label'])

columns_buttons2  = st.columns(5)
with columns_buttons2[0]:
    save_object2 = st.button(' Save ',key='save2')

if save_object1 or save_object2:    
    is_correct = True
    for f in mandatory_fields:
        if f in record_data:
            if record_data[f] is None or record_data[f].strip() == '':
                is_correct = False
    if is_correct:
        try:
            projectManager.save_sales_process(current_bperson,record_data)
            st.switch_page('pages/build_bperson.py')
        except Exception as e:
            message_area.error('Error Desconocido - Favor contactar con el Administrador del Sistema')
    else:
        message_area.error('Por favor revise los datos de Formulario, No se han llenado alguno de los datos obligatorios.')


