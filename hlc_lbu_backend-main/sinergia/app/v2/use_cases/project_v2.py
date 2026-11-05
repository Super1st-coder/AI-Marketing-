import logging
from app.v2.repository.project_v2 import ProjectV2Repository
from app.tools.fury import FuryClient
from app.exceptions.base import DataNotFoundException, ParametersNotFoundException

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AnalyzeMarketingHypothesisUseCase:
    def __init__(self, account_email):
        self.account_email = account_email
        self.project_repository = ProjectV2Repository()
        self.fury_client = FuryClient()

    def execute(self, payload):
        project_id = payload.get('project_id')
        marketing_hypothesis = payload.get('marketing_hypothesis')

        if not project_id:
            logger.error("Project id is required")
            raise ParametersNotFoundException('Project id is required')
        
        if not marketing_hypothesis:
            logger.error("Marketing hypothesis is required")
            raise ParametersNotFoundException('Marketing hypothesis is required')

        logger.info(f"Analyzing marketing hypothesis for project {project_id}")
        
        # 1. Call Fury to extract variables
        fury_payload = {
            "instruction": marketing_hypothesis
        }
        
        try:
            analysis_result = self.fury_client.post('/api/v2/llm/extract-hypothesis-variables', fury_payload)
        except Exception as e:
            logger.error(f"Error calling Fury for hypothesis analysis: {e}")
            raise Exception("ERROR - Processing in IA LLM Model")

        # 2. Prepare data to save in Strapi
        update_data = {
            "marketing_hypothesis": marketing_hypothesis,
            "marketing_hypothesis_analysis": analysis_result
        }

        # 3. Update Strapi Project-V2
        updated_project = self.project_repository.update(project_id, update_data)
        
        if not updated_project:
            logger.error(f"Failed to save project {project_id} in Strapi")
            raise DataNotFoundException("ERROR - Saving Project")

        # 4. Build n8n-compatible response
        return {
            "ok": 1,
            "data": {
                "project_id": project_id,
                "marketing_hypothesis": marketing_hypothesis,
                "marketing_hypothesis_analysis": analysis_result
            }
        }
