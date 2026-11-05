import streamlit as st
import os
# from strapi import strapi 
from app.repository.marketing import AccountRepository
from app.use_cases.security import SecurityManager

import pandas as pd
from app.models.entity import contentlist_to_pandas
from streamlit_modal import Modal

import streamlit as st
from menu import menu


# accountRepository = AccountRepository()
securityManager = SecurityManager()

st.set_page_config(layout="wide", page_title="Marketing Application", page_icon="🧮")

# Initialize st.session_state.role to None
if "role" not in st.session_state:
    st.session_state.role = None

# Retrieve the role from Session State to initialize the widget
st.session_state._role = st.session_state.role
st.session_state.hide_reset_password = False 
st.session_state.hide_confirm_reset_password = False 
st.session_state.hide_signup = False 


def logon():
    # Callback function to save the role selection to Session State
    if st.session_state._email != '':
        # st.session_state.role = st.session_state._role
        email = st.session_state._email
        password = st.session_state._password

        user_credential = securityManager.login(email,password)

        if not user_credential is None:
            st.session_state.role = "user"
            st.session_state.account = user_credential
        else:
            st.error('Usuario o contraseña incorrectos')
    else:
        st.error('Debe proporcionar primero el correo electronico')


if ("role" not in st.session_state or st.session_state.role is None) or ('account' not in st.session_state or st.session_state.account is None) :


    # st.markdown("<h1 style='text-align: center; color: grey;'>Entrar a HiLUCA</h1>", unsafe_allow_html=True)    

    c = st.container(border=True)
    with c:
        left_co, cent_co,last_co = st.columns(3)
        with cent_co:
            st.image('pages/images/hiluca-logo.png',width=200)

        st.text_input('Email',key='_email')
        st.text_input('Password', type="password", key='_password')
        st.button('Logon',on_click=logon)    
    
else:
    st.markdown("# Bienvenidos a HiLUCA!")
    if st.button("Go to Dashboard"):
        pass 
        # st.switch_page('pages/dashboards.py')

menu() # Render the dynamic menu!



