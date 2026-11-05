import logging, re
import boto3
from urllib.parse import urlparse, unquote
from app.exceptions.base import ParametersNotFoundException, IncorrectValidationException, S3ClientException, DataNotFoundException
from app.v2.repository.account import AccountRepository
from app.tools.fury import FuryClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GetBinaryObject():
    """Use case to get a binary object from S3."""
    def __init__(self, user_id):
        self.s3 = boto3.client('s3')
        self.user_id = user_id
        self.account_repository = AccountRepository()

    def get_account(self):
        account = self.account_repository.get_by_email(self.user_id)
        if not account:
            logger.error(f"Account not found: {self.account_email}")
            raise DataNotFoundException('Account not found')
        return account

    def parse_s3_url(self, s3_url: str):
        """
        Soporta:
        - https://bucket.s3.amazonaws.com/<key>
        - https://bucket.s3.us-east-1.amazonaws.com/<key>
        - https://s3.amazonaws.com/bucket/<key>
        """
        parsed = urlparse(s3_url)

        if not parsed.scheme.startswith("https"):
            raise IncorrectValidationException("URL inválida")

        host = parsed.netloc
        path = parsed.path.lstrip("/")

        # Caso 1: bucket.s3.amazonaws.com/key
        match = re.match(r"^(.+)\.s3\.amazonaws\.com$", host)
        if match:
            bucket = match.group(1)
            key = unquote(path)
            return bucket, key

        # Caso 2: bucket.s3.region.amazonaws.com/key
        match_virtual = re.match(r"^(.+)\.s3[.-][a-z0-9-]+\.amazonaws\.com$", host)
        if match_virtual:
            bucket = match_virtual.group(1)
            key = unquote(path)
            return bucket, key

        # Caso 3: s3.amazonaws.com/bucket/key
        if host.startswith("s3.amazonaws.com"):
            parts = path.split("/", 1)
            if len(parts) < 2:
                raise IncorrectValidationException("Formato de URL S3 inválido")
            bucket = parts[0]
            key = unquote(parts[1])
            return bucket, key

        raise IncorrectValidationException("La URL no parece ser de AWS S3")

    def execute(self, url):
        """Get a binary object from URL."""
        if not url:
            raise ParametersNotFoundException('Presigned URL Missing!')
        
        try:
            bucket, key = self.parse_s3_url(url)
        except Exception as e:
            logger.error(f"Error parsing S3 URL: {e}")
            raise e
        
        # validar account
        if not bucket or not key:
            raise IncorrectValidationException('Bucket or Key missing!')
        
        account = self.get_account()
        parent_account = account['attributes']['parent_account']['data']['id'] if account['attributes']['parent_account']['data'] else account['id']
        account_key = key.split('/', 1)[0]

        if isinstance(account_key, str) and account_key.isdigit():
            account_key = int(account_key)
        else:
            logger.error(f"Bucket Account {account_key} is not valid")
            raise IncorrectValidationException('Bucket Account is not valid!')
            

        if int(parent_account) != account_key:
            logger.error(f"Bucket Account {account_key} does not match account {parent_account}")
            raise IncorrectValidationException('Bucket does not match account!')

        try:
            response = self.s3.get_object(Bucket=bucket, Key=key)
            content_type = response.get("ContentType", "application/octet-stream")
            content = response["Body"].read()
            return {'content': content, 'content_type': content_type}
        except Exception as e:
            logger.error(f"Error getting object from S3: {e}")
            raise S3ClientException('Error getting object from S3')
        
class GetJobResultUseCase():
    def __init__(self, account_email):
        self.account_email = account_email
        self.account_repository = AccountRepository()
        self.fury_client = FuryClient()

    def execute(self, job_id):        
        account = self.account_repository.get_by_email(self.account_email)
        if not account:
            logger.error(f"Account not found: {self.account_email}")
            raise DataNotFoundException('Account not found')
        
        if not job_id:
            logger.error("Job id is required")
            raise ParametersNotFoundException('Job Id is required')

        try:
            response = self.fury_client.get(f'/api/v2/jobs/{job_id}')
            return response.get('data')
        except Exception as e:
            logger.error(f"Error getting job result: {str(e)}")
            raise e