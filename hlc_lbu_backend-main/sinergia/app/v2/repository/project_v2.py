import logging
from app.tools.strapi import StrapiClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ProjectV2Repository(StrapiClient):
    def __init__(self):
        super(ProjectV2Repository, self).__init__()
        self.content_type = 'project-v2s'

    def update(self, project_id, data):
        # En Strapi V4, para actualizar necesitamos el ID interno (documentId o ID relacional),
        # pero n8n usa `updateKey=project_id`. Asumimos que podemos buscar por project_id primero.
        filters = {
            'project_id': project_id
        }
        
        # 1. Buscar el documento interno de Strapi
        response = self.find_by_filters(self.content_type, filters)
        if not response or not len(response.get('data', [])) > 0:
            logger.error(f"ProjectV2 not found by project_id: {project_id}")
            return None
            
        strapi_id = response['data'][0]['id']
        
        # 2. Actualizar el documento
        payload = {
            'data': data
        }
        update_resp = self.put(f"{self.content_type}/{strapi_id}", payload)
        
        if not update_resp or not update_resp.get('data'):
            logger.error(f"Failed to update project-v2 {project_id}: {update_resp}")
            return None
            
        return update_resp.get('data')

