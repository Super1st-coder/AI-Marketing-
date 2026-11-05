from app.v2.repository.brand import BrandRepository
from app.v2.repository.account import AccountRepository
from app.v2.repository.image_library import ImageLibraryRepository
from app.v2.repository.brand_document import BrandDocumentRepository
from app.exceptions.base import DataAlreadyRegisteredException, DataNotFoundException, IncorrectValidationException, SinergiaException, ImageLibraryException, S3ClientException
from app.v2.models.constant import ACTIVE_DATA, FONT_ALLOWED_EXTENSIONS
from app.v2.models.brand_scheme import sc_brand_save_completed, sc_brand_save_valid
from cerberus import Validator
from PIL import Image
from io import BytesIO
from retrying import retry
from werkzeug.utils import secure_filename
import logging
import mimetypes
import os
from config import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

config_type = os.environ.get('CONFIG_TYPE', 'dev')

class BrandUseCase:
    """docstring for BrandUseCase."""
    def __init__(self, account_email):
        self.account_email = account_email
        cfg = config.get(config_type)
        self.docs_bucket = getattr(cfg, 'DOCS_BUCKET', None)
        self.region = getattr(cfg, 'REGION_BUCKET', None)
        self.brand_repository = BrandRepository()
        self.account_repository = AccountRepository()

    def get_account(self):
        # Buscar account en la base de datos
        account = self.account_repository.get_by_email(self.account_email)
        if not account:
            logger.error(f"Account not found: {self.account_email}")
            raise DataNotFoundException('Account not found')
        return account
    
    def get_docs_bucket_config(self):
        return {'bucket_name': self.docs_bucket, 'region': self.region}
    
    def get_doc_presigned_url(self, command, key):
        url = self.brand_repository.get_presigned_url(self.docs_bucket, command, key)
        return url
    
    def _validate_typography(self, payload):
        typography_complete = False
        typography = payload.get('typography', [])
        for item in typography:
            if item.get('family') and item.get('fonts'):
                for font in item.get('fonts'):
                    a_font_complete = False
                    if font.get('style') and font.get('file'):
                        a_font_complete = True
                        if font.get('usage'):
                            typography_complete = True
                            
                    font['complete'] = a_font_complete
        return typography_complete

    def _validate_logos(self, payload):
        logos_complete = False
        logos = payload.get('logos', [])
        for logo in logos:
            a_logo_complete = False
            if logo.get('category') and logo.get('image_id'):
                a_logo_complete = True
                if logo.get('category') == 'main-logo' and logo.get('description'):
                    logos_complete = True
            logo['complete'] = a_logo_complete
        return logos_complete

    def _validate_colors(self, payload):
        colors_complete = False
        colors = payload.get('colors', [])
        for color in colors:
            if color.get('category') == 'primary' and color.get('name') and color.get('hex_code'):
                colors_complete = True
                break
        return colors_complete

    def _validate_identity(self, payload):
        identity_complete = False
        identity = payload.get('identity')
        if (identity) and (identity.get('values', {}).get('value', []) or \
                identity.get('about_us', {}).get('value') or \
                    identity.get('mission', {}).get('value') or \
                        identity.get('vision', {}).get('value') or \
                            identity.get('tone_voice', {}).get('value', [])):
            identity_complete = True
        return identity_complete

