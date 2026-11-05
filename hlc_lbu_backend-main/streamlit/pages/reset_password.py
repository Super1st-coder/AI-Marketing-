import streamlit as st
import os
# from strapi import strapi 
from app.use_cases.security import SecurityManager
import pandas as pd
from app.models.entity import contentlist_to_pandas
from streamlit_modal import Modal

import streamlit as st
from menu import menu

securityManager = SecurityManager()

st.set_page_config(layout="wide", page_title="Marketing Application", page_icon="🧮")

if 'hide_reset_password' not in st.session_state:
    st.session_state.hide_reset_password = False 

# Initialize st.session_state.role to None
if "role" not in st.session_state:
    st.session_state.role = None


def reset_password():
    # Callback function to save the role selection to Session State
    email = st.session_state._email

    action_executed = securityManager.init_reset_password(email)

    if action_executed:
        st.session_state.hide_reset_password = True
        st.info('Se ha enviado un correo electronico con las instrucciones correspondientes para reiniciar su contrasena!')   
    else:
        st.error('Error al reiniciar la contrasena del Usuario! Es posible que la direccion de correo NO este registrada!')    


if not st.session_state.hide_reset_password:
    st.markdown("<h1 style='text-align: center; color: grey;'>Reiniciar Contrase#a - HiLUCA</h1>", unsafe_allow_html=True)    

    c = st.container(border=True)
    with c :
        st.text_input('Email',key='_email')
        st.button('Reset Password',on_click=reset_password)
else:
    st.markdown("<h1 style='text-align: center; color: grey;'>Reiniciar Contrase#a</h1>", unsafe_allow_html=True)    

    return_operation = st.button(' Regresar ')

    if return_operation:
        st.session_state.hide_reset_password = False
        st.switch_page('main.py')            

menu() # Render the dynamic menu!



