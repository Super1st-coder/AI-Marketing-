import pandas as pd
import streamlit as st
import extra_streamlit_components as stx
import json
import itertools

import os   
import openai

from jinja2 import Environment, FileSystemLoader
environment = Environment(loader=FileSystemLoader("templates/"))

OPENAI_KEY = 'OPENAI_API_KEY_REDACTED'

def load_openai_engine() : 
    engine = OpenAIEngine(OPENAI_KEY,{})
    return engine

class OpenAIEngine:

    def __init__(self,openai_key,data):
        self.openai_key = openai_key
        self.data = data

    def send_query(self,text): 
        # Cargar los templates de contexto
        all_files = os.listdir("training/")         
        txt_files = filter(lambda x: x[-4:] == '.txt', all_files)        
        corpus = [open(file).read() for file in [ "training/%s" % file_name for file_name in txt_files]  ]

        messages = []
        for c in corpus:
            messages.append({"role": "system", "content": c })

        # Cargar los templates de Agentes
        all_files = os.listdir("agent/")         
        txt_files = filter(lambda x: x[-4:] == '.txt', all_files)        
        corpus = [open(file).read() for file in [ "agent/%s" % file_name for file_name in txt_files]  ]
        for c in corpus:
            messages.append({"role": "system", "content": c })

        #Ejecutar la consulta
        openai.api_key = self.openai_key
        messages.append({"role": "user", "content": text })

        response = openai.ChatCompletion.create(model="gpt-3.5-turbo-16k-0613", temperature=0.8,messages = messages)
        reply = response["choices"][0]["message"]["content"]        

        return reply



st.set_page_config(layout="wide", page_title="Google Ads", page_icon="🧮")

st.title("✍️ Google Ads Generation")
st.caption("Generate Google Ads using Situations / Dimensions / Discovery Elements")


product_data = {}
person_data = {}

def get_product_data():
    df = pd.read_csv('data/product.csv' )
    df = df[df.name == 'product_name']
    json_df = df.to_json(orient='records' )
    json_object = json.loads(json_df)
    return json_object[0]['value']

# [Unique selling points, Key feature 1, Key feature 2]. 
def get_product_features():
    df = pd.read_csv('data/product.csv' )
    df = df[ (df.name == 'unique_selling_points') | (df.name == 'key_feature_1') | (df.name == 'key_feature_2') | (df.name == 'key_feature_3')] 
    json_df = df.to_json(orient='records' )
    json_object = json.loads(json_df)
    return json_object

# [Keyword 1, Keyword 2, Keyword 3, Keyword 4, Keyword 5]  
def get_product_keywords():
    df = pd.read_csv('data/product.csv' )
    df = df[df.name == 'keyword_list']
    json_df = df.to_json(orient='records' )
    json_object = json.loads(json_df)
    return json_object[0]['value']


def get_person_data():
    df = pd.read_csv('data/person.csv' )
    df = df[df.name == 'person_name']
    json_df = df.to_json(orient='records' )
    json_object = json.loads(json_df)
    return json_object[0]['value']

product_data = get_product_data()
person_data = get_person_data()
# model = load_llm_model()
model = load_openai_engine()

df_selected_dimensions = pd.DataFrame()
df_ads = pd.DataFrame()
text_ads = ''

def load_dimensions() : 
    df_dimensions = pd.read_csv('intermediate/dimensions.csv' )
    df_dimensions['active'] = False

    df_interests = pd.read_csv('intermediate/interests_product.csv' )
    df_interests = df_interests[['title','description']]
    df_interests['dimension'] = 'Interests'
    df_interests['active'] = False

    df = pd.concat([df_dimensions,df_interests])

    st.session_state.df_selected_dimensions = df     
    return df

###############################################################################

# if not 'df_selected_dimensions' in st.session_state:
df_selected_dimensions = load_dimensions()
st.session_state.df_selected_dimensions = df_selected_dimensions 
# else:
#     df_selected_dimensions = st.session_state.df_selected_dimensions

if not 'df_ads' in st.session_state:
    df_ads = pd.DataFrame()
    st.session_state.df_ads = df_ads 
else:
    df_ads = st.session_state.df_ads


if not 'text_ads' in st.session_state:
    text_ads = ''
    st.session_state.text_ads = text_ads 
else:
    text_ads = st.session_state.text_ads


def transform_list(l_description):
    if type(l_description) == list:
        list_elements = ['- %s' % s for s in l_description]
        return '\n'.join(list_elements)
    else:
        return str(l_description)

