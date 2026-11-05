from sqlalchemy.ext.declarative import DeclarativeMeta
import json

def entity_as_dict(obj):
    fields = {}
    if isinstance(obj.__class__, DeclarativeMeta):
        # an SQLAlchemy class
        for field in [x for x in dir(obj) if not x.startswith('_') and x != 'metadata']:
            data = obj.__getattribute__(field)
            try:
                json.dumps(data) # this will fail on non-encodable values, like other classes
                fields[field] = data
            except TypeError:
                fields[field] = None
        # a json-encodable dict
    return fields

