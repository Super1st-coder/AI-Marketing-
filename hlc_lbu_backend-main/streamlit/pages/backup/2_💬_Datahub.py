import pandas as pd
import streamlit as st
import extra_streamlit_components as stx
import json

from jinja2 import Environment, FileSystemLoader
environment = Environment(loader=FileSystemLoader("templates/"))

def load_data_consultant() : 
    df = pd.read_csv('data/consultant.csv' )
    df.group = df.group.astype("category")
    df.group = df.group.cat.add_categories(("Relation"))
    return df

def load_data_product() : 
    df = pd.read_csv('data/product.csv' )
    df.group = df.group.astype("category")
    df.group = df.group.cat.add_categories(("Relation"))
    return df

def load_data_person() : 
    df = pd.read_csv('data/person.csv' )
    df.group = df.group.astype("category")
    df.group = df.group.cat.add_categories(("Relation"))
    return df

st.set_page_config(layout="wide", page_title="DataHub", page_icon="🧮")

st.title("✍️ DataHub")
st.caption("Update Data")


def update_entity(df,entity_name):
    df_filtered = df[df.value.notnull()]

    entity_reference_name = df_filtered[df.name == "%s_name" % entity_name]["value"].iloc[0]

    json_entity = df_filtered.to_json(orient='records')       
    json_object = json.loads(json_entity)     

    t_entity = environment.get_template("%s.txt" % entity_name)
    template_content  = t_entity.render({ 'entity_name' : entity_reference_name, 'entity' : json_object})

    output_name = 'training/%s.txt' % entity_name
    with open(output_name, 'w') as f:
        f.write(template_content)
    
    df.to_csv('data/%s.csv' % entity_name, header=True, encoding='utf-8', index=False)

tab1, tab2, tab3 = st.tabs(['Consultant','Product','Person'])

with tab1:
    df = load_data_consultant()
    annotated_df = st.data_editor(df) 
    entity_name = "consultant"
    btn_save_consultant = st.button('Save', key="save_consultant", on_click=update_entity , args = (annotated_df,entity_name,) )


with tab2:
    df = load_data_product()
    annotated_df = st.data_editor(df)  
    entity_name = "product"
    btn_save_product = st.button('Save', key="save_product" , on_click=update_entity , args = (annotated_df,entity_name,) )


with tab3:
    df = load_data_person()    
    annotated_df = st.data_editor(df)  
    entity_name = "person"
    btn_save_product = st.button('Save', key="save_person" , on_click=update_entity , args = (annotated_df,entity_name,) )
