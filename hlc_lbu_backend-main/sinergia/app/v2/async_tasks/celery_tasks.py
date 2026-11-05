from celery import shared_task
from app.v1.repository.base import N8NClient
from app.v2.use_cases.meta_ads import FacebookPublishCampaignUseCase, FacebookLaunchCampaignUseCase
from app.v2.use_cases.google_ads import GoogleAdsCreateCampaignUseCase


@shared_task(ignore_result=False)
def generate_topics_from_desc(credentials: dict, url: str, payload: dict) -> dict:
    try:
        n8nClient = N8NClient(credentials=credentials)
        response = n8nClient.executePost(url,payload,True,timeout=360)
        return  response
    except Exception as e:
        return {'ok': 0, 'message': {'code': e.code,  'text': e.text}}


@shared_task(ignore_result=False)
def publish_facebook_campaign(user_id, campaign_id, complete_campaign_data, creative_type) -> dict:
    try:
        data = FacebookPublishCampaignUseCase(user_id, campaign_id, complete_campaign_data, creative_type).execute()
        return {'ok' : 1, 'data': data }
    except Exception as e:
        return {'ok': 0, 'message': {'code': e.code,  'text': e.text}}

@shared_task(ignore_result=False)
def publish_google_campaign(user_id, customer_id, payload) -> dict:
    try:
        data = GoogleAdsCreateCampaignUseCase().execute(user_id, customer_id, payload)
        return {'ok' : 1, 'data': data }
    except Exception as e:
        return {'ok': 0, 'message': {'code': e.code,  'text': e.text}}
    
@shared_task(ignore_result=False)
def launch_facebook_campaign(user_id, launch_data) -> dict:
    try:
        data = FacebookLaunchCampaignUseCase(user_id, launch_data).execute()
        return {'ok' : 1, 'data': data }
    except Exception as e:
        return {'ok': 0, 'message': {'code': e.code,  'text': e.text}}
