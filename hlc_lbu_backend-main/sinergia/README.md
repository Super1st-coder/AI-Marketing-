# SINERGIA - Backend para Aplicaciones Web


## Getting Started

Installing (in project folder):

    Use python3.8

    py -m venv venv
    . venv/Scripts/activate
    # In venv:
    pip install -r requirements.txt
    export CONFIG_TYPE=dev
    py manage.py db_init


Running app:
    Add a .env file from a copy from .env_base

    # In venv:
    py manage.py run

 And go to: `http://127.0.0.1:5000/api/v1/`

Running tests:

    # In venv
    export CONFIG_TYPE=tests
    py manage.py run_tests
