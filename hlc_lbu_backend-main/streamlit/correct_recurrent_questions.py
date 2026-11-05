from slugify import slugify
import pandas as pd
import csv
import json


entity_name = 'sales-process'

if __name__ == "__main__":
    archivo_salida = f'data/{entity_name}/questions.csv'    # Nombre del archivo de salida

    df = pd.read_csv(archivo_salida, quoting=csv.QUOTE_ALL)
    
    questions_dict = {}
    questions_counter = {}
    for index,row in df.iterrows():
        questions_index = -1
        question_title =  row['label']        
        if question_title in questions_dict:
            if question_title in questions_counter:
                questions_counter[question_title] = questions_counter[question_title] + 1 
                questions_index = questions_counter[question_title]
            else:
                questions_counter[question_title] = 0
                questions_index = 0 
        else:
            questions_counter[question_title] = 0
            questions_index = 0 
            questions_dict[question_title] = question_title

        final_question = f"{question_title}"
        if questions_index > 0:
            final_question = f"{question_title} ({questions_index})"

        df.at[index,'label'] = final_question    

    print(df)
    print(questions_counter)

    archivo_salida_final = f'data/{entity_name}/questions_final.csv'    # Nombre del archivo de salida
    df.to_csv(archivo_salida_final,escapechar='\\', quoting=csv.QUOTE_ALL,index=False)