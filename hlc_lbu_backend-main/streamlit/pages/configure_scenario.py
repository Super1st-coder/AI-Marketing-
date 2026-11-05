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
    st.switch_page('pages/build_scenarios.py')

st.title("Configure Scenario")
st.caption("Configure Scenario")
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
if 'current_bperson' in st.session_state and not st.session_state['current_bperson'] is None:
    current_bperson = st.session_state['current_bperson']
else:
    menu_with_redirect()


current_scenario = None
if 'current_scenario' in st.session_state and not st.session_state['current_scenario'] is None:
    current_scenario = st.session_state['current_scenario']
else:
    menu_with_redirect()

try:
    productoSurvey = projectManager.get_product_survey(current_project)
    st.session_state['producto_survey'] = productoSurvey
except Exception as e:
    menu_with_redirect()

try:
    scenario_activities = projectManager.get_scenario_activities(current_scenario)
    st.session_state['scenario_activities'] = scenario_activities
except Exception as e:
    menu_with_redirect()

########################################################################################


def generate_activities(current_project,bperson,product,bperson_scenario):
    print("Generate Activities")
    try:
        scenario_activities = projectManager.generate_scenario_activities(current_project,bperson,product,bperson_scenario)
    except Exception as e:
        message_area.error('Error Desconocido - Favor contactar con el Administrador del Sistema')

def improve_text_activity(current_project,current_bperson,producto,bperson_scenario,activity,old_text,new_text):
    print('Improve Text Activity')
    try:
        improved_activity = projectManager.improve_text_activity(current_project,current_bperson,producto,bperson_scenario,activity,old_text,new_text)
    except Exception as e:
        message_area.error('Error Desconocido - Favor contactar con el Administrador del Sistema')


########################################################################################


@st.experimental_dialog("Edit Activity", width="large")
def popup_edit_activity(current_project, bperson, scenario, activity):

    message_area_dialog = st.empty()
    
    activity['Name'] = st.text_input('Title', activity['Name'] )
    activity['Description'] = st.text_area('Description', activity['Description'] , height=15)

    add_vertical_space(1)
    columns_operations = st.columns(2,gap="small")

    with  columns_operations[0]:
        if st.button("Save"):
            if not activity['Name'].strip() == '' and not activity['Description'].strip() == '' :
                try:
                    projectManager.save_scenario_activity(scenario,activity)
                    st.rerun()
                except Exception as e:
                    message_area_dialog.error('Error Desconocido - Favor contactar con el Administrador del Sistema')
            else:
                message_area_dialog.error('Debe proporcionar todos los datos de la Actividad')


    with  columns_operations[1]:
        if st.button("Close"):
            st.rerun()

########################################################################################

columns_header = st.columns(2)

with columns_header[0]:
    with st.container(border=True):
        st.caption(f"Buyer Person")
        print(current_bperson)
        st.markdown(f"### {current_bperson['Name']}")
        st.caption(f"{current_bperson['Description']}")

with columns_header[1]:
    with st.container(border=True):
        st.caption(f"Scenario")
        st.markdown(f"### {current_scenario['Name']}")
        st.caption(f"{current_scenario['Description']}")


container_activities = st.container(border=True)

with container_activities:
    st.markdown("### Activities / Feelings")
    columns_operations = st.columns(2)
    message_area = st.empty()

    with columns_operations[0]:
        btn_new_actitity = st.button('New Activity',key='new_activity')
        if btn_new_actitity:
            new_activity = projectManager.new_scenario_actitiy(current_scenario)
            popup_edit_activity(current_project,current_bperson,current_scenario,new_activity)

    with columns_operations[1]:
        st.button('Generate',key='generate_activities',on_click=generate_activities,args=(current_project,current_bperson,productoSurvey,current_scenario))

    add_vertical_space(1)

    current_row =  1
    next_row = 1
    current_index_column =  0
    max_index_columns = 2
    columns = st.columns(max_index_columns + 1)
    for index,activity in scenario_activities.iterrows():

        if next_row > current_row:
            columns = st.columns(max_index_columns + 1)
            current_index_column =  0
            current_row = next_row

        with columns[current_index_column]:
            c = st.container(border=True)
            with c: 
                dict_activity = activity.to_dict()                

                old_text = dict_activity['Description']
                dict_activity['Description'] = st.text_area(dict_activity['Name'],height=15, value=dict_activity['Description'])

                row_buttons = st.columns(2)
                with row_buttons[0]:
                    btn_edit_activity = st.button('Edit',key=f'new_activity_{index}')
                    if btn_edit_activity:
                        popup_edit_activity(current_project, current_bperson, current_scenario, dict_activity)

                with row_buttons[1]:
                    new_text = dict_activity['Description']
                    st.button('Improve',key=f'improve_activity_{index}',on_click=improve_text_activity,args=(current_project, current_bperson, productoSurvey, current_scenario, dict_activity,old_text,new_text) )

        current_index_column = current_index_column + 1 
        if current_index_column > max_index_columns:
            next_row = next_row + 1
            