class CreateBrandManualUseCase(BrandUseCase):
    """docstring for CreateBrandManualUseCase."""
    def __init__(self, account_email):
        super().__init__(account_email)

    def execute(self, payload):
        # Validar payload
        if not payload or not isinstance(payload, dict):
            logger.error(f"Invalid payload: {payload}")
            raise IncorrectValidationException('Invalid payload')
        
        # Validar que el payload tenga los campos requeridos
        required_fields = ['name', 'website_url', 'language']

        # Validar que el payload tenga los campos requeridos
        for field in required_fields:
            if field not in payload:
                logger.error(f"Missing required field: {field}")
                raise IncorrectValidationException(f"Missing required field: {field}")

        # Validar que el valor de language sea uno de los permitidos ['English', 'Spanish']
        if payload['language'].lower() not in ['english', 'spanish']:
            logger.error(f"Invalid language: {payload['language']}")
            raise IncorrectValidationException('The language field must be either English or Spanish.')

        try:
            logger.debug(f"Creating brand: {payload['name']} for account: {self.account_email}")
            account = self.get_account()
            parent_account = account['attributes']['parent_account']['data']['id'] if account['attributes']['parent_account']['data'] else account['id']

            # Validar que el nombre de la marca sea unico por la cuenta
            brand = self.brand_repository.get_by_name_and_account(payload['name'], parent_account)
            if brand:
                logger.error(f"Brand name already exists: {payload['name']}")
                raise DataAlreadyRegisteredException('Brand name already exists')
            
            data = {
                'name': payload['name'],
                'account_ref': parent_account,
                'account_id': parent_account,
                'created_by_account': account['id'],
                'creation_method': 'MANUAL',
                'website': payload['website_url'],
                'complete': False,
                'identity': {
                    'about_us': {'value': '', 'source': []},
                    'mission': {'value': '', 'source': []},
                    'vision': {'value': '', 'source': []},
                    'values': {'value': [], 'source': []},
                    'tone_voice': {'value': [], 'source': []},
                    'complete': False

                },
                'logos': {'values': [], 'complete': False},
                'colors': {'values': [], 'complete': False},
                'typography': {'values': [], 'complete': False},
                'dos_donts': [],
                'language': payload['language'].capitalize()
            }

            # Crear la marca            
            response = self.brand_repository.create_manual(data)
            if not response:
                logger.error(f"Error creating brand: {response}")
                raise SinergiaException('Error creating brand')
            
        except SinergiaException as e:
            logger.error(f"Error creating brand: {e.text}")
            raise e
        except Exception as err:
            logger.error(f"Error creating brand: {err}")
            raise SinergiaException('Error creating brand') 
        else:
            logger.debug(f"Brand created successfully: {response['id']} - {response['name']}")
            return response   

class GetABrandUseCase(BrandUseCase):
    """docstring for GetABrandUseCase."""
    def __init__(self, account_email):
        super().__init__(account_email)

    def execute(self, brand_id):
        try:
            logger.debug(f"Getting brand by id: {brand_id}")
            account = self.get_account()
            parent_account = account['attributes']['parent_account']['data']['id'] if account['attributes']['parent_account']['data'] else account['id']

            brand = self.brand_repository.get_by_id_and_account(brand_id, parent_account)
            if not brand:
                logger.error(f"Brand not found: {brand_id}")
                raise DataNotFoundException('Brand not found')
            
            rep = ImageLibraryRepository()

            # Recorrer los logos y obtener las imagenes
            logos = brand['logos']
            if logos and isinstance(logos, dict) and logos.get('values'):
                for logo in logos.get('values'):
                    image_url = rep.get_image(logo.get('image_id')) if logo.get('image_id') else None
                    logo['image_url'] = image_url.get('url') if image_url else None

            # Recorrer los Dos and Donts y obtener las imagenes
            if brand['dos_donts']:
                for do_dont in brand['dos_donts']:
                    image_url = rep.get_image(do_dont.get('image_id')) if do_dont.get('image_id') else None
                    do_dont['image_url'] = image_url.get('url') if image_url else None

            # creation_doc = brand.get('creation_doc_id')
            # doc_url = None
            # if creation_doc:
            #     doc_url = self.get_doc_presigned_url('get_object', creation_doc)
            
            # brand.update({'creation_doc_url': doc_url})
            
        except SinergiaException as e:
            logger.error(f"Error getting brand: {e.text}")
            raise e
        except Exception as err:
            logger.error(f"Error getting brand: {err}")
            raise SinergiaException('Error getting brand') 
        else:
            return brand
        
