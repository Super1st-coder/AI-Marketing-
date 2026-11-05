import streamlit as st
import os
from app.repository.marketing import ProjectRepository, AccountRepository, BrandRepository
import pandas as pd
from app.models.entity import contentlist_to_pandas
from streamlit_modal import Modal

from streamlit_extras.add_vertical_space import add_vertical_space 

from menu import menu_with_redirect

menu_with_redirect()

cancel_operation = st.button(' Back ')
if cancel_operation:
    st.switch_page('pages/project.py')

st.title("Brand Voice")
st.caption("Brand")
add_vertical_space(2)

repository = BrandRepository() 

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

brand = None
if 'brand' in st.session_state and not st.session_state['brand'] is None:
    brand = st.session_state['brand']     
else:
    menu_with_redirect()

columns_buttons1 = st.columns(5)
with columns_buttons1[0]:
    save_object1 = st.button(' Save ',key='save1')

message_area = st.empty()

# Definir los distintos campos para la Voz de Marca
attributes = repository.get_content_type_attributes('brand')
df_fields = pd.read_csv('data/brand/fields.csv' )
mandatory_fields = []

for key,value in brand.items():

    if key in attributes:
        features = attributes[key]

        searching_field = df_fields[df_fields.field == key]
        if len(searching_field) > 0:
            field_label = searching_field['label'].iloc[0]

            mandatory = searching_field['mandatory'].iloc[0]
            if mandatory:
                mandatory_fields.append( searching_field['field'].iloc[0])            

            if features['type'] == 'enumeration':
                choices = []
                choices = features['enum']
                selection = choices.index(brand[key]) if brand[key] != '' else 0
                brand[key] = st.selectbox(field_label, choices,selection)
            elif features['type'] == 'text':
                brand[key] = st.text_area(value=brand[key], label=field_label,height=4)
            else:
                brand[key] = st.text_input(value=brand[key], label=field_label)


columns_buttons2  = st.columns(5)
with columns_buttons2[0]:
    save_object2 = st.button(' Save ',key='save2')

if save_object1 or save_object2:    
    is_correct = True
    for f in mandatory_fields:
        if f in brand:
            if brand[f] is None or brand[f].strip() == '':
                is_correct = False

    if is_correct:
        try: 
            if 'id' in brand:
                repository.update(brand)    
            else:
                repository.create(brand)    
            st.switch_page('pages/project.py')
        except Exception as e:
            message_area.error('Error Desconocido - Favor contactar con el Administrador del Sistema')
    else: 
        message_area.error('Por favor revise los datos de Formulario, No se han llenado alguno de los datos obligatorios.')

