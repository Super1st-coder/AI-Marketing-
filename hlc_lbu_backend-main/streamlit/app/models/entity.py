import pandas as pd

def content_todict(content):
    entity = {}
    if not content is None:
        new_entity = {}
        new_entity['id'] = content['id']
        attributes = content['attributes']
        entity = { **new_entity, **attributes }
    return entity

def contentlist_to_pandas(content_list):
    df = pd.DataFrame(content_list)
    df.reset_index(drop=True,inplace=True)
    return df
