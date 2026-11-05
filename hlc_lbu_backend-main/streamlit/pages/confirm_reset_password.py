import streamlit as st
import os
# from strapi import strapi 
from app.use_cases.security import SecurityManager

import pandas as pd
from app.models.entity import contentlist_to_pandas
from streamlit_modal import Modal

import streamlit as st
from menu import menu
import time 

securityManager = SecurityManager()

st.set_page_config(layout="wide", page_title="Marketing Application", page_icon="🧮")

if 'hide_confirm_reset_password' not in st.session_state:
    st.session_state.hide_confirm_reset_password = False 
 

# Initialize st.session_state.role to None
if "role" not in st.session_state:
    st.session_state.role = None

params = st.query_params.to_dict()

def change_password():
    new_password = st.session_state._newpassword

    action_confirmed = securityManager.change_password(email,confirmation_code,new_password)

    if action_confirmed:
        st.session_state.hide_confirm_reset_password = True
        st.info(f'Se ha cambiado la contrasena a su cuenta {email} correctamente!')        
    else:
        st.error('Error al realizar el cambio de contrasena!')    

if 'confirmation_code' in params and 'email' in params:
    confirmation_code = params['confirmation_code']
    email = params['email']
else:
    st.session_state.hide_confirm_reset_password = True
    st.error('No se ha confirmar la cuenta! Faltaron datos en la solicitud!')    


if not st.session_state.hide_confirm_reset_password:
    c = st.container()
    with c :
        st.text_input('New Password', type="password", key='_newpassword')
        st.button('Change Password',on_click=change_password,key='signup')
else:
    return_operation = st.button(' Regresar ')

    if return_operation:
        st.session_state.hide_confirm_reset_password = False
        st.switch_page('main.py')            


menu() # Render the dynamic menu!



