import logging
from app.v2.repository.account import AccountRepository
from app.v2.repository.media_platform_project import MediaPlatformProjectRepository
from app.v2.repository.brand import BrandRepository
from app.v2.repository.abyssale import AbyssaleRepository
from app.exceptions.base import DataNotFoundException, ParametersNotFoundException

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MediaPlatformProjectBaseUseCase():
    def __init__(self, account_email):
        self.account_email = account_email
        self.media_platform_repository = MediaPlatformProjectRepository()
        self.account_repository = AccountRepository()
        self.brand_repository = BrandRepository()
        self.abyssale_repository = AbyssaleRepository()

    def get_account(self):
        account = self.account_repository.get_by_email(self.account_email)
        if not account:
            logger.error(f"Account not found: {self.account_email}")
            raise DataNotFoundException('Account not found')
        return account

    def get_brand(self, brand_id):
        account = self.get_account()
        parent_account = account['attributes']['parent_account']['data']['id'] if account['attributes']['parent_account']['data'] else account['id']

        brand = self.brand_repository.get_by_id_and_account(brand_id, parent_account)
        if not brand:
            logger.error(f"Brand not found: {brand_id}")
            raise DataNotFoundException('Brand not found')
        
        return brand

class AddMediaPlatformProjectUseCase(MediaPlatformProjectBaseUseCase):
    def __init__(self, account_email):
        super().__init__(account_email)

    def _check_project_exists(self, project_id):
        project = self.abyssale_repository.get_project(project_id)

        if not project:
            return False
        
        return True
    
    def _build_response(self, data):
        response = {
            'id': data['id'],
            'project_id': data['attributes']['project_id'],
            'project_name': data['attributes']['project_name']
        }
        return response

    def execute(self, media_platform_data):
        if not media_platform_data.get('project_id'):
            logger.error("Project id is required")
            raise ParametersNotFoundException('Project id is required')
        
        if not media_platform_data.get('project_name'):
            logger.error("Project Name is required")
            raise ParametersNotFoundException('Project Name is required')
        
        brand = self.get_brand(media_platform_data.get('brand_id', 0))

        # Validar que el proyecto exista en Abyssale
        if not self._check_project_exists(media_platform_data.get('project_id')):
            logger.error(f"Project not found in Abyssale: {media_platform_data.get('project_id')}")
            raise DataNotFoundException('Project not found in Abyssale')

        new_project = {
            'brand_id': brand.get('id'),
            'project_id': media_platform_data.get('project_id'),
            'project_name': media_platform_data.get('project_name')
        }

        data = self.media_platform_repository.create(new_project)
        return self._build_response(data)

class GetMediaPlatformProjectsUseCase(MediaPlatformProjectBaseUseCase):
    def __init__(self, account_email):
        super().__init__(account_email)

    def _build_response(self, data):
        response = []
        for item in data:
            response.append({
                'id': item['id'],
                'project_id': item['project_id'],
                'project_name': item['project_name']
            })
        return response

    def execute(self, brand_id):
        brand = self.get_brand(brand_id)
        projects = self.media_platform_repository.get_by_brand(brand.get('id'))
        return self._build_response(projects)
    
class GetMediaPlatformTemplatesUseCase(MediaPlatformProjectBaseUseCase):
    def __init__(self, account_email):
        super().__init__(account_email)

    def _build_response(self, data):
        response = []
        for item in data:
            response.append({
                'template_id': item['id'],
                'template_name': item['name'],
                'template_preview_url': item['preview_url'],
                'type': item['type']
            })
        return response

    def get_project(self, brand_id, project_id):
        project = self.media_platform_repository.get_by_brand_and_id(brand_id, project_id)
        if not project:
            logger.error(f"Project not found: {brand_id} - {project_id}")
            raise DataNotFoundException('Project not found')
        
        return project

    def execute(self, brand_id, project_id):
        brand = self.get_brand(brand_id)
        project = self.get_project(brand.get('id'), project_id)
        templates = self.abyssale_repository.get_templates(project.get('project_id'))
        return self._build_response(templates)

class GetMediaTemplatesUseCase(MediaPlatformProjectBaseUseCase):
    def __init__(self, account_email):
        super().__init__(account_email)

    def _build_response(self, data):
        response = []
        for item in data:
            response.append({
                'template_id': item['id'],
                'template_name': item['name'],
                'template_preview_url': item['preview_url'],
                'type': item['type']
            })
        return response

    def execute(self, brand_id, project_id):
        brand = self.get_brand(brand_id)
        templates = self.abyssale_repository.get_templates(project_id)
        return self._build_response(templates)

class GetMediaPlatformTemplatesFuryUseCase():
    def __init__(self):
        self.media_platform_repository = MediaPlatformProjectRepository()
        self.abyssale_repository = AbyssaleRepository()

    def _build_response(self, data):
        response = []
        for item in data:
            response.append({
                'template_id': item['id'],
                'template_name': item['name'],
                'template_preview_url': item['preview_url'],
                'type': item['type']
            })
        return response

    def get_project(self, project_id):
        project = self.media_platform_repository.get_by_id(project_id)
        if not project:
            logger.error(f"Project not found: {project_id}")
            raise DataNotFoundException('Project not found')
        
        return project

    def execute(self, project_id):
        project = self.get_project(project_id)
        templates = self.abyssale_repository.get_templates(project.get('project_id'))
        return self._build_response(templates)
    
class GetAbyssaleTemplateFuryUseCase():
    def __init__(self):
        self.abyssale_repository = AbyssaleRepository()

    def _build_response(self, data):
        response = {
            'template_id': data['id'],
            'template_name': data['name'],
            'template_preview_url': data['preview_url'],
            'type': data['type'],
            'elements': data['elements']
        }
        return response

    def execute(self, template_id):
        template = self.abyssale_repository.get_template(template_id)
        if not template:
            logger.error(f"Template not found: {template_id}")
            raise DataNotFoundException('Template not found')
        
        return template