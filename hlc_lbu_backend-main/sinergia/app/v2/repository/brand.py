from app.tools.strapi import StrapiClient
from app.tools.s3 import S3Client
from app.v2.models.constant import ACTIVE_DATA
from app.exceptions.base import S3ClientException
from config import config
import logging
import requests
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

config_type = os.environ.get('CONFIG_TYPE', 'dev')

class BrandRepository(StrapiClient):
    """docstring for ClassName."""
    def __init__(self):
        super(BrandRepository, self).__init__()
        self.content_type = 'brand-v2s'
        cfg = config.get(config_type)
        self.font_bucket = getattr(cfg, 'FONT_BUCKET', None)

    def create_manual(self, data):
        payload = {
            'data': data
        }
        
        response = self.post(f"{self.content_type}", payload)
        
        data = {
            'id': response['data']['id'],
            'name': response['data']['attributes']['name'],
            'creation_method': response['data']['attributes']['creation_method'],
            'complete': response['data']['attributes']['complete'],
            'website_url': response['data']['attributes']['website'] if response['data']['attributes'].get('website') else '',
            'identity': response['data']['attributes']['identity'],
            'logos': response['data']['attributes']['logos'],
            'colors': response['data']['attributes']['colors'],
            'typography': response['data']['attributes']['typography'],
            'dos_donts': response['data']['attributes']['dos_donts'],
            'language': response['data']['attributes']['language']
        }
        return data
    
    def get_by_name_and_account(self, name, account):
        filters = {
            'account_id': account,
            'name': name
        }
        populate = ['parent_account']
        response = self.find_by_filters(self.content_type, filters, populate)
        if not response or not len(response['data']) > 0:
            return None
        
        a_brand = response['data'][0]

        data = {
            'id': a_brand['id'],
            'name': a_brand['attributes']['name'],
            'creation_method': a_brand['attributes']['creation_method'],
            'complete': a_brand['attributes']['complete'],
            'identity': a_brand['attributes']['identity'],
            'logos': a_brand['attributes']['logos'],
            'colors': a_brand['attributes']['colors'],
            'typography': a_brand['attributes']['typography'],
            'dos_donts': a_brand['attributes']['dos_donts']   
        }
        return data

        
    
    def get_by_id_and_account(self, brand_id, account):
        filters = {
            'account_id': account,
            'id': brand_id,
            'status': ACTIVE_DATA
        }

        response = self.find_by_filters(self.content_type, filters)
        if not response or not len(response['data']) > 0:
            return None
        
        a_brand = response['data'][0]

        data = {
            'id': a_brand['id'],
            'name': a_brand['attributes']['name'],
            'creation_method': a_brand['attributes']['creation_method'],
            'complete': a_brand['attributes']['complete'],
            'website_url': a_brand['attributes']['website'] if a_brand['attributes'].get('website') else '',
            'identity': a_brand['attributes']['identity'],
            'logos': a_brand['attributes']['logos'],
            'colors': a_brand['attributes']['colors'],
            'typography': a_brand['attributes']['typography'],
            'dos_donts': a_brand['attributes']['dos_donts'],
            'language': a_brand['attributes']['language']
        }
        return data

    
    def get_by_brand_id(self, brand_id):
        response = self.get_by_id(self.content_type, brand_id)

        if not response or not response.get('data'):
            return None
        
        data = {
            'id': response['data']['id'],
            'name': response['data']['attributes']['name'],
            'creation_method': response['data']['attributes']['creation_method'],
            'complete': response['data']['attributes']['complete'],
            'identity': response['data']['attributes']['identity'],
            'logos': response['data']['attributes']['logos'],
            'colors': response['data']['attributes']['colors'],
            'typography': response['data']['attributes']['typography'],
            'dos_donts': response['data']['attributes']['dos_donts']   
        }
        return data
    
    def update_brand(self, brand_id, data):
        payload = {
            'data': data
        }

        response = self.put(f"{self.content_type}/{brand_id}", payload)
        if not response or not response.get('data'):
            return None

        data = {
            'id': response['data']['id'],
            'name': response['data']['attributes']['name'],
            'creation_method': response['data']['attributes']['creation_method'],
            'complete': response['data']['attributes']['complete'],
            'website_url': response['data']['attributes']['website'] if response['data']['attributes'].get('website') else '',
            'identity': response['data']['attributes']['identity'],
            'logos': response['data']['attributes']['logos'],
            'colors': response['data']['attributes']['colors'],
            'typography': response['data']['attributes']['typography'],
            'dos_donts': response['data']['attributes']['dos_donts'],
            'language': response['data']['attributes']['language']
        }
        return data
    

    def get_all(self, payload):
        filters = payload.get('filters', {})
        populate = payload.get('populate', [])
        pagination = payload.get('pagination', {})
        sort = payload.get('sort')
        response = self.find_by_filters(self.content_type, filters, populate, pagination, sort)
        
        if not response or not response.get('data'):
            return None

        resp = {
            'data': [],
            'count': response['meta']['pagination']['limit'],
            'total': response['meta']['pagination']['total']
        }
        
        for brand in response['data']:
            resp['data'].append({
                'id': brand['id'],
                'name': brand['attributes']['name'],
                'creation_method': brand['attributes']['creation_method'],
                'complete': brand['attributes']['complete'],
                'website_url': brand['attributes']['website'] if brand['attributes'].get('website') else '',
                'identity': brand['attributes']['identity'],
                'logos': brand['attributes']['logos'],
                'colors': brand['attributes']['colors'],
                'typography': brand['attributes']['typography'],
                'dos_donts': brand['attributes']['dos_donts'],
                'language': brand['attributes']['language']
            })

        return resp
    
    def upload_font_file(self, key, file, content_type):
        if self.font_bucket:
            response = self.upload_file(key, file, self.font_bucket, content_type)
        else:
            logger.error(f"Font bucket not configured")
            raise S3ClientException('Font bucket not configured')
        return response
    
    def upload_file(self, key, file, bucket, content_type):
        if bucket:
            s3_client = S3Client(bucket)
            url = s3_client.generate_presigned_url('put_object', key, content_type=content_type)
            if not url:
                logger.error(f"Error generating signed URL")
                raise S3ClientException('Error generating signed URL')
            
            headers = {'Content-Type': content_type}
            response = requests.put(url, data=file.read(), headers=headers)
            response.raise_for_status()
        else:
            logger.error(f"Bucket not configured")
            raise S3ClientException('Bucket not configured')
        return response
    
    def get_presigned_url(self, bucket_name, command, key):
        s3_client = S3Client(bucket_name)
        url = s3_client.generate_presigned_url(command, key)
        return url

    