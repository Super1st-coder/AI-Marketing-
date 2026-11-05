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
            if new_line.strip() != '-' and new_line[:2] != '**':
                slug = slug_line(new_line.strip())
                suggested_slug = slug[:56].strip()
                if not suggested_slug in entries:
                    # Escribe el slug en el archivo de salida
                    entries[suggested_slug] = {'label' : new_line,'field' : suggested_slug,'is_title' : False}
                else:
                    sequence_number = 1
                    while True:
                        new_slug = f"{suggested_slug}_{sequence_number}"
                        if not new_slug in entries: 
                            entries[new_slug] = {'label' : new_line,'field' : new_slug,'is_title' : False}
                            break     
                        else:
                            sequence_number += 1
            else:
                slug = slug_line(new_line.strip())
                new_slug = slug[:56].strip()                
                entries[new_slug] = {'label' : new_line,'field' : '','is_title' : True}

    df = pd.DataFrame.from_records([e for e in entries.values()])           
    df.to_csv(archivo_salida,escapechar='\\', quoting=csv.QUOTE_ALL,index=False)
    return df

entity_name = 'sales-process'

if __name__ == "__main__":
    archivo_entrada = f'data/{entity_name}/questions.txt'  # Nombre del archivo de entrada
    archivo_salida = f'data/{entity_name}/questions.csv'    # Nombre del archivo de salida
    df = slugify_filecontent(archivo_entrada, archivo_salida)

    fi = open(f'data/{entity_name}/schema.json')
    json_schema = json.load(fi)
    for index,row in df.iterrows():
        if not row['is_title']:
            json_schema['attributes'][row['field']] = { "type": "string"}

    json_string = json.dumps(json_schema,indent=4)
    print(json_string)

    with open(f'data/{entity_name}/new-schema.json', 'w', encoding='utf-8') as fo:
        json.dump(json_schema, fo, ensure_ascii=False, indent=4)

    fi.close()