def generate_ads(product_data,person_data,model,df,option_writing_style,option_buyer_person_type):
    print("LOADING ADS")
    if not df is None:

        df_filtered = df[df['active'] == True]
        if not df_filtered.empty:

            json_entity = df_filtered.to_json(orient='records')       
            json_object = json.loads(json_entity)     

            product_features = get_product_features()
            keyword_list = get_product_keywords()


            t_prompt = environment.get_template("generate_ads.txt")
            template_content  = t_prompt.render({ 'person_name' : person_data, \
                                                 'product_name' : product_data, \
                                                 'writing_style' : option_writing_style, \
                                                 'buyer_person_style' : option_buyer_person_type, \
                                                 'dimensions' : json_object, \
                                                 'product_features' : product_features,\
                                                 'keyword_list' :  keyword_list, 'language' : "Spanish" })

            print(template_content)

            llm_response = model.send_query(template_content)

            print(llm_response)

            text_ads = llm_response
            st.session_state.text_ads = text_ads 

            # json_data = json.loads(llm_response)


            # df_ads = pd.DataFrame.from_records(json_data['result'])

            # df_ads['description'] = df_ads['description'].apply(lambda l_description: transform_list(l_description) )
            # df_ads['active'] = False

            # return df_ads

            return text_ads

        else:
            # return pd.DataFrame()
            return '' 
    else:
        # return pd.DataFrame()
        return ''

def regenerate_ads():
            
    if 'text_ads' in st.session_state:
        text_ads = st.session_state.text_ads
        if text_ads:        
            t_prompt = environment.get_template("regenerate_ads.txt")
            template_content  = t_prompt.render({ 'text_ads' : text_ads })

            print(template_content)

            llm_response = model.send_query(template_content)

            print(llm_response)

            text_ads = llm_response
            st.session_state.text_ads = text_ads 


def save_ads(df):
    pass


# c1_0, c2_0 = st.columns([6,6])

# with st.container():
#     with c1_0:
        # SELECTED DIMENSIONS         
st.subheader('Selected Dimensions')
with st.container():
    annotated_selected_dimensions = st.data_editor(df_selected_dimensions,key = 'annotated_selected_dimensions') 
with st.container():
    c1_1, c2_1 = st.columns([6,6])
    btn_refresh_dimensions = c1_1.button('Refresh Dimensions', key="refresh_dimensions" , on_click=load_dimensions  )
# CREATED SITUATIONS         
st.subheader('Ads  Results')
with st.container():
    c1_3, c2_3, c3_3 = st.columns([6,6,6])
    option_writing_style = c1_3.selectbox( 'Writing Style',('Conversational','Persuasive','Informative','Storytelling','Humorous','Emotional',\
'Inspirational','Professional','Playful','Intriguing','Urgent','Provocative','Nostalgic',\
'Straightforward','Sensational','Explanatory','Interactive','Bold','Caring','Trendy',\
'Quirky','Luxurious','Minimalist','Technical','Personal','Exciting','Exaggerated','Memorable',\
'Pioneering','Reassuring','Authentic','Controversial','Mysterious','Bold Claims','Curiosity-driven',\
'High-End','Urgency-driven','Futuristic','Alluring','Trust-building','Authentic storytelling','Provocative questions',\
'Playful rhymes','Conversational FAQs','Edgy','Youthful','Eco-friendly','Witty','Striking visuals',\
'Bold slogans','Jargon-free' ))
    option_buyer_person_type = c2_3.selectbox( 'Buyer Person Type', ( 'Financial','Operations','Technical',\
'Influencer','Decision Maker','End User','Innovator','Cost-Conscious','ROI-Focused',\
'Time-Constrained','Brand-Conscious','Sustainability-Minded','Quality-Driven','Trendsetter',\
'Risk-Averse','Local Shopper','Global Player','Tech-Savvy','Traditional','DIY Enthusiast',\
'Health-Conscious','Family-Oriented','Luxury Seeker','Budget Shopper','Early Adopter','Educated Consumer',\
'Frequent Traveler','Career-Focused','Minimalist','Eco-Conscious','Busy Professional',\
'Socially Responsible','Fashionista','DIY Homeowner','Health Professional','Sports Enthusiast',\
'Pet Lover','Tech Entrepreneur','Outdoor Adventurer','Foodie','Student','Retiree','Artistic',\
'Health and Fitness','DIY Parent','Music Lover','Remote Worker','Social Media Savvy','DIY Crafter') )
    btn_generate_ads = c3_3.button('Generate Ads', key="generate_ads" , on_click=generate_ads , args = (product_data,person_data,model,annotated_selected_dimensions,option_writing_style,option_buyer_person_type) )
    
with st.container():
    # annotated_addsense = st.data_editor(df_ads,key = 'annotated_ads') 
    area_ads = st.text_area('Generated Ads ', key = 'text_ads', height=480 )    
with st.container():
    c1_2, c2_2 = st.columns([6,6])
    c1_2.button('Save Ads Results', key="save_ads" )
    c2_2.button('Regenerate Ads', key="regenerate_ads", on_click=regenerate_ads  )
