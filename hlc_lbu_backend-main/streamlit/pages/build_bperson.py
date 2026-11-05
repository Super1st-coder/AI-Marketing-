import streamlit as st
import os
import pandas as pd
from app.use_cases.project import ProjectManager
from app.models.entity import contentlist_to_pandas
from streamlit_modal import Modal

from streamlit_extras.stylable_container import stylable_container 
from streamlit_extras.add_vertical_space import add_vertical_space 

from menu import menu_with_redirect

menu_with_redirect()

cancel_operation = st.button(' Back ')
if cancel_operation:
    st.switch_page('pages/make_bperson_journey.py')

st.title("Edit Buyer Person Attributes")
st.caption("BPerson Journey")
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
    bPersonSurvey = projectManager.get_bperson_survey(current_project)

    salesProcessSurvey = projectManager.get_sales_process_survey(current_bperson)
    st.session_state['sales_process_survey'] = salesProcessSurvey

    productoSurvey = projectManager.get_product_survey(current_project)
    current_product = projectManager.get_product(current_bperson)
    scenarioContexts = projectManager.get_scenario_contexts(current_bperson)
except Exception as e:
    menu_with_redirect()

########################################################################################

def save(current_project,entity):
    print("SAVE")
    try: 
        projectManager.save_bperson(current_project,entity)
    except Exception as e:
        message_area.error('Error Desconocido - Favor contactar con el Administrador del Sistema')

def improve(current_project,old_entity,new_entity):
    print("IMPROVE BPERSON")
    try:
        improved_bperson = projectManager.improve_bperson(current_project,old_entity,new_entity)
        if not improved_bperson is  None:
            st.session_state.current_bperson = improved_bperson
    except Exception as e:
        message_area.error('Error Desconocido - Favor contactar con el Administrador del Sistema')
    
def set_favorite(current_project,entity):
    print("SET FAVORITE")
    try:
        projectManager.set_fav_bperson(current_project,entity)
    except Exception as e:
        message_area.error('Error Desconocido - Favor contactar con el Administrador del Sistema')

def unset_favorite(current_project,entity):
    print("UNSET FAVORITE")
    try:
        projectManager.unset_fav_bperson(current_project,entity)
    except Exception as e:
        message_area.error('Error Desconocido - Favor contactar con el Administrador del Sistema')

########################################################################################

@st.experimental_dialog("Working Contexts", width="large")
def popup_select_context_for_scenarios(current_project, bperson, bperson_survey,product, scenario_contexts,sales_process):
    columns_operations = st.columns(2)
    message_area_dialog1 = st.empty()
    with columns_operations[0]:
        btn_generate_context_scenarios = st.button('Generate',key='generate_scenarios')
        if btn_generate_context_scenarios:
            try: 
                scenario_contexts = projectManager.generate_scenario_contexts(current_project,bperson,bperson_survey,product)
                st.rerun()
            except Exception as e:
                message_area_dialog1.error('Error Desconocido - Favor contactar con el Administrador del Sistema')


    current_row =  1
    next_row = 1
    current_index_column =  0
    max_index_columns = 2
    columns = st.columns(max_index_columns + 1)
    for index,row in scenario_contexts.iterrows():
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

            c = stylable_container(key=f'container_scenario_context_{index}',css_styles=css_style)

            with c:
                
                current_row_data = row.to_dict()
                
                row_content = st.columns(1)
                with row_content[0]:
                    st.markdown(f"#### {current_row_data['Name']}")            
                    st.text_area('Description',key=f'description_{index}' , value=current_row_data['Description'],disabled=True)
  
                row_buttons = st.columns(1)
                with row_buttons[0]:
                    btn_fill_sales_process = st.button('Fill Sales Process',key=f'fill_sales_process_{index}')
                    if btn_fill_sales_process:
                        try: 
                            projectManager.autofill_sales_process_using_context(current_project,bperson,bperson_survey,product,current_row_data,sales_process)                        
                            st.rerun()
                        except Exception as e:
                            message_area_dialog1.error('Error Desconocido - Favor contactar con el Administrador del Sistema')


        current_index_column = current_index_column + 1 
        if current_index_column > max_index_columns:
            next_row = next_row + 1


    columns_operations = st.columns(2,gap="small")
    with  columns_operations[0]:
        if st.button("Close"):
            st.rerun()

