import logging
from app.tools.abyssale import AbyssaleClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AbyssaleRepository(AbyssaleClient):
    """Repository for Abyssale interactions."""
    def __init__(self):
        super(AbyssaleRepository, self).__init__()

    def get_project(self, project_id: str) -> dict:
        """Retrieve a project from Abyssale by its ID."""
        try:
            response = self.get(f'templates?category_id={project_id}')
        except Exception as e:
            logger.error(f"Error retrieving project {project_id} from Abyssale: {e}")
            return None
        
        return response
    
    def get_templates(self, project_id: str) -> list:
        """Retrieve templates for a project from Abyssale."""
        try:
            response = self.get(f'templates?category_id={project_id}')
        except Exception as e:
            logger.error(f"Error retrieving templates for project {project_id} from Abyssale: {e}")
            return []
        
        return response
    
    def get_template(self, template_id: str) -> dict:
        """Retrieve a single template from Abyssale by its ID."""
        try:
            response = self.get(f'templates/{template_id}')
        except Exception as e:
            logger.error(f"Error retrieving template {template_id} from Abyssale: {e}")
            return None
        
        return response