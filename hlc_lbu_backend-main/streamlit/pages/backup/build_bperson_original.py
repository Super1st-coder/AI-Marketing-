import streamlit as st
import os
import pandas as pd
from app.use_cases.project import AgentInteraction, ProjectManager
from app.models.entity import contentlist_to_pandas
from streamlit_modal import Modal

from menu import menu_with_redirect

menu_with_redirect()


projectManager = ProjectManager()


cancel_operation = st.button(' Back ')
if cancel_operation:
    st.switch_page('pages/project.py')

st.title("✍️ Make BPerson Journey")
st.caption("BPerson Journey")

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


if not 'df_bpersons' in st.session_state:
    df_bpersons = projectManager.get_bpersons(current_project)
    if len(df_bpersons) == 0:
        df_bpersons = pd.DataFrame([],columns=['Name', 'Age', 'Occupation'])

    st.session_state.df_bpersons = df_bpersons 
else:
    df_bpersons = st.session_state.df_bpersons    


########################################################################################


def get_bpersons_from_strapi(current_project):
    print("LOADING BPERSONS")
    df_bpersons =  projectManager.get_bpersons(current_project)

    st.session_state.df_bpersons = df_bpersons     
    return df_bpersons

def generate_bpersons_from_aigent(current_project,df_bpersons):
    print("REFRESHING BPERSONS")

    df_bpersons_fromai = projectManager.get_bpersons_from_aiagent(current_project)
    if len(df_bpersons_fromai) > 0:
        if len(df_bpersons) > 0:
            df_bpersons = pd.concat([df_bpersons,df_bpersons_fromai]) 
        else:
            df_bpersons = df_bpersons_fromai        
    
    st.session_state.df_bpersons = df_bpersons 

def save_all(current_project,df_bpersons):
    if len(df_bpersons) > 0:
        projectManager.save_dataframe_bperson(current_project,df_bpersons)
    else:
        print('NOTHING TO SAVE ...')


def make_bperson_suggestions(df_bpersons,bperson):
    print("MAKING SUGGESTIONS BPERSONS")
    if not df_bpersons is None and not bperson is None:
        variation_name  = bperson['Name']

        text_attributes = [f"{key}: {value}" for key,value in bperson.items()]
        variation_text  = "\n".join(text_attributes)

        variations = projectManager.generate_new_bpersons_using_another(current_project,variation_name,variation_text)

        if not df_bpersons.empty:
            if len(variation_name) > 0:
                df_bpersons = pd.concat([df_bpersons,variations]) 
        else:
            df_bpersons = variations

        st.session_state.df_bpersons = df_bpersons


########################################################################################

selection_bperson = None
df_selection = None
original_text = ''

columns_contents  = st.columns(2)
# with columns_contents[0]:
container_izq = st.container(border=True)
with container_izq:
    st.markdown("### Buyer Person Suggestion")
    columns_operations = st.columns(3)

    with columns_operations[0]:        
        st.button('Generate from ChatGPT', on_click=generate_bpersons_from_aigent, args=(current_project,df_bpersons,))


    selection_bperson = st.dataframe(df_bpersons
                                        ,key="Name"
                                        ,on_select="rerun"
                                        ,column_config={ "Name": "Name", "Occupation" : "Occupation", "Age" : "Age" }
                                        ,hide_index=True
                                        , selection_mode="single-row" ) 
    
    with columns_operations[1]:
        st.button('Save All',key='save_all', on_click=save_all, args=(current_project,df_bpersons) )

    with columns_operations[2]:

        current_selection = selection_bperson.selection

        if not current_selection is None: 
            selected_rows = current_selection['rows']

            if len(selected_rows) > 0 :
                selected_index = selected_rows[0]
                df_selection = df_bpersons.iloc[selected_rows[0]]

                st.button('Make Suggestions!',key='make_suggestions_bpersons', on_click=make_bperson_suggestions, args = (df_bpersons,df_selection,))