class SaveBrandUseCase(BrandUseCase):
    """docstring for SaveBrandUseCase."""
    def __init__(self, account_email):
        super().__init__(account_email)

    def execute(self, brand_id, payload):
        try:
            logger.debug(f"Saving brand by id: {brand_id}")
            # Validar payload
            val = Validator(sc_brand_save_valid)
            if not val.validate(payload):
                logger.error(f"Invalid payload: {val.errors}")
                raise IncorrectValidationException(f"Invalid payload {val.errors}")

            account = self.get_account()
            parent_account = account['attributes']['parent_account']['data']['id'] if account['attributes']['parent_account']['data'] else account['id']

            brand = self.brand_repository.get_by_id_and_account(brand_id, parent_account)
            if not brand:
                logger.error(f"Brand not found: {brand_id}")
                raise DataNotFoundException('Brand not found')     

            # Validar que la seccion Identity este completa
            identity_complete = self._validate_identity(payload) if payload.get('identity') else brand.get('identity', {}).get('complete', False)

            # Validar que la seccion Colors tenga al menos un color con category == 'primary' and name and hex_code para marcar la seccion como completa
            colors_complete = self._validate_colors(payload) if isinstance(payload.get('colors'), list) else brand.get('colors', {}).get('complete', False)

            # Validar que la seccion Logos tenga al menos un logo con category == 'main-logo', image_id y description para marcar la seccion como completa
            logos_complete = self._validate_logos(payload) if isinstance(payload.get('logos'), list) else brand.get('logos', {}).get('complete', False)

            # Validar que la seccion Typography tenga al menos un item con family, fonts[].style, fonts[].file y fonts[].usage para marcar la seccion como completa
            typography_complete = self._validate_typography(payload) if isinstance(payload.get('typography'), list) else brand.get('typography', {}).get('complete', False)

            completed = identity_complete and colors_complete and logos_complete and typography_complete
            
            # Actualizar la marca
            data = {
                # 'name': payload.get('name', brand['name']),
                'identity': {'complete': identity_complete,  **payload.get('identity', brand['identity'])},
                'logos': {'complete': logos_complete, 'values': payload.get('logos', brand['logos']['values'] if isinstance(brand['logos'], dict) else brand['logos'])},
                'colors': {'complete': colors_complete, 'values': payload.get('colors', brand['colors']['values'] if isinstance(brand['colors'], dict) else brand['colors'])},
                'typography': {'complete': typography_complete, 'values': payload.get('typography', brand['typography']['values'] if isinstance(brand['typography'], dict) else brand['typography'])},
                'dos_donts': payload.get('dos_donts', brand['dos_donts']),
                'complete': completed
            }

            response = self.brand_repository.update_brand(brand_id, data)
            if not response:
                logger.error(f"Error saving brand: {response}")
                raise SinergiaException('Error saving brand')
            
            rep = ImageLibraryRepository()
            
            # Recorrer los logos y obtener las imagenes
            logos = response['logos']
            if logos and isinstance(logos, dict) and logos.get('values'):
                for logo in logos.get('values'):
                    image_url = rep.get_image(logo.get('image_id')) if logo.get('image_id') else None
                    logo['image_url'] = image_url.get('url') if image_url else None

            # Recorrer los Dos and Donts y obtener las imagenes
            if response['dos_donts']:
                for do_dont in response['dos_donts']:
                    image_url = rep.get_image(do_dont.get('image_id')) if do_dont.get('image_id') else None
                    do_dont['image_url'] = image_url.get('url') if image_url else None


            # creation_doc = response.get('creation_doc_id')
            # doc_url = None
            # if creation_doc:
            #     doc_url = self.get_doc_presigned_url('get_object', creation_doc)

            # response.update({'creation_doc_url': doc_url})
            
        except SinergiaException as e:
            logger.error(f"Error saving brand: {e.text}")
            raise e
        except Exception as err:
            logger.error(f"Error saving brand: {err}")
            raise SinergiaException('Error saving brand') 
        else:
            logger.debug(f"Brand saved successfully: {response['id']} - {response['name']}")
            return response
        
class GetBrandsUseCase(BrandUseCase):
    """docstring for GetBrandsUseCase."""
    def __init__(self, account_email):
        super().__init__(account_email)

    def execute(self, payload):
        try:
            logger.debug(f"Getting brands")

            account = self.get_account()
            parent_account = account['attributes']['parent_account']['data']['id'] if account['attributes']['parent_account']['data'] else account['id']

            if payload.get('orderKey') and payload.get('orderValue'):
                sort = f"{payload.get('orderKey')}:{payload.get('orderValue')}"
            else:
                sort = 'id:asc'

            filter = None
            if payload.get('filterKey') and payload.get('filterValue'):
                filter = {payload.get('filterKey'): {'$containsi': payload.get('filterValue')}}

            data = {
                'filters': {'account_id': parent_account, 'status': ACTIVE_DATA},
                'populate': ['parent_account'],
                'pagination': {
                    'start': payload.get('offset', 0),
                    'limit': payload.get('limit', 10),
                    'withCount': 'true'
                },
                'sort': sort
            }

            if filter:
                data['filters'].update(filter)

            brands = self.brand_repository.get_all(data)
            if not brands:
                logger.info(f"Brands not found")
                return {'data': [], 'count': 0, 'total': 0}
            
            rep = ImageLibraryRepository()

            # Recorrer las Brands
            for brand in brands['data']:
                # Recorrer los logos y obtener las imagenes
                logos = brand['logos']
                if logos and isinstance(logos, dict) and logos.get('values'):
                    for logo in logos.get('values'):
                        if logo.get('category', '') == 'main-logo':
                            image_url = rep.get_image(logo.get('image_id')) if logo.get('image_id') else None
                            logo['image_url'] = image_url.get('url') if image_url else None
                            break # Solo retornar la url del primer item

                # Recorrer los Dos and Donts y obtener las imagenes
                # if brand['dos_donts']:
                #     for do_dont in brand['dos_donts']:
                #         image_url = rep.get_image(do_dont.get('image_id')) if do_dont.get('image_id') else None
                #         do_dont['image_url'] = image_url.get('url') if image_url else None
                #         break # Solo retornar la url del primer item

                # creation_doc = brand.get('creation_doc_id')
                # doc_url = None
                # if creation_doc:
                #     doc_url = self.get_doc_presigned_url('get_object', creation_doc)

                # brand.update({'creation_doc_url': doc_url})

        except SinergiaException as e:
            logger.error(f"Error getting brands: {e.text}")
            raise e
        except Exception as err:
            logger.error(f"Error getting brands: {err}")
            raise SinergiaException('Error getting brands')
        else:
            logger.debug(f"Brands retrieved successfully")
            return brands
        
