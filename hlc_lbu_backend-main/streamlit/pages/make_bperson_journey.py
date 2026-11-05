import streamlit as st
import os
import pandas as pd
from app.use_cases.project import AgentInteraction, ProjectManager
from app.models.entity import contentlist_to_pandas
from streamlit_modal import Modal

from streamlit_extras.stylable_container import stylable_container 
from streamlit_extras.add_vertical_space import add_vertical_space 
from streamlit_extras.colored_header import colored_header 

from menu import menu_with_redirect

menu_with_redirect()

projectManager = ProjectManager()

cancel_operation = st.button(' Back ')
if cancel_operation:
    st.switch_page('pages/project.py')


st.title("Make BPerson Journey")
st.caption("BPerson Journey")
add_vertical_space(2)

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

try:
    df_bpersons = projectManager.get_bpersons(current_project)
    productoSurvey = projectManager.get_product_survey(current_project)
    bPersonSurvey = projectManager.get_bperson_survey(current_project)
except Exception as e:
    menu_with_redirect()

########################################################################################


def get_bpersons_from_strapi(current_project):
    print("LOADING BPERSONS")
    df_bpersons = pd.DataFrame()
    try:    
        df_bpersons =  projectManager.get_bpersons(current_project)
        st.session_state.df_bpersons = df_bpersons     
    except Exception as e:
        message_area.error('Error Desconocido - Favor contactar con el Administrador del Sistema')

    return df_bpersons

def generate_bpersons_from_aigent(current_project,df_bpersons):
    print("REFRESHING BPERSONS")
    df_bpersons = pd.DataFrame()
    try:
        df_bpersons_fromai = projectManager.get_bpersons_from_aiagent(current_project)
        if len(df_bpersons_fromai) > 0:
            if len(df_bpersons) > 0:
                df_bpersons = pd.concat([df_bpersons,df_bpersons_fromai]) 
            else:
                df_bpersons = df_bpersons_fromai        
    except Exception as e:
        message_area.error('Error Desconocido - Favor contactar con el Administrador del Sistema')

    st.session_state.df_bpersons = df_bpersons 

def save_all(current_project,df_bpersons):
    try:
        if len(df_bpersons) > 0:
            projectManager.save_dataframe_bperson(current_project,df_bpersons)
    except Exception as e:
        message_area.error('Error Desconocido - Favor contactar con el Administrador del Sistema')


def make_bperson_suggestions(current_project,bperson):
    print("MAKING SUGGESTIONS BPERSONS")
    try:
        variations = projectManager.generate_new_bpersons_using_another(current_project,bperson)
    except Exception as e:
        message_area.error('Error Desconocido - Favor contactar con el Administrador del Sistema')

def make_favorite(current_project,bperson):
    print("MAKE FAVORITE")
    try:
        projectManager.set_fav_bperson(current_project,bperson)
    except Exception as e:
        message_area.error('Error Desconocido - Favor contactar con el Administrador del Sistema')

def remove_favorite(current_project,bperson):
    print("REMOVE  FAVORITE")
    try:
        projectManager.unset_fav_bperson(current_project,bperson)
    except Exception as e:
        message_area.error('Error Desconocido - Favor contactar con el Administrador del Sistema')


@st.experimental_dialog("Long Description for BPerson", width="large")
def popup_edit_long_description_bperson(current_project, bperson, bperson_survey, product):
    message_area_dialog = st.empty()
    text_long_description = "" 
    if 'Long Description' in bperson and not bperson['Long Description'] is None:
        text_long_description = bperson['Long Description']

    columns_actions = st.columns([4,1])
    add_vertical_space(1)

    with  columns_actions[0]:
        current_long_description = st.empty()
        edit_long_description = current_long_description.text_area('Long Description', text_long_description , height=15)

    with  columns_actions[1]:
        btn_generate = st.button("Generate",key="generate_long_description")
        btn_improve = st.button("Improve",key="improve_long_description")

        if btn_generate:
            try:
                new_text = projectManager.generate_longtext_bperson(current_project,bperson,bperson_survey,product)
                edit_long_description = current_long_description.text_area('Long Description', new_text['Text'], height=15)
            except Exception as e:
                message_area_dialog.error('Error Desconocido - Favor contactar con el Administrador del Sistema')

        if btn_improve:
            try:
                modified_text = edit_long_description
                improved_text = projectManager.improve_longtext_bperson(current_project,bperson,product,text_long_description,modified_text)
                edit_long_description = current_long_description.text_area('Long Description', improved_text['Text'], height=15)
                text_long_description = improved_text['Text']
            except Exception as e:
                message_area.error('Error Desconocido - Favor contactar con el Administrador del Sistema')

    columns_operations = st.columns(2,gap="small")

    with  columns_operations[0]:
        if st.button("Close"):
            st.rerun()

