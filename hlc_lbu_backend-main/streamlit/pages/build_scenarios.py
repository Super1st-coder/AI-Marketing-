import streamlit as st
import os
import pandas as pd
from app.use_cases.project import ProjectManager
from app.models.entity import contentlist_to_pandas
from streamlit_modal import Modal

from streamlit_extras.add_vertical_space import add_vertical_space 
from streamlit_extras.stylable_container import stylable_container 

from menu import menu_with_redirect

menu_with_redirect()

cancel_operation = st.button(' Back ')
if cancel_operation:
    st.switch_page('pages/build_bperson.py')

st.title("Build Scenarios")
st.caption("Build Scenarios")
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


current_bperson = None
original_bperson = None
if 'current_bperson' in st.session_state and not st.session_state['current_bperson'] is None:
    current_bperson = st.session_state['current_bperson']
    if 'id' in current_bperson:
        refreshed = projectManager.get_bperson_by_id(current_bperson['id'])
        if not refreshed is None:
            current_bperson = refreshed
    original_bperson = current_bperson.copy()
else:
    menu_with_redirect()

try:
    salesProcessSurvey = projectManager.get_sales_process_survey(current_bperson)
    st.session_state['sales_process_survey'] = salesProcessSurvey

    productoSurvey = projectManager.get_product_survey(current_project)
    st.session_state['producto_survey'] = productoSurvey

    bperson_scenarios = projectManager.get_scenarios(current_bperson)
    st.session_state['bperson_scenarios'] = bperson_scenarios
except Exception as e:
    menu_with_redirect()

########################################################################################


def save_all(bperson,bperson_scenarios):
    print("SAVE")
    try:
        projectManager.save_dataframe_scenarios(bperson,bperson_scenarios)
    except Exception as e:
        message_area.error('Error Desconocido - Favor contactar con el Administrador del Sistema')

def generate_scenarios(current_project,bperson,producto,salesProcess):
    print("GENERATE SCENARIOS")
    try:
        bperson_scenarios = projectManager.get_scenarios_from_aiagent(current_project,bperson,producto,salesProcess)
        if not bperson_scenarios is  None:
            st.session_state.bperson_scenarios = bperson_scenarios
    except Exception as e:
        message_area.error('Error Desconocido - Favor contactar con el Administrador del Sistema')

def generate_new_scenario(current_project,current_bperson,productoSurvey,salesProcessSurvey,bperson_scenario):
    print('Generate NEW Scenario')
    try: 
        new_scenario = projectManager.generate_new_scenario_using_another(current_project,current_bperson,productoSurvey,salesProcessSurvey,bperson_scenario)
    except Exception as e:
        message_area.error('Error Desconocido - Favor contactar con el Administrador del Sistema')

def improve_scenario_text(current_project,current_bperson,productoSurvey,salesProcessSurvey,bperson_scenario,old_text,new_text):
    print('Improve Scenario')
    try:
        improved_scenario = projectManager.improve_text_scenario(current_project,current_bperson,productoSurvey,salesProcessSurvey,bperson_scenario,old_text,new_text)
    except Exception as e:
        message_area.error('Error Desconocido - Favor contactar con el Administrador del Sistema')


########################################################################################

container_bpersons = st.container(border=True) 
with container_bpersons:
    st.markdown(f"### {current_bperson['Name']}")
    st.caption(f"{current_bperson['Description']}")

container_scenarios = st.container(border=True) 
with container_scenarios:
    st.markdown("### Scenarios")
    columns_operations = st.columns(5)

    with columns_operations[0]:
        st.button('Save All',key='save_scenarios',on_click=save_all,args=(current_bperson,bperson_scenarios))

    with columns_operations[1]:
        st.button('Generate',key='generate_scenarios',on_click=generate_scenarios,args=(current_project,current_bperson,productoSurvey,salesProcessSurvey))

    message_area = st.empty()

    current_row =  1
    next_row = 1
    current_index_column =  0
    max_index_columns = 2
    columns = st.columns(max_index_columns + 1)
    for index,scenario in bperson_scenarios.iterrows():

        if next_row > current_row:
            columns = st.columns(max_index_columns + 1)
            current_index_column =  0
            current_row = next_row

        with columns[current_index_column]:
            dict_scenario = scenario.to_dict()

            count_activities = projectManager.count_activities(dict_scenario)


            background_color = 'white'
            if count_activities >= 10:
                background_color = 'green'

            css_style = f""" {{
                    background-color: {background_color};
                    border: 1px solid rgba(49, 51, 63, 0.2);
                    border-radius: 0.5rem;
                    padding: calc(1em - 1px)
            }}
            """

            # c = st.container(border=True)
            c = stylable_container(key=f'container_bperson_{index}',css_styles=css_style)

            with c:

                old_text = scenario['Description']
                with st.container():
                    scenario['Description'] = st.text_area(scenario['Name'],height=15, value=scenario['Description'])

                row_buttons = st.columns(3)
                with row_buttons[0]:
                    st.button('New',key=f'new_scenario_{index}',on_click=generate_new_scenario,args=(current_project,current_bperson,productoSurvey,salesProcessSurvey,scenario))

                with row_buttons[1]:
                    btn_activities = st.button('Activities',key=f'edit_activities_{index}')

                    if btn_activities:
                        print('Edit Activities')

                        st.session_state.current_scenario = dict_scenario
                        st.switch_page('pages/configure_scenario.py')

                with row_buttons[2]:
                    st.button('Improve',key=f'improve_scenario_{index}',on_click=improve_scenario_text,args=(current_project,current_bperson,productoSurvey,salesProcessSurvey,scenario,old_text,scenario['Description']))


        current_index_column = current_index_column + 1 
        if current_index_column > max_index_columns:
            next_row = next_row + 1
            