class UploadBrandLogoImageUseCase(BrandUseCase):
    """docstring for UploadBrandLogoImageUseCase."""
    def __init__(self, account_email):
        super().__init__(account_email)

    @retry(wait_fixed=5000, stop_max_attempt_number=4)
    def get_image_url(self, image_id):
        logger.debug(f"Getting image url for id: {image_id}")
        image_library_repository = ImageLibraryRepository()
        url = image_library_repository.get_image(image_id)
        if not url.get('url'):
            logger.error(f"Image not found: {image_id}")
            raise ImageLibraryException('Image not found')
        return url.get('url')

    def execute(self, brand_id, logo_id, files, buffer):
        try:
            logger.debug(f"Uploading brand logo image, brand id: {brand_id}, logo id: {logo_id}")
            b = buffer
            b.seek(0)

            account = self.get_account()
            parent_account = account['attributes']['parent_account']['data']['id'] if account['attributes']['parent_account']['data'] else account['id']
            
            brand = self.brand_repository.get_by_id_and_account(brand_id, parent_account)
            if not brand:
                logger.error(f"Brand not found: {brand_id}")
                raise DataNotFoundException('Brand not found')

            metadata = {
                'category': 'brand',
                'description': f"{files['file'][0]}",
                'type': 'original',
                'brand': brand_id
            }
            body = {
                'accountId': parent_account,
                'fileName': f"{files['file'][0]}",
                'contentType': f"{files['file'][2]}",
                #'fileSize': files['size_file'],
                'metadata': metadata
            }

            image_library_repository = ImageLibraryRepository()
            image_id = image_library_repository.upload_image(b, body)

            # Obtener URL de la imagen
            url = self.get_image_url(image_id)
            data = {
                'image_id': image_id,
                'image_url': url
            }
            
        except SinergiaException as e:
            logger.error(f"Error uploading brand logo image: {e.text}")
            raise e
        except Exception as err:
            logger.error(f"Error uploading brand logo image: {err}")
            raise ImageLibraryException('Error uploading brand logo image')
        else:
            logger.debug(f"Brand logo image uploaded successfully: {data}")
            return data
        
class UploadBrandFontFileUseCase(BrandUseCase):
    """docstring for UploadBrandFontFileUseCase."""
    def __init__(self, account_email):
        super().__init__(account_email)

    def allowed_file(self, filename):
        return '.' in filename and \
            filename.rsplit('.', 1)[1].lower() in FONT_ALLOWED_EXTENSIONS

    def execute(self, brand_id, font_id, file):
        try:
            logger.debug(f"Uploading brand font file, brand id: {brand_id}, font id: {font_id}")

            account = self.get_account()
            parent_account = account['attributes']['parent_account']['data']['id'] if account['attributes']['parent_account']['data'] else account['id']

            brand = self.brand_repository.get_by_id_and_account(brand_id, parent_account)
            if not brand:
                logger.error(f"Brand not found: {brand_id}")
                raise DataNotFoundException('Brand not found')
            
            filename = None
            
            if file and self.allowed_file(file.filename):
                filename = secure_filename(file.filename)
            else:
                logger.error(f"Invalid file type: {file.filename}")
                raise IncorrectValidationException('Invalid file type')

            key = f"{parent_account}/{brand_id}/{font_id}/{filename}"
            content_type = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
            response = self.brand_repository.upload_font_file(key, file, content_type)

            data = {
                'file': filename,
                'file_id': key
            }

        except SinergiaException as e:
            logger.error(f"Error uploading brand font file: {e.text}")
            raise e
        except Exception as err:
            logger.error(f"Error uploading brand font file: {err}")
            raise S3ClientException('Error uploading brand font file')
        else:
            logger.debug(f"Brand font file uploaded successfully: {data}")
            return data
        
