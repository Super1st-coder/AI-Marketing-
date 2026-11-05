import json
from app.exceptions.base import ParametersNotFoundException
from app.v2.repository.channel import ChannelRepository
from app.v2.use_cases.facebook_validator_service import MetaAdsValidator

class GetCtasUseCase():
    def __init__(self):
        self.channel_repository = ChannelRepository()

    def execute(self):
        # if not channel_name:
        #     raise ParametersNotFoundException('Channel name is required')
        
        # channel = self.channel_repository.get_by_name(channel_name)
        # if not channel:
        #     raise ParametersNotFoundException(f'Channel {channel_name} not found')
        
        # # return channel.ctas or []
        return list(MetaAdsValidator().VALID_CTA_VALUES)
