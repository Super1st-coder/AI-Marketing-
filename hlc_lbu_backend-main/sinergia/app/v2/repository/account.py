from app.tools.strapi import StrapiClient
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AccountRepository(StrapiClient):
    """Repository for account-related operations."""
    def __init__(self):
        super(AccountRepository, self).__init__()
        self.content_type = 'accounts'

    def get_by_email(self, email):
        filters = {
            'email': email
        }
        populate = ['parent_account']
        response = self.find_by_filters(self.content_type, filters, populate)
        
        if response and len(response['data']) > 0:
            return response['data'][0]
        return None