import streamlit as st
import os

from app.repository.marketing import ProjectRepository, AccountRepository,B2CConsultorSurveyRepository
from app.use_cases.project import AgentManager,ProjectManager

import pandas as pd
from app.models.entity import contentlist_to_pandas
from streamlit_modal import Modal

from streamlit_extras.add_vertical_space import add_vertical_space 
from streamlit_extras.stylable_container import stylable_container 

from menu import menu_with_redirect

menu_with_redirect()

cancel_operation = st.button(' Back ')
if cancel_operation:
    st.switch_page('pages/project.py')

st.title("B2C Consultant Survey")
st.caption("B2C Consultant")
add_vertical_space(2)

surveyRepository = B2CConsultorSurveyRepository() 
agentManager = AgentManager()
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
if 'consultor_survey' in st.session_state and not st.session_state['consultor_survey'] is None:
    current_survey = st.session_state['consultor_survey']     
else:
    menu_with_redirect()

df_survey = pd.read_csv('data/b2c-consultor-survey/questions_final.csv' )
mandatory_fields = []

record_data = {}
if 'id' in current_survey:
    record_data['id'] = current_survey['id']

record_data['parent_ref'] = current_survey['parent_ref']

consultor_suggestions = projectManager.get_consultor_suggestions(current_project)

########################################################################################

@st.experimental_dialog("Suggest Consultors", width="large")
def popup_select_suggest_consultors(current_project,consultor_suggestions):
    columns_operations = st.columns(2)
    message_area_dialog1 = st.empty()
    with columns_operations[0]:
        btn_generate_consultor_suggestions = st.button('Generate',key='generate_scenarios')
        if btn_generate_consultor_suggestions:
            try: 
                consultor_suggestions = projectManager.generate_consultor(current_project)
                st.rerun()
            except Exception as e:
                message_area_dialog1.error('Error Desconocido - Favor contactar con el Administrador del Sistema')


    current_row =  1
    next_row = 1
    current_index_column =  0
    max_index_columns = 2
    columns = st.columns(max_index_columns + 1)
    for index,row in consultor_suggestions.iterrows():
        if next_row > current_row:
            columns = st.columns(max_index_columns + 1)
            current_index_column =  0
            current_row = next_row

        with columns[current_index_column]:
            

            css_style = f""" {{
                    background-color: white;
                    border: 1px solid rgba(49, 51, 63, 0.2);
                    border-radius: 0.5rem;
                    padding: calc(1em - 1px)
            }}
            """

            c = stylable_container(key=f'container_consultor_suggestion_{index}',css_styles=css_style)

            with c:
                
                current_row_data = row.to_dict()
                
                row_content = st.columns(1)
                with row_content[0]:
                    st.markdown(f"#### {current_row_data['cual-es-el-nombre-del-consultor']}")            

                    st.markdown(f"{current_row_data['cual-es-el-titulo-universitario']}")            
                    st.markdown(f"{current_row_data['cual-es-su-puesto-de-trabajo-actual']}")            
                    st.markdown(f"{current_row_data['cuantos-anos-de-experiencia-tiene-en-este-ramo']}")            
  
                row_buttons = st.columns(1)
                with row_buttons[0]:
                    btn_fill_project_consultor = st.button('Fill Project Consultor',key=f'fill_project_consultor{index}')
                    if btn_fill_project_consultor:
                        try: 
                            projectManager.autofill_consultor_survey(current_project,current_row_data)                        

                            consultorSurvey = projectManager.get_consultor_survey(current_project)
                            st.session_state['consultor_survey'] = consultorSurvey            

                            st.rerun()
                        except Exception as e:
                            message_area_dialog1.error('Error Desconocido - Favor contactar con el Administrador del Sistema')


        current_index_column = current_index_column + 1 
        if current_index_column > max_index_columns:
            next_row = next_row + 1


    columns_operations = st.columns(2,gap="small")
    with  columns_operations[0]:
        if st.button("Close"):

            consultorSurvey = projectManager.get_consultor_survey(current_project)
            st.session_state['consultor_survey'] = consultorSurvey            

            st.rerun()

########################################################################################


columns_buttons1 = st.columns(5)
with columns_buttons1[0]:
    save_object1 = st.button(' Save ',key='save1')
with columns_buttons1[1]:
    btn_suggestions = st.button(' Suggestions ',key='suggestions')

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
        record_data[row['field']] = st.text_area(row['label'], value=question_value, height=3,max_chars=255, disabled=not canEdit)
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
            if 'id' in record_data:
                surveyRepository.update(record_data)    
            else:
                surveyRepository.create(record_data)    
            st.switch_page('pages/project.py')
        except Exception as e:
            message_area.error('Error Desconocido - Favor contactar con el Administrador del Sistema')        
    else: 
        message_area.error('Por favor revise los datos de Formulario, No se han llenado alguno de los datos obligatorios. (Nombre del Consultor) ')

if btn_suggestions:
    popup_select_suggest_consultors(current_project,consultor_suggestions)
