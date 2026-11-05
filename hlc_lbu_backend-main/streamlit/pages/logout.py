import streamlit as st
import os
# from strapi import strapi 
from app.repository.marketing import AccountRepository
import pandas as pd
from app.models.entity import contentlist_to_pandas
from streamlit_modal import Modal

import streamlit as st
from menu import menu


st.set_page_config(layout="wide", page_title="Marketing Application", page_icon="🧮")

st.session_state.role = None
st.session_state.account = None

st.switch_page("main.py")