########################################################################################

@st.experimental_dialog("Description for Product", width="large")
def popup_edit_product(current_project, bperson, bperson_survey, product, product_survey ):

    st.markdown(f"### {product['Name']}")

    text_long_description = "" 
    if 'Long Description' in product and not product['Long Description'] is None:
        text_long_description = product['Long Description']

    columns_actions = st.columns([4,1])
    add_vertical_space(1)

    message_area_dialog2 = st.empty()

    with  columns_actions[0]:
        current_long_description = st.empty()
        edit_long_description = current_long_description.text_area('Long Description', text_long_description , height=15,key='long_description_product_1')

    with  columns_actions[1]:
        btn_generate = st.button("Generate",key="generate_long_description")
        btn_improve = st.button("Improve",key="improve_long_description")

        if btn_generate:
            try: 
                new_text = projectManager.generate_longtext_product(current_project,bperson,bperson_survey,product,product_survey)
                edit_long_description = current_long_description.text_area('Long Description', new_text['Text'], height=15,key='long_description_product_2')
            except Exception as e:
                message_area_dialog2.error('Error Desconocido - Favor contactar con el Administrador del Sistema')

        if btn_improve:
            try: 
                modified_text = edit_long_description
                improved_text = projectManager.improve_longtext_product(current_project,bperson,product,text_long_description,modified_text)
                edit_long_description = current_long_description.text_area('Long Description', improved_text['Text'], height=15,key='long_description_product_3')
                text_long_description = improved_text['Text']
            except Exception as e:
                message_area_dialog2.error('Error Desconocido - Favor contactar con el Administrador del Sistema')


    columns_operations = st.columns(2,gap="small")

    with  columns_operations[0]:
        if st.button("Close"):
            st.rerun()

########################################################################################


omit_fields = ['id','is_favorite','from_another','was_improved','parent_ref','Long Description']
container_center = st.container(border=True)
with container_center:
    columns_operations = st.columns(7)
    message_area = st.empty()

    with columns_operations[0]:
        st.button('Save',key='save_bperson',on_click=save,args=(current_project,current_bperson,))

    with columns_operations[1]:
        st.button('Improve',key='improve_bperson',on_click=improve,args=(current_project,original_bperson,current_bperson))

    with columns_operations[2]:
        if current_bperson['is_favorite'] == False:
            st.button('Set Favorite',key='set_favorite',on_click=set_favorite,args=(current_project,current_bperson,) )

        if current_bperson['is_favorite'] == True:
            st.button('Unset Favorite',key='unset_favorite',on_click=unset_favorite,args=(current_project,current_bperson,) )

    with columns_operations[3]:
        btn_product_description = st.button('Product',key='product_description')
        if btn_product_description:
            popup_edit_product(current_project, current_bperson, bPersonSurvey, current_product, productoSurvey)        

    with columns_operations[4]:
        btn_working_context = st.button('Working Contexts',key='working_context')
        if btn_working_context:
            print("GENERATE SCENARIOS CONTEXT")
            popup_select_context_for_scenarios(current_project,current_bperson,bPersonSurvey, productoSurvey,scenarioContexts,salesProcessSurvey)

    with columns_operations[5]:
        btn_sales_process = st.button('Sales Process Survey',key='sales_process')
        if btn_sales_process:
            if 'id' in current_bperson and not current_bperson['id'] is None:
                st.switch_page('pages/sales_process_survey.py')        
            else:
                message_area.error('Debe primero Guardar el Buyer Persona para definir su proceso de Venta')

    with columns_operations[6]:
        btn_build_scenarios = st.button('Build Scenarios',key='build_scenarios')
        if btn_build_scenarios:
            if not ('id' in current_bperson and not current_bperson['id'] is None):
                message_area.error('Debe primero Guardar el Buyer Persona para definir su proceso de Venta')
            elif not ('id' in salesProcessSurvey and not salesProcessSurvey['id'] is None):
                message_area.error('Debe primero guardar el Proceso de Venta de  Buyer Persona para definir los escenarios de ventas')
            else:
                st.switch_page('pages/build_scenarios.py')        


    for key,value in current_bperson.items():
        if not key in omit_fields:
            item_value = value
            disabled = False 
            if key == 'Name':
                disabled = True
            current_bperson[key] = st.text_area(key, value=item_value, height=3,disabled=disabled)




