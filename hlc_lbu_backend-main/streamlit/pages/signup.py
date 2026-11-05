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

if 'hide_signup' not in st.session_state:
    st.session_state.hide_signup = False 


def signup():
    # Callback function to save the role selection to Session State
    email = st.session_state._email
    first_name = st.session_state._firstname
    last_name = st.session_state._lastname
    password = st.session_state._password

    user_registered = securityManager.register(email,first_name,last_name,password)

    if user_registered:
        st.session_state.hide_signup = True
        st.info('El Usuario fue Registrado Satisfactoriamente!')   
    else:
        st.error('Error al registrar el usuario! Es posible que la direccion de correo ya se este usando!')    


if not st.session_state.hide_signup:

    st.markdown("<h1 style='text-align: center; color: grey;'>Registrarse en HiLUCA</h1>", unsafe_allow_html=True)    

    c = st.container(border=True)
    with c :
        st.text_input('Email',key='_email')
        st.text_input('Nombre',key='_firstname')
        st.text_input('Apellidos',key='_lastname')
        st.text_input('Password', type="password", key='_password')
        st.button('Signup',on_click=signup,key='signup')

else:
    st.markdown("<h1 style='text-align: center; color: grey;'>Registrarse en HiLUCA</h1>", unsafe_allow_html=True)    

    return_operation = st.button(' Regresar ')

    if return_operation:
        st.session_state.hide_signup = False
        st.switch_page('main.py')            


menu() # Render the dynamic menu!



