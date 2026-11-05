import logging
from app.tools.strapi import StrapiClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MediaPlatformProjectRepository(StrapiClient):
    def __init__(self):
        super(MediaPlatformProjectRepository, self).__init__()
        self.content_type = 'media-platform-projects'

    def create(self, data):
        payload = {
            'data': data
        }

        response = self.post(self.content_type, payload)
        if not response or not response.get('data'):
            logger.error(f"Failed to add media platform project {response}")
            return None
        
        return response.get('data')
    
    def get_by_brand(self, brand_id):
        filters = {
            'brand_id': brand_id
        }
        response = self.find_by_filters(self.content_type, filters)
        if not response or not len(response['data']) > 0:
            return []
        
        projects = []
        for a_project in response['data']:
            project_data = {
                'id': a_project['id'],
                'project_id': a_project['attributes']['project_id'],
                'project_name': a_project['attributes']['project_name']
            }
            projects.append(project_data)

        return projects
    
    def get_by_brand_and_id(self, brand_id, id):
        filters = {
            'brand_id': brand_id,
            'id': id
        }
        response = self.find_by_filters(self.content_type, filters)

        if 'error' in response:
            logger.error(f"Error getting project {id} for brand {brand_id}: {response}")
            return None

        if not response or not len(response['data']) > 0:
            return None

        a_project = response['data'][0]
        data = {
            'id': a_project['id'],
            'project_id': a_project['attributes']['project_id'],
            'project_name': a_project['attributes']['project_name']
        }
        return data
    
    def get_by_id(self, id):
        filters = {
            'id': id
        }
        response = self.find_by_filters(self.content_type, filters)

        if 'error' in response:
            logger.error(f"Error getting project {id}: {response}")
            return None

        if not response or not len(response['data']) > 0:
            return None

        a_project = response['data'][0]
        data = {
            'id': a_project['id'],
            'project_id': a_project['attributes']['project_id'],
            'project_name': a_project['attributes']['project_name']
        }
        return data
