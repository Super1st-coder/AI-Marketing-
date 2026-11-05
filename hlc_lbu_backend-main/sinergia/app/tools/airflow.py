
from app.tools.config import load_configuration_file
import requests
from requests.exceptions import HTTPError
from app.exceptions.base import RESTClientException
import json
import urllib.parse

from datetime import datetime, timedelta


configuration = load_configuration_file()

class RESTClient(object):

    HOST_URI = 'http://localhost'
    USER = 'admin'
    PASSWORD = 'admin'

    def __init__(self,host_uri,username='admin',password='admin'):
        super().__init__()
        self.HOST_URI = host_uri    
        self.USER = username
        self.PASSWORD = password

    def get(self,end_point,params={}):
        json_response = None

        try:

            headers = {
                'content-type': "application/json",
                'cache-control': "no-cache"
            }
    
            final_url = urllib.parse.urljoin(self.HOST_URI,end_point)
    
            response = requests.get(final_url ,\
                                        params=params,\
                                        headers=headers, 
                                        auth=(self.USER,self.PASSWORD))

            response.raise_for_status()
            
        except HTTPError as http_err:
            if response.status_code == 400:
                raise RESTClientException(text='HTTP error occurred: %s' % http_err)
            else:
                raise RESTClientException(text='HTTP error occurred: %s' % http_err)
        except Exception as err:
            raise RESTClientException(text='Other error occurred: %s' % err)
        else:
            json_response = json.loads(response.text)
        
        return json_response

    def post(self, end_point, payload):
        
        json_response = None

        try:

            headers = {
                'content-type': "application/json",
                'cache-control': "no-cache"
            }
    
            json_payload = json.dumps(payload)

            final_url = urllib.parse.urljoin(self.HOST_URI,end_point)

            response = requests.post(final_url ,\
                                        data=json_payload,\
                                        headers=headers, 
                                        auth=(self.USER,self.PASSWORD) )
            
            response.raise_for_status()
            
        except HTTPError as http_err:           
            print(http_err)
            if response.status_code == 400:
                raise RESTClientException(text='HTTP error occurred: %s' % http_err)
            else:
                raise RESTClientException(text='HTTP error occurred: %s' % http_err)
        except Exception as err:
            raise RESTClientException(text='Other error occurred: %s' % err)
        else:
            json_response = json.loads(response.text)
        
        return json_response


class AirflowUtils(RESTClient):

    IMPORT_DAG = configuration.get('AIRFLOW','IMPORT_DAG')
    EXPORT_DAG = configuration.get('AIRFLOW','EXPORT_DAG')

    def __init__(self):
        super().__init__(host_uri=configuration.get('AIRFLOW','HOST_URI'),username=configuration.get('AIRFLOW','USERNAME'),password=configuration.get('AIRFLOW','PASSWORD'))

    def is_active(self):
        response = super.get('/api/v1/health')
        metadatabase_status = response['metadatabase']['status'] == "healthy" 
        scheduler_status = response['scheduler']['status'] == "healthy" 
        return metadatabase_status and scheduler_status 

    def get_last_import(self):
        query_path = '/api/v1/dags/{dag_id}/dagRuns'.format(dag_id = self.IMPORT_DAG)        

        today = datetime.now()
        two_week_ago = today - timedelta(weeks=2)
        two_week_ago_str = two_week_ago.strftime("%Y-%m-%d")

        response = self.get(query_path, { 'execution_date_gte' : two_week_ago_str } )
        dag_runs = response["dag_runs"] if "dag_runs" in response else []

        last_run = None
        if len(dag_runs) > 0:
            sorted_dag_runs = sorted(dag_runs, key=lambda k: k['start_date'], reverse=True)
            last_run = sorted_dag_runs[0]

        return last_run

    def is_running_import(self):
        last_run = self.get_last_import()
        return last_run['state'] == 'running'

    def execute_import(self,payload):
        query_path = '/api/v1/dags/{dag_id}/dagRuns'.format(dag_id = self.IMPORT_DAG)

        today = datetime.now()
        today_str = today.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        airflow_payload = { 'conf': payload , 'execution_date' :  today_str }

        response = self.post(query_path,airflow_payload)

    def get_last_export(self):
        query_path = '/api/v1/dags/{dag_id}/dagRuns'.format(dag_id = self.EXPORT_DAG)        

        today = datetime.now()
        two_week_ago = today - timedelta(weeks=2)
        two_week_ago_str = two_week_ago.strftime("%Y-%m-%d")

        response = self.get(query_path, { 'execution_date_gte' : two_week_ago_str } )
        dag_runs = response["dag_runs"] if "dag_runs" in response else []

        last_run = None
        if len(dag_runs) > 0:
            sorted_dag_runs = sorted(dag_runs, key=lambda k: k['start_date'], reverse=True)
            last_run = sorted_dag_runs[0]

        return last_run

    def is_running_export(self):
        last_run = self.get_last_export()
        return last_run['state'] == 'running'        

    def execute_export(self,payload):
        query_path = '/api/v1/dags/{dag_id}/dagRuns'.format(dag_id = self.EXPORT_DAG)

        today = datetime.now()
        today_str = today.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        airflow_payload = { 'conf': payload , 'execution_date' :  today_str }

        response = self.post(query_path,airflow_payload)

