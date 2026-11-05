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
import time 

accountRepository = AccountRepository()
securityManager = SecurityManager()

st.set_page_config(layout="wide", page_title="Marketing Application", page_icon="🧮")

# Initialize st.session_state.role to None
if "role" not in st.session_state:
    st.session_state.role = None


params = st.query_params.to_dict()


if 'confirmation_code' in params and 'email' in params:

    confirmation_code = params['confirmation_code']
    email = params['email']

    account_confirmed = securityManager.confirm_account(email,confirmation_code)

    if account_confirmed:
        st.info(f'Su cuenta {email} se ha confirmado exitosamente!')        
    else:
        st.error('Error al registrar el usuario! Es posible que la direccion de correo ya se este usando!')    


else:
    st.error('No se ha confirmar la cuenta! Faltaron datos en la solicitud!')    


return_operation = st.button(' Regresar ')
if return_operation:
    st.switch_page('main.py')    


menu() # Render the dynamic menu!