class CreateBrandAIUseCase(BrandUseCase):
    """docstring for CreateBrandAIUseCase."""
    def __init__(self, account_email):
        super().__init__(account_email)

    def execute(self, payload):
        pass

class GetSourceFilesUseCase(BrandUseCase):
    """docstring for GetsourceFilesUseCase."""
    def __init__(self, account_email):
        super().__init__(account_email)
        self.brand_doc_repository = BrandDocumentRepository()

    def _build_documents(self, documents):
        docs = []
        for doc in documents:
            doc_url = self.get_doc_presigned_url('get_object', doc['attributes']['object_key']) if doc['attributes']['type'] == 'DOC' and doc['attributes']['object_key'] else None
            docs.append({
                'id': doc['id'],
                'name': doc['attributes']['name'],
                'type': doc['attributes']['type'],
                'presigned_url': doc_url
            })
        return docs

    def execute(self, brand_id):
        try:
            logger.debug(f"Getting Source Files by brand: {brand_id}")
            account = self.get_account()
            parent_account = account['attributes']['parent_account']['data']['id'] if account['attributes']['parent_account']['data'] else account['id']

            brand = self.brand_repository.get_by_id_and_account(brand_id, parent_account)
            if not brand:
                logger.error(f"Brand not found: {brand_id}")
                raise DataNotFoundException('Brand not found')
            
            # Buscar los documentos relacionados a la marca
            data = {
                'filters': {
                    'brand_ref': brand_id
                }
            }
            documents = self.brand_doc_repository.get_all(data)
            if not documents:
                logger.error(f"No documents found for brand: {brand_id}")
                raise DataNotFoundException('No documents found for brand')
            
            response = {
                'id': brand['id'],
                'name': brand['name'],
                'data_sources': self._build_documents(documents.get('data', []))
            }
            
        except SinergiaException as e:
            logger.error(f"Error getting Source Files by brand: {e.text}")
            raise e
        except Exception as err:
            logger.error(f"Error getting Source Files by brand: {err}")
            raise SinergiaException('Error getting brand') 
        else:
            return response
        
