from slugify import slugify
import pandas as pd
import csv
import json

def slug_line(line):
    # Genera el slug a partir de la línea
    return slugify(line)

def slugify_filecontent(archivo_entrada, archivo_salida):
    entries = {}
    with open(archivo_entrada, 'r') as entrada:
        # Lee cada línea del archivo de entrada
        for linea in entrada:
            # Genera el slug de la línea
            new_line = linea.strip() 
            if new_line.strip() != '-':
                slug = slug_line(new_line.strip())
                suggested_slug = slug[:56].strip()
                if not suggested_slug in entries:
                    # Escribe el slug en el archivo de salida
                    entries[suggested_slug] = {'line' : new_line,'slug' : suggested_slug}
                else:
                    sequence_number = 1
                    while True:
                        new_slug = f"{suggested_slug}_{sequence_number}"
                        if not new_slug in entries: 
                            entries[new_slug] = {'line' : new_line,'slug' : new_slug}
                            break     
                        else:
                            sequence_number += 1

    df = pd.DataFrame.from_records([e for e in entries.values()])           
    df.to_csv(archivo_salida,escapechar='\\', quoting=csv.QUOTE_ALL,index=False)
    return df

if __name__ == "__main__":
    archivo_entrada = 'data/b2c-project-survey/b2c-project-survey_questions.txt'  # Nombre del archivo de entrada
    archivo_salida = 'data/b2c-project-survey/b2c-project-survey_questions.csv'    # Nombre del archivo de salida
    df = slugify_filecontent(archivo_entrada, archivo_salida)

    fi = open('data/b2c-project-survey/schema.json')
    json_schema = json.load(fi)
    for index,row in df.iterrows():
        json_schema['attributes'][row['slug']] = { "type": "string"}

    json_string = json.dumps(json_schema,indent=4)
    print(json_string)

    with open('data/b2c-project-survey/new-schema.json', 'w', encoding='utf-8') as fo:
        json.dump(json_schema, fo, ensure_ascii=False, indent=4)

    fi.close()