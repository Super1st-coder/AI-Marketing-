import streamlit as st
import os
# from strapi import strapi 
from app.repository.marketing import ProjectRepository, AccountRepository
import pandas as pd
from app.models.entity import contentlist_to_pandas
from streamlit_modal import Modal

from streamlit_extras.add_vertical_space import add_vertical_space 

import streamlit as st
from menu import menu_with_redirect

menu_with_redirect()

st.title("HiLUCA Dashboard")
st.caption("Welcome to HiLUCA")
add_vertical_space(2)

accountRepository = AccountRepository()
projectRepository = ProjectRepository()

account = st.session_state.account

df_projects = pd.DataFrame(columns=['id','name','project_type'])
if not account is None:
    projects = projectRepository.get_by_account(account)
    if not projects is None and len(projects) > 0:
        df_projects = contentlist_to_pandas(projects)
        

message_area = st.empty()
col1, col2  = st.columns(2)
with col1:
    container_izq = st.container(border=True)
    with container_izq:
        st.markdown("### User Profile")
        user_data_markdown = f"""
| E-mail | Name | 
|:-------:|:-----|
|   {account['attributes']['email']}   |  {account['attributes']['name']}  |        
        """
        st.markdown(user_data_markdown)


current_selection  = None

@st.experimental_dialog("create-project")
def create_project(current_project):
    message_area_dialog = st.empty()

    current_project['name'] = st.text_input(value=current_project['name'], label='Nombre')

    project_types = ("B2B", "B2C")
    sel_project_type = project_types.index(current_project['project_type'])
    current_project['project_type'] = st.selectbox('Tipo', project_types,sel_project_type)

    columns_buttons  = st.columns(5)

    with columns_buttons[0]:
        save_object = st.button(' Save ')

    if save_object:
        try:
            if not current_project['name'].strip() == '':
                projectRepository.create(current_project)
                st.rerun()
            else:
                message_area_dialog.error('Debe proporcionar el nombre del Proyecto')
        except Exception as e:
            message_area.error('Error Desconocido - Favor contactar con el Administrador del Sistema')


    with columns_buttons[1]:
        cancel_operation = st.button(' Cancel ')
        
    if cancel_operation:
        st.rerun()


with col2:
    container_der = st.container(border=True)
    with container_der:
        st.markdown("### Projects")

        columns_buttons  = st.columns(5)        
        with columns_buttons[0]:
            new_project = st.button(' New ')

        if new_project:
            current_project = projectRepository.new(account)
            create_project(current_project)

        current_row =  1
        next_row = 1
        current_index_column =  0
        max_index_columns = 1
        columns = st.columns(max_index_columns + 1)
        for index,element in df_projects.iterrows():

            if next_row > current_row:
                columns = st.columns(max_index_columns + 1)
                current_index_column =  0
                current_row = next_row

            with columns[current_index_column]:
                c = st.container(border=True)
                with c:
                    dict_element = element.to_dict()                

                    st.markdown(f"##### {dict_element['name']}")

                    btn_edit_activity = st.button('Edit',key=f'edit_element_{index}')
                    if btn_edit_activity:
                        current_project = dict_element      
                        current_project['account_ref'] = account['id']
                        st.session_state['current_project'] = current_project
                        st.switch_page("pages/project.py")


            current_index_column = current_index_column + 1 
            if current_index_column > max_index_columns:
                next_row = next_row + 1        




