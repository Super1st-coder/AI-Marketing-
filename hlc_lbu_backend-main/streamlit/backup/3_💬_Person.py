import pandas as pd
import streamlit as st
import extra_streamlit_components as stx
import json

from jinja2 import Environment, FileSystemLoader
environment = Environment(loader=FileSystemLoader("templates/"))

entity_name = 'person'
output_name = "training/%s.txt" % entity_name
template_name = "%s.txt" % entity_name
entity_variable_name = "%s_name" % entity_name
entity_prompt_name = "%s_prompt" % entity_name 

df = pd.read_csv('data/%s.csv' % entity_name)
df.group = df.group.astype("category")
df.group = df.group.cat.add_categories(("Relation"))

st.set_page_config(layout="wide",  page_title="Update Person Data", page_icon="🧮")

st.title("✍️ Person")
st.caption("Update Person Data")

is_vertical = True

def finish_operation():
    
    template_content = st.session_state[entity_prompt_name]

    with open(output_name, 'w') as f:
        f.write(template_content)

    st.warning('Data Saved', icon="⚠️")


if is_vertical:
    c1, c2 = st.columns([1, 3])
    with c1:
        val_p = stx.stepper_bar(steps=["Edit", "Template", "Finish"], is_vertical=is_vertical, lock_sequence=True)

    with c2:
        
        if val_p == 0:
            annotated = st.data_editor(df)    
        elif val_p == 1:
            # Show ChatGPT Template0
            df_filtered = df[df.value.notnull()]

            entity_reference_name = df_filtered[df.name == entity_variable_name]["value"].iloc[0]

            json_entity = df_filtered.to_json(orient='records')       
            json_object = json.loads(json_entity)     

            t_entity = environment.get_template(template_name)
            template_content  = t_entity.render({ 'entity_name' : entity_reference_name, 'entity' : json_object})

            st.markdown(template_content)

            st.session_state[entity_prompt_name] = template_content

            # st.write(df_filtered)
        else:
            # Save
            st.info(f"Finish")
            st.button('Finish', on_click=finish_operation)


