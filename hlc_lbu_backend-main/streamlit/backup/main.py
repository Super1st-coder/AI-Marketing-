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


accountRepository = AccountRepository()
securityManager = SecurityManager()

st.set_page_config(layout="wide", page_title="Marketing Application", page_icon="🧮")

# Initialize st.session_state.role to None
if "role" not in st.session_state:
    st.session_state.role = None

# Retrieve the role from Session State to initialize the widget
st.session_state._role = st.session_state.role

def set_role():
    # Callback function to save the role selection to Session State
    if st.session_state._email != '':
        # st.session_state.role = st.session_state._role
        email = st.session_state._email
        password = st.session_state._password

        user_credential = securityManager.login(email,password)

        if not user_credential is None:
            st.session_state.role = "user"

            account = accountRepository.get_by_email(email)

            if not account is None:
                st.session_state.account = account
            else:
                st.error('El correo electronico no esta registrado')
        else:
            st.error('Usuario o contraseña incorrectos')
    else:
        st.error('Debe proporcionar primero el correo electronico')


if ("role" not in st.session_state or st.session_state.role is None) or ('account' not in st.session_state or st.session_state.account is None) :

    st.text_input('Email',key='_email')
    st.text_input('Password', type="password", key='_password')
    st.button('Logon',on_click=set_role)

    # Selectbox to choose role
    # st.selectbox(
    #     "Select your role:",
    #     [None, "user", "admin", "super-admin"],
    #     key="_role",
    #     on_change=set_role,
    # )

else:
    st.markdown('# Bienvenidos a HiLUCA')

menu() # Render the dynamic menu!