class RemoveDataSourceUseCase(BrandUseCase):
    """docstring for RemoveDataSourceUseCase."""
    def __init__(self, account_email):
        super().__init__(account_email)
        self.brand_doc_repository = BrandDocumentRepository()

    def execute(self, payload):
        try:
            logger.debug(f"Removing data source from brand: {payload.get('brand_id')}, data source id: {payload.get('data_source_id')}")
            brand_id = payload.get('brand_id')
            if not brand_id:
                logger.error(f"Missing brand_id in payload: {payload}")
                raise IncorrectValidationException('Missing brand_id in payload')
            
            data_source_id = payload.get('data_source_id')
            if not data_source_id:
                logger.error(f"Missing data_source_id in payload: {payload}")
                raise IncorrectValidationException('Missing data_source_id in payload')
            
            data_source_name = payload.get('data_source_name')
            if not data_source_name:
                logger.error(f"Missing data_source_name in payload: {payload}")
                raise IncorrectValidationException('Missing data_source_name in payload')


            account = self.get_account()
            parent_account = account['attributes']['parent_account']['data']['id'] if account['attributes']['parent_account']['data'] else account['id']

            brand = self.brand_repository.get_by_id_and_account(brand_id, parent_account)
            if not brand:
                logger.error(f"Brand not found: {brand_id}")
                raise DataNotFoundException('Brand not found')
            
            # Buscar el documento para validar que exista y que este relacionado con la marca
            data = {
                'filters': {
                    'id': data_source_id,
                    'brand_ref': brand_id,
                    'name': data_source_name
                }
            }
            document = self.brand_doc_repository.get_all(data)
            if not document or not document.get('data'):
                logger.error(f"Document not found for brand: {brand_id} and data source id: {data_source_id}")
                raise DataNotFoundException('Document not found for brand and data source id')
            
            # Eliminar el documento de la marca
            response = self.brand_doc_repository.delete_entry(data_source_id)
            if not response:
                logger.error(f"Error removing data source from brand: {response}")
                raise SinergiaException('Error removing data source from brand')
            
            # Actualizar el source de cada atributo de la marca (identity, logos, colors, dos_donts) para eliminar la referencia al documento eliminado
            identity = brand.get('identity', {})
            if identity:
                for key, value in identity.items():
                    sources = value.get('source', []) if isinstance(value, dict) else []
                    item = next((item for item in sources if item.get('value') == data_source_name), None)
                    if item:
                        sources.remove(item)
                        value['source'] = sources
                        content = value.get('value')
                        if isinstance(content, list):
                            content = []
                        else:
                            content = ''
                        
                        value['value'] = content

            # Validar que la seccion Identity este completa
            identity_complete = self._validate_identity({'identity': identity}) if identity else False
            identity['complete'] = identity_complete


            logos = brand.get('logos', {}).get('values', [])
            logos_updated = []
            for logo in logos:
                sources = logo.get('source', [])
                items = [item for item in sources if item.get('value') == data_source_name]
                if not items:
                    logos_updated.append(logo)

            logos = logos_updated
            
            # Validar que la seccion Logos tenga al menos un logo con category == 'main-logo', image_id y description para marcar la seccion como completa
            logos_complete = self._validate_logos({'logos': logos}) if isinstance(logos, list) else False
            brand['logos']['complete'] = logos_complete
            brand['logos']['values'] = logos


            colors = brand.get('colors', {}).get('values', [])
            colors_updated = []
            for color in colors:
                sources = color.get('source', [])
                items = [item for item in sources if item.get('value') == data_source_name]
                if not items:
                    colors_updated.append(color)

            colors = colors_updated

            # Validar que la seccion Colors tenga al menos un color con category == 'primary' and name and hex_code para marcar la seccion como completa
            colors_complete = self._validate_colors({'colors': colors}) if isinstance(colors, list) else False
            brand['colors']['complete'] = colors_complete
            brand['colors']['values'] = colors


            dos_donts = brand.get('dos_donts', [])
            dos_donts_updated = []
            for do_dont in dos_donts:
                sources = do_dont.get('source', [])
                items = [item for item in sources if item.get('value') == data_source_name]
                if not items:
                    dos_donts_updated.append(do_dont)

            dos_donts = dos_donts_updated
            brand['dos_donts'] = dos_donts

            completed = identity_complete and colors_complete and logos_complete and brand.get('typography', {}).get('complete', False)

            # Actualizar la marca
            data = {
                'identity': brand['identity'],
                'logos': brand['logos'],
                'colors': brand['colors'],
                'typography': brand['typography'],
                'dos_donts': brand['dos_donts'],
                'complete': completed
            }

            response = self.brand_repository.update_brand(brand_id, data)
            if not response:
                logger.error(f"Error saving brand: {response}")
                raise SinergiaException('Error saving brand')
            
            rep = ImageLibraryRepository()
            
            # Recorrer los logos y obtener las imagenes
            logos = response['logos']
            if logos and isinstance(logos, dict) and logos.get('values'):
                for logo in logos.get('values'):
                    image_url = rep.get_image(logo.get('image_id')) if logo.get('image_id') else None
                    logo['image_url'] = image_url.get('url') if image_url else None

            # Recorrer los Dos and Donts y obtener las imagenes
            if response['dos_donts']:
                for do_dont in response['dos_donts']:
                    image_url = rep.get_image(do_dont.get('image_id')) if do_dont.get('image_id') else None
                    do_dont['image_url'] = image_url.get('url') if image_url else None

        except SinergiaException as e:
            logger.error(f"Error removing data source from brand: {e.text}")
            raise e
        except Exception as e:
            logger.error(f"Error removing data source from brand: {e}")
            raise SinergiaException('Error removing data source from brand') 
        else:
            return response
        
