import logging
import requests

from app.tools.image_library import ImageLibraryClient
from app.exceptions.base import ImageLibraryException

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ImageLibraryRepository(ImageLibraryClient):
    """Repository for Image Library interactions."""
    def __init__(self):
        super(ImageLibraryRepository, self).__init__()

    def upload_image(self, image_data: any, body: dict) -> str:
        """Upload an image to the Image Library."""
        # Get pre-signed URL
        pre_signed = self.post('upload', body)
        logger.info(f"Received pre-signed URL response: {pre_signed}")
        upload_url = pre_signed['uploadUrl']
        image_id = pre_signed['imageId']
        s3_key = pre_signed['s3Key']
        expires_in = pre_signed['expiresIn']

        # Upload Image
        h = self.headers
        content_type = body.get('contentType', 'image/png')
        h.update({'x-amz-server-side-encryption': 'AES256', 'Content-Type': content_type})
        try:
            response = requests.put(url=upload_url, data=image_data.read(), headers=h)
            
            logger.info(f"Image uploaded to S3: {response.text}")
            response.raise_for_status()
        except Exception as e:
            logger.error(f"Error uploading image to S3: {e}")
            raise ImageLibraryException("Error uploading image to S3")

        return image_id

    def get_image(self, image_id: str, url_expiry: int = 43200) -> dict:
        """Retrieve an image from the Image Library by its ID.

        HL-2630: the returned URL is a presigned S3 link. Its default lifetime (~1h) was
        expiring before the ads pipeline's compositing step could download the product
        image (the URL is cached in the image_prompts checkpoint, then used later by
        nano_banana), so the composite silently fell back to scene-only. Request a longer
        expiry (12h) so the URL outlives the agent steps + Abyssale render + checkpoint
        resumes. Mirrors get_images_by_account, which already passes urlExpiry."""
        response = self.get(f'images/{image_id}', params={'urlExpiry': url_expiry})
        return response

    def get_images_by_account(self, account_id: str, category: str) -> list:
        """Retrieve all product images for an account from the Image Library."""
        response = self.get('images', params={'accountId': account_id, 'category': category, 
                                              'type': 'original', 'urlExpiry': 1200, 
                                              'start': 6, 'limit': 10})
        return response.get('items', [])