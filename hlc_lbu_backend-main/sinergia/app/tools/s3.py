import logging
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

class S3Client:
    def __init__(self, bucket_name):
        self.bucket_name = bucket_name
        self.s3_client = boto3.client('s3')

    def generate_presigned_url(self, command, s3_key, expiration=300, content_type=None):
        """Genera una URL prefirmada para un objeto S3."""
        params = {'Bucket': self.bucket_name, 'Key': s3_key}
        if content_type:
            params['ContentType'] = content_type
        try: 
            url = self.s3_client.generate_presigned_url(command, 
                                                   Params=params,
                                                   ExpiresIn=expiration)
            return url
        except ClientError as e:
            logger.error(f"Error al generar URL prefirmada: {e}")
            return None