class EditBrandUseCase(BrandUseCase):
    """docstring for EditBrandUseCase."""
    def __init__(self, account_email):
        super().__init__(account_email)
        self.brand_doc_repository = BrandDocumentRepository()

    def _remove_source_references(self, brand, delete_data_sources):
        """Remove source references from brand attributes for deleted documents."""
        doc_names = {doc.get('data_source_name') for doc in delete_data_sources}
        
        # Update identity sources
        identity = brand.get('identity', {})
        for key, value in identity.items():
            if isinstance(value, dict) and 'source' in value:
                value['source'] = [s for s in value.get('source', []) if s.get('value') not in doc_names]
        
        # Update logos sources
        logos = brand.get('logos', {}).get('values', [])
        for logo in logos:
            if 'source' in logo:
                logo['source'] = [s for s in logo.get('source', []) if s.get('value') not in doc_names]
        
        # Update colors sources
        colors = brand.get('colors', {}).get('values', [])
        for color in colors:
            if 'source' in color:
                color['source'] = [s for s in color.get('source', []) if s.get('value') not in doc_names]
        
        # Update dos_donts sources
        dos_donts = brand.get('dos_donts', [])
        for do_dont in dos_donts:
            if 'source' in do_dont:
                do_dont['source'] = [s for s in do_dont.get('source', []) if s.get('value') not in doc_names]
        
        return brand

    def execute(self, brand_id, payload):
        try:
            logger.debug(f"Editing brand: {brand_id}")
            
            # Validate payload structure
            if not payload or not isinstance(payload, dict):
                raise IncorrectValidationException('Invalid payload')
            
            name = payload.get('name')
            website_url = payload.get('website_url')
            urls = payload.get('urls')
            files_payload = payload.get('files')
            analyze = payload.get('analyze', False)
            delete_data_sources = payload.get('delete_data_sources', [])
            language =  payload.get('language')
            
            # Validate required fields
            if not name:
                raise IncorrectValidationException('name is required')
            if not website_url:
                raise IncorrectValidationException('website_url is required')
            if not language:
                raise IncorrectValidationException('language is required')
            
            # Validate analyze is bool
            if not isinstance(analyze, bool):
                raise IncorrectValidationException('analyze must be a boolean')
            
            # Validate urls is array if exists
            if urls is not None and not isinstance(urls, list):
                raise IncorrectValidationException('urls must be a JSON array')
            
            # Validate delete_data_sources format
            if delete_data_sources:
                if not isinstance(delete_data_sources, list):
                    raise IncorrectValidationException('delete_data_sources must be a JSON array')
                for ds in delete_data_sources:
                    if not isinstance(ds, dict) or 'data_source_id' not in ds or 'data_source_name' not in ds:
                        raise IncorrectValidationException('delete_data_sources items must have data_source_id and data_source_name')
            
            # Validate files format
            if files_payload:
                if not isinstance(files_payload, list):
                    raise IncorrectValidationException('files must be a JSON array')
                for f in files_payload:
                    if not isinstance(f, dict) or 'filename' not in f or 'content_type' not in f or 'content' not in f:
                        raise IncorrectValidationException('files items must have filename, content_type, and content')
            
            # Validate account
            account = self.get_account()
            parent_account = account['attributes']['parent_account']['data']['id'] if account['attributes']['parent_account']['data'] else account['id']
            
            # Validate brand
            brand = self.brand_repository.get_by_id_and_account(brand_id, parent_account)
            if not brand:
                raise DataNotFoundException('Brand not found')
            
            # Delete data sources from brand-documents
            if delete_data_sources:
                for ds in delete_data_sources:
                    try:
                        self.brand_doc_repository.delete_entry(ds['data_source_id'])
                        logger.info(f"Deleted data source: {ds['data_source_id']} - {ds['data_source_name']}")
                    except Exception as e:
                        logger.warning(f"Failed to delete data source {ds['data_source_id']}: {e}")
            
                # Remove source references from brand attributes
                brand = self._remove_source_references(brand, delete_data_sources)
            
            # Save URLs to brand-documents
            if urls:
                for url in urls:
                    try:
                        doc_data = {
                            'name': url,
                            'type': 'URL',
                            'object_url': url,
                            'brand_ref': brand_id
                        }
                        self.brand_doc_repository.create(doc_data)
                        logger.info(f"Saved URL to brand-documents: {url}")
                    except Exception as e:
                        logger.warning(f"Failed to save URL {url}: {e}")
            
            # Upload files to S3 and save to brand-documents
            if files_payload:
                docs_config = self.get_docs_bucket_config()
                for file_item in files_payload:
                    try:
                        from io import BytesIO
                        filename = file_item['filename']
                        content = file_item['content']
                        content_type = file_item['content_type']
                        
                        # Upload to S3
                        key = f"{parent_account}/{brand_id}/creation_doc/{filename}"
                        file_buffer = BytesIO(content if isinstance(content, bytes) else content.encode())
                        object_s3 = self.brand_repository.upload_file(key, file_buffer, docs_config['bucket_name'], content_type)
                        
                        # Get presigned URL
                        # object_url = self.get_doc_presigned_url('get_object', key)
                        
                        # Save to brand-documents
                        doc_data = {
                            'name': filename,
                            'type': 'DOC',
                            'bucket': docs_config['bucket_name'],
                            'region': docs_config['region'],
                            'object_key': key,
                            # 'object_url': object_url,
                            'brand_ref': brand_id
                        }
                        self.brand_doc_repository.create(doc_data)
                        logger.info(f"Uploaded and saved file to brand-documents: {filename}")
                    except Exception as e:
                        logger.warning(f"Failed to upload file {file_item.get('filename')}: {e}")
            
            if analyze:
                # Path: analyze == True
                # Clean identity attributes
                identity = brand.get('identity', {})
                if identity:
                    for key in ['values', 'vision', 'mission', 'about_us', 'tone_voice']:
                        if key in identity and isinstance(identity[key], dict):
                            identity[key]['value'] = '' if key != 'values' and key != 'tone_voice' else []
                            identity[key]['source'] = []
                    identity['complete'] = False
                
                logos_complete = self._validate_logos({'logos': brand.get('logos', {}).get('values', [])}) if brand.get('logos') else False
                colors_complete = self._validate_colors({'colors': brand.get('colors', {}).get('values', [])}) if brand.get('colors') else False
                typography_complete = brand.get('typography', {}).get('complete', False)

                completed = identity['complete'] and colors_complete and logos_complete and typography_complete
                
                data = {
                    'name': name,
                    'website': website_url,
                    'identity': identity,
                    'logos': {'complete': logos_complete, 'values': brand.get('logos', {}).get('values', [])},
                    'colors': {'complete': colors_complete, 'values': brand.get('colors', {}).get('values', [])},
                    'dos_donts': brand.get('dos_donts', []),
                    'complete': completed,
                    'language': language.capitalize()
                }
                
                response = self.brand_repository.update_brand(brand_id, data)
                if not response:
                    raise SinergiaException('Error updating brand')
                
                try:
                    # Invoke N8N workflow for reanalysis
                    from app.v1.repository.base import N8NClient
                    n8n_client = N8NClient(credentials={'username': self.account_email})
                    n8n_payload = {
                        'brand_id': brand_id,
                        'language': language.capitalize()
                    }
                    
                    n8n_response = n8n_client.executePut('/webhook/v2/new_brand/reanalyze',n8n_payload,True)
                except Exception as e:
                    logger.warning(f"Failed to invoke N8N workflow for reanalysis: {e}")
                
                brand = self.brand_repository.get_by_id_and_account(brand_id, parent_account)
                if not brand:
                    logger.error(f"Brand not found: {brand_id}")
                    raise DataNotFoundException('Brand not found')
                
                rep = ImageLibraryRepository()

                # Recorrer los logos y obtener las imagenes
                logos = brand['logos']
                if logos and isinstance(logos, dict) and logos.get('values'):
                    for logo in logos.get('values'):
                        image_url = rep.get_image(logo.get('image_id')) if logo.get('image_id') else None
                        logo['image_url'] = image_url.get('url') if image_url else None

                # Recorrer los Dos and Donts y obtener las imagenes
                if brand['dos_donts']:
                    for do_dont in brand['dos_donts']:
                        image_url = rep.get_image(do_dont.get('image_id')) if do_dont.get('image_id') else None
                        do_dont['image_url'] = image_url.get('url') if image_url else None

                return brand

            else:
                # Path: analyze == False
                identity_complete = self._validate_identity({'identity': brand.get('identity', {})}) if brand.get('identity') else False
                logos_complete = self._validate_logos({'logos': brand.get('logos', {}).get('values', [])}) if brand.get('logos') else False
                colors_complete = self._validate_colors({'colors': brand.get('colors', {}).get('values', [])}) if brand.get('colors') else False
                typography_complete = brand.get('typography', {}).get('complete', False)
                
                data = {
                    'name': name,
                    'website': website_url,
                    'identity': {'complete': identity_complete, **brand.get('identity', {})},
                    'logos': {'complete': logos_complete, 'values': brand.get('logos', {}).get('values', [])},
                    'colors': {'complete': colors_complete, 'values': brand.get('colors', {}).get('values', [])},
                    'dos_donts': brand.get('dos_donts', []),
                    'complete': identity_complete and logos_complete and colors_complete and typography_complete,
                    'language': language.capitalize()
                }
                
                response = self.brand_repository.update_brand(brand_id, data)
                if not response:
                    raise SinergiaException('Error updating brand')
                
                # Recorrer los logos y obtener las imagenes
                logos = response['logos']
                if logos and isinstance(logos, dict) and logos.get('values'):
                    for logo in logos.get('values'):
                        image_url = rep.get_image(logo.get('image_id')) if logo.get('image_id') else None
                        logo['image_url'] = image_url.get('url') if image_url else None

                # Recorrer los Dos and Donts y obtener las imagenes
                if response['dos_donts']:
                    for do_dont in response['dos_donts']:
                        image_url = rep.get_image(do_dont.get('image_id')) if do_dont.get('image_id') else None
                        do_dont['image_url'] = image_url.get('url') if image_url else None
                
                return response
                
        except SinergiaException as e:
            logger.error(f"Error editing brand: {e.text}")
            raise e
        except Exception as err:
            logger.error(f"Error editing brand: {err}")
            raise SinergiaException('Error editing brand')