########################################################################################


original_text = ''

main_container = st.container(border=True)

with main_container:
    message_area = st.empty()

    st.markdown("### Buyer Person Candidates")
    columns_operations = st.columns(4)

    with columns_operations[0]:        
        st.button('Generate', on_click=generate_bpersons_from_aigent, args=(current_project,df_bpersons,))

    with columns_operations[1]:
        st.button('Save All',key='save_all', on_click=save_all, args=(current_project,df_bpersons) )

    current_row =  1
    next_row = 1
    current_index_column =  0
    max_index_columns = 1
    columns = st.columns(max_index_columns + 1)
    for index,bperson in df_bpersons.iterrows():

        if next_row > current_row:
            columns = st.columns(max_index_columns + 1)
            current_index_column =  0
            current_row = next_row

        with columns[current_index_column]:

            # c = st.container(border=1)

            background_color = 'white'
            if bperson['is_favorite'] == True:
                background_color = 'green'


            css_style = f""" {{
                    background-color: {background_color};
                    border: 1px solid rgba(49, 51, 63, 0.2);
                    border-radius: 0.5rem;
                    padding: calc(1em - 1px)
            }}
            """

            c = stylable_container(key=f'container_bperson_{index}',css_styles=css_style)

            with c:

                current_bperson = bperson.to_dict()
                
                row_content = st.columns(1)
                with row_content[0]:
                    st.markdown(f"#### {bperson['Name']}")            
                    st.text_area('Description',key=f'description_{index}' , value=bperson['Description'],disabled=True)
                    st.text_input('Age',key=f'age_{index}' , value=bperson['Age'],disabled=True) 
                    st.text_input('Occupation',key=f'occupation_{index}' , value=bperson['Occupation'],disabled=True) 

                # old_text = scenario['Description']
                # scenario['Description'] = st.text_area(scenario['Name'],height=15, value=scenario['Description'])

                row_buttons = st.columns(4)
                with row_buttons[0]:
                    btn_edit_detail = st.button('Edit',key=f'edit_bperson_{index}')
                with row_buttons[1]:
                    st.button('New',key=f'suggest_new_version_{index}',on_click=make_bperson_suggestions, args = (current_project,bperson))
                with row_buttons[2]:
                    if not bperson['is_favorite'] :
                        st.button('Favorite',key=f'make_favorite_{index}',on_click=make_favorite, args = (current_project,current_bperson))
                    else:
                        st.button('UnFavorite',key=f'remove_favorite_{index}',on_click=remove_favorite, args = (current_project,current_bperson))
                with row_buttons[3]:
                    btn_longtext_bperson = st.button('Description',key=f'edit_longtext_bperson_{index}')
                    # ,on_click=edit_longtext, args = (current_project,bperson)


                if btn_edit_detail:
                    print("EDIT DETAILS")
                    st.session_state.current_bperson = current_bperson
                    st.switch_page('pages/build_bperson.py')

                if btn_longtext_bperson:
                    print("EDIT LONG TEXT BPERSON")
                    popup_edit_long_description_bperson(current_project,current_bperson,bPersonSurvey,productoSurvey)


        current_index_column = current_index_column + 1 
        if current_index_column > max_index_columns:
            next_row = next_row + 1
