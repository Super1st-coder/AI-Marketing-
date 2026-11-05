import os
import requests
import pandas as pd
import logging
from io import BytesIO
from app.v1.repository.base import N8NClient
from app.v1.resources.base import ProxySecureResource
from config import Config

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class ExcelManagerUseCase(ProxySecureResource):
    def __init__(self):
        logger.info("Initializing ExcelManagerUseCase")
        try:
            self.security_credentials = self.checkCredentials()
            logger.info(f"Security credentials obtained: {self.security_credentials}")
            
            self.n8n_client = N8NClient(credentials=self.security_credentials)
            logger.info("N8NClient initialized successfully with credentials")
            
            self.config = Config()
            logger.info("Config loaded successfully")
            logger.info("ExcelManagerUseCase initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing ExcelManagerUseCase: {str(e)}", exc_info=True)
            raise

    def export_to_excel(self, brand_id=None, campaign_id=None, project_id=None, filters=None):
        """
        Export data to Excel format
        
        Args:
            brand_id: Optional brand ID to filter ads
            campaign_id: Optional campaign ID to filter ads
            project_id: Optional project ID to filter ads
            filters: Optional additional filters
            
        Returns:
            tuple: (excel_file_bytes, filename, status_code)
        """
        logger.info(f"Starting export_to_excel with params: brand_id={brand_id}, campaign_id={campaign_id}, project_id={project_id}, filters={filters}")
        
        try:
            logger.info("Fetching ads data from n8n...")
            ads_data = self._fetch_ads_data(brand_id, campaign_id, project_id, filters)
            logger.info(f"Ads data received: {ads_data}")
            
            if not ads_data or not ads_data.get('data'):
                logger.warning(f"No ads data received or empty data: {ads_data}")
                return self._create_empty_excel_file(brand_id, campaign_id, project_id)
            
            logger.info("Transforming data to DataFrame...")
            df = self._transform_to_dataframe(ads_data['data'])
            logger.info(f"DataFrame created with shape: {df.shape}")
            
            if df.empty:
                logger.error("DataFrame is empty after transformation")
                return None, None, 404
            
            logger.info("Generating Excel file...")
            excel_buffer = BytesIO()
            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Ads_Data', index=False)
                
                worksheet = writer.sheets['Ads_Data']
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 50)
                    worksheet.column_dimensions[column_letter].width = adjusted_width
            
            excel_buffer.seek(0)
            filename = f"ads_export_{brand_id or 'all'}_{campaign_id or 'all'}_{project_id or 'all'}.xlsx"
            logger.info(f"Excel file generated successfully: {filename}")
            
            return excel_buffer.getvalue(), filename, 200
            
        except Exception as e:
            logger.error(f"Error exporting ads to Excel: {str(e)}", exc_info=True)
            return None, None, 500
    
    def import_from_excel(self, excel_file, object_type='ads', validation_rules=None):
        """
        Import data from Excel file to create/update ads or other objects
        
        Args:
            excel_file: BytesIO object containing Excel file
            object_type: Type of object to import ('ads', 'campaigns', 'brands', 'projects')
            validation_rules: Optional validation rules for the data
            
        Returns:
            tuple: (import_result, status_code, message)
        """
        try:
            df = pd.read_excel(excel_file)
            
            if df.empty:
                return None, 400, "Excel file is empty or contains no data"
            
            validation_result = self._validate_excel_structure(df, object_type)
            if not validation_result['valid']:
                return None, 400, f"Invalid Excel structure: {validation_result['message']}"
            
            structured_data = self._transform_excel_to_structured_data(df, object_type)
            
            if validation_rules:
                business_validation = self._validate_business_rules(structured_data, validation_rules)
                if not business_validation['valid']:
                    return None, 400, f"Business validation failed: {business_validation['message']}"
            
            import_result = self._import_data_to_n8n(structured_data, object_type)
            
            return import_result, 200, "Data imported successfully"
            
        except Exception as e:
            print(f"Error importing from Excel: {str(e)}")
            return None, 500, f"Import error: {str(e)}"
    
    def bulk_export_to_excel(self, export_configs):
        """
        Export multiple ads datasets to Excel with multiple sheets
        
        Args:
            export_configs: List of export configurations
            
        Returns:
            tuple: (excel_file_bytes, filename, status_code)
        """
        try:
            excel_buffer = BytesIO()
            
            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                for i, config in enumerate(export_configs):
                    excel_data, _, status_code = self.export_to_excel(
                        brand_id=config.get('brand_id'),
                        campaign_id=config.get('campaign_id'),
                        project_id=config.get('project_id'),
                        filters=config.get('filters', {})
                    )
                    
                    if excel_data is not None:
                        df = pd.read_excel(BytesIO(excel_data))
                        
                        sheet_name = config.get('sheet_name', f'Ads_Export_{i+1}')
                        if len(sheet_name) > 31:  
                            sheet_name = f'Ads_Export_{i+1}'
                        
                        df.to_excel(writer, sheet_name=sheet_name, index=False)
                        
                        worksheet = writer.sheets[sheet_name]
                        for column in worksheet.columns:
                            max_length = 0
                            column_letter = column[0].column_letter
                            for cell in column:
                                try:
                                    if len(str(cell.value)) > max_length:
                                        max_length = len(str(cell.value))
                                except:
                                    pass
                                adjusted_width = min(max_length + 2, 50)
                                worksheet.column_dimensions[column_letter].width = adjusted_width
            
            excel_buffer.seek(0)
            filename = f"bulk_ads_export_{len(export_configs)}_sheets.xlsx"
            
            return excel_buffer.getvalue(), filename, 200
            
        except Exception as e:
            print(f"Error in bulk export: {str(e)}")
            return None, None, 500
    
    def export_to_excel_by_channel_group(self, brand_id, campaign_id, channel_group_id):
        """
        Export ads data to Excel format using the existing ad_structure endpoint for a specific channel group
        
        Args:
            brand_id: Brand ID
            campaign_id: Campaign ID  
            channel_group_id: Channel Group ID
            
        Returns:
            tuple: (excel_file_bytes, filename, status_code)
        """
        logger.info(f"Starting export_to_excel_by_channel_group with params: brand_id={brand_id}, campaign_id={campaign_id}, channel_group_id={channel_group_id}")
        
        try:
            logger.info("Fetching ads data from n8n using ad_structure endpoint for specific channel group...")
            ads_data = self._fetch_ads_data_by_channel_group(brand_id, campaign_id, channel_group_id)
            logger.info(f"Ads data received: {ads_data}")
            
            if not ads_data or not ads_data.get('data'):
                logger.warning(f"No ads data received or empty data: {ads_data}")
                return self._create_empty_excel_file(brand_id, campaign_id, channel_group_id=channel_group_id)
            
            logger.info("Transforming data to DataFrame...")
            df = self._transform_single_structure_to_dataframe(ads_data['data'])
            logger.info(f"DataFrame created with shape: {df.shape}")
            
            if df.empty:
                logger.error("DataFrame is empty after transformation")
                return self._create_empty_excel_file(brand_id, campaign_id, channel_group_id=channel_group_id)
            
            logger.info("Generating Excel file...")
            excel_buffer = BytesIO()
            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Ads_Data', index=False)
                
                worksheet = writer.sheets['Ads_Data']
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 50)
                    worksheet.column_dimensions[column_letter].width = adjusted_width
            
            excel_buffer.seek(0)
            filename = f"ads_export_brand_{brand_id}_campaign_{campaign_id}_channel_group_{channel_group_id}.xlsx"
            logger.info(f"Excel file generated successfully: {filename}")
            
            return excel_buffer.getvalue(), filename, 200
            
        except Exception as e:
            logger.error(f"Error exporting ads to Excel by channel group: {str(e)}", exc_info=True)
            return None, None, 500
    
    def _fetch_ads_data_from_structure(self, brand_id, campaign_id, project_id=None, filters=None):
        """
        Fetch ads data from n8n using the existing ad_structure endpoint
        """
        logger.info(f"Fetching ads data using ad_structure with params: brand_id={brand_id}, campaign_id={campaign_id}, project_id={project_id}, filters={filters}")
        
        try:
            channel_groups = self._get_campaign_channel_groups(brand_id, campaign_id)
            if not channel_groups:
                logger.warning("No channel groups found for campaign")
                return None
            
            all_ads_data = []
            
            for channel_group in channel_groups:
                try:
                    endpoint = f"/webhook/v2/ad_structure/channel_group"
                    params = {
                        'brand_id': brand_id,
                        'campaign_id': campaign_id,
                        'channel_group_id': channel_group['id']
                    }
                    
                    logger.info(f"Calling n8n endpoint: {endpoint} with params: {params}")
                    response = self.n8n_client.executeGet(endpoint, params=params)
                    logger.info(f"n8n response received for channel_group {channel_group['id']}: {response}")
                    
                    if response and response.get('ok') == 1 and response.get('data'):
                        all_ads_data.append(response['data'])
                    
                except Exception as e:
                    logger.error(f"Error fetching ad structure for channel_group {channel_group['id']}: {str(e)}")
                    continue
            
            if not all_ads_data:
                logger.warning("No ad structure data found for any channel group")
                return None
            
            combined_data = {
                'ok': 1,
                'data': {
                    'brand_id': brand_id,
                    'campaign_id': campaign_id,
                    'channel_groups': all_ads_data
                }
            }
            
            return combined_data
            
        except Exception as e:
            logger.error(f"Error fetching ads data from structure: {str(e)}", exc_info=True)
            return None
    
    def _get_campaign_channel_groups(self, brand_id, campaign_id):
        """
        Get channel groups for a campaign
        """
        try:
            endpoint = "/webhook/v2/ad_structure/channel_group"
            params = {
                'brand_id': brand_id,
                'campaign_id': campaign_id
            }
            
            logger.info(f"Getting channel groups: {endpoint} with params: {params}")
            response = self.n8n_client.executeGet(endpoint, params=params)
            
            if response and response.get('ok') == 1:
                if 'channel_groups' in response.get('data', {}):
                    return response['data']['channel_groups']
                elif 'channel_group' in response.get('data', {}):
                    return [{'id': response['data']['channel_group']}]
                elif 'ad_sets' in response.get('data', {}):
                    return [{'id': 1}] 
            
            logger.info("Trying alternative endpoint for channel groups...")
            alt_endpoint = "/webhook/v2/campaign/channel_groups"
            alt_response = self.n8n_client.executeGet(alt_endpoint, params=params)
            
            if alt_response and alt_response.get('ok') == 1:
                return alt_response.get('data', [])
            
            logger.warning("No channel groups found, using default")
            return [{'id': 1}]
            
        except Exception as e:
            logger.error(f"Error fetching ads data: {str(e)}", exc_info=True)
            return None
    
    def _transform_to_dataframe(self, ads_data):
        """
        Transform ads data to pandas DataFrame
        """
        try:
            flattened_data = []
            
            for ad in ads_data:
                ad_row = self._flatten_ad_data(ad)
                flattened_data.append(ad_row)
            
            df = pd.DataFrame(flattened_data)
            
            priority_columns = [
                'id', 'name', 'brand_name', 'campaign_name', 'project_name',
                'ad_set_name', 'channel_name', 'status', 'created_at'
            ]
            
            existing_columns = [col for col in priority_columns if col in df.columns]
            remaining_columns = [col for col in df.columns if col not in existing_columns]
            
            df = df[existing_columns + remaining_columns]
            
            return df
            
        except Exception as e:
            print(f"Error transforming data to DataFrame: {str(e)}")
            return pd.DataFrame()
    
    def _flatten_channel_group_data(self, channel_group_data, flattened_data):
        """
        Flatten nested ad data structure
        """
        flattened = {}
        
        flattened['id'] = ad.get('id')
        flattened['name'] = ad.get('name')
        flattened['status'] = ad.get('status')
        flattened['created_at'] = ad.get('createdAt')
        flattened['updated_at'] = ad.get('updatedAt')
        
        if ad.get('ad_set_ref'):
            ad_set = ad['ad_set_ref']
            flattened['ad_set_id'] = ad_set.get('id')
            flattened['ad_set_name'] = ad_set.get('name')
            
            if ad_set.get('funnel_flow_ref'):
                funnel_flow = ad_set['funnel_flow_ref']
                flattened['funnel_flow_id'] = funnel_flow.get('id')
                flattened['funnel_flow_name'] = funnel_flow.get('name')
                
                if funnel_flow.get('campaign_ref'):
                    campaign = funnel_flow['campaign_ref']
                    flattened['funnel_flow_id'] = campaign.get('id')
                    flattened['campaign_name'] = campaign.get('name')
                    
                    if campaign.get('project_ref'):
                        project = campaign['project_ref']
                        flattened['project_id'] = project.get('id')
                        flattened['project_name'] = project.get('name')
                        
                        if project.get('brand_ref'):
                            brand = project['brand_ref']
                            flattened['brand_id'] = brand.get('id')
                            flattened['brand_name'] = brand.get('name')
        
        if ad.get('ad_channels'):
            ad_channels = ad['ad_channels']
            if isinstance(ad_channels, list) and len(ad_channels) > 0:
                first_channel = ad_channels[0]
                flattened['channel_id'] = first_channel.get('id')
                flattened['channel_name'] = first_channel.get('name')
                flattened['media_template_id'] = first_channel.get('media_template_id')
                flattened['media_template_name'] = first_channel.get('media_template_name')
                flattened['media_generated'] = first_channel.get('media_generated')
                
                if first_channel.get('media_elements'):
                    media_elements = first_channel['media_elements']
                    if isinstance(media_elements, dict):
                        for key, value in media_elements.items():
                            flattened[f'media_{key}'] = str(value) if value is not None else ''
                
                if first_channel.get('channel_attributes'):
                    channel_attrs = first_channel['channel_attributes']
                    if isinstance(channel_attrs, dict):
                        for key, value in channel_attrs.items():
                            flattened[f'channel_attr_{key}'] = str(value) if value is not None else ''
                
                flattened['total_channels'] = len(ad_channels)
        
        if ad.get('experiment_ref'):
            experiment = ad['experiment_ref']
            flattened['experiment_id'] = experiment.get('id')
            flattened['experiment_name'] = experiment.get('name')
            flattened['experiment_status'] = experiment.get('status')
        
        return flattened
    
    def _validate_excel_structure(self, df, object_type):
        """
        Validate Excel file structure based on object type
        """
        try:
            required_columns = self._get_required_columns(object_type)
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                return {
                    'valid': False,
                    'message': f"Missing required columns: {', '.join(missing_columns)}"
                }
            
            return {'valid': True, 'message': 'Structure is valid'}
            
        except Exception as e:
            return {'valid': False, 'message': f"Validation error: {str(e)}"}
    
    def _get_required_columns(self, object_type):
        """
        Get required columns for different object types
        """
        column_maps = {
            'ads': ['name', 'status', 'ad_set_id'],
            'campaigns': ['name', 'status', 'project_id'],
            'brands': ['name', 'description'],
            'projects': ['name', 'status', 'brand_id']
        }
        
        return column_maps.get(object_type, ['name'])
    
    def _transform_excel_to_structured_data(self, df, object_type):
        """
        Transform Excel DataFrame to structured data for import
        """
        try:
            structured_data = []
            
            for index, row in df.iterrows():
                row_dict = {}
                for column in df.columns:
                    value = row[column]
                    if pd.isna(value):
                        row_dict[column] = None
                    else:
                        row_dict[column] = value
                
                structured_data.append(row_dict)
            
            return structured_data
            
        except Exception as e:
            print(f"Error transforming Excel to structured data: {str(e)}")
            return []
    
    def _validate_business_rules(self, data, rules):
        """
        Validate business rules for imported data
        """
        try:
            for rule in rules:
                if rule['type'] == 'required_field':
                    for item in data:
                        if not item.get(rule['field']):
                            return {
                                'valid': False,
                                'message': f"Required field '{rule['field']}' is missing"
                            }
                
                elif rule['type'] == 'field_format':
                    for item in data:
                        value = item.get(rule['field'])
                        if value and not rule['validator'](value):
                            return {
                                'valid': False,
                                'message': f"Field '{rule['field']}' has invalid format"
                            }
            
            return {'valid': True, 'message': 'Business rules validation passed'}
            
        except Exception as e:
            return {'valid': False, 'message': f"Business validation error: {str(e)}"}
    
    def _import_data_to_n8n(self, data, object_type):
        """
        Import data to n8n based on object type
        """
        try:
            endpoint_map = {
                'ads': '/api/ads',
                'campaigns': '/api/campaigns',
                'brands': '/api/brands',
                'projects': '/api/projects'
            }
            
            endpoint = endpoint_map.get(object_type, '/api/ads')
            import_results = []
            
            for item in data:
                try:
                    clean_item = {k: v for k, v in item.items() if v is not None and v != ''}
                    
                    response = self.n8n_client.executePost(endpoint, clean_item)
                    import_results.append({
                        'data': clean_item,
                        'result': response,
                        'success': True
                    })
                    
                except Exception as e:
                    import_results.append({
                        'data': item,
                        'error': str(e),
                        'success': False
                    })
            
            return {
                'total_items': len(data),
                'successful_imports': len([r for r in import_results if r['success']]),
                'failed_imports': len([r for r in import_results if not r['success']]),
                'results': import_results
            }
            
        except Exception as e:
            print(f"Error importing data to n8n: {str(e)}")
            return None
    
    def _fetch_ads_data_by_channel_group(self, brand_id, campaign_id, channel_group_id):
        """
        Fetch ads data from n8n using the existing ad_structure endpoint for a specific channel group
        """
        logger.info(f"Fetching ads data for channel_group {channel_group_id} with params: brand_id={brand_id}, campaign_id={campaign_id}")
        
        try:
            endpoint = "/webhook/v2/ad_structure/channel_group"
            params = {
                'brand_id': brand_id,
                'campaign_id': campaign_id,
                'channel_group_id': channel_group_id
            }
            
            logger.info(f"Calling n8n endpoint: {endpoint} with params: {params}")
            response = self.n8n_client.executeGet(endpoint, params=params)
            logger.info(f"n8n response received: {response}")
            
            if response is None:
                logger.error("Received None response from n8n")
                return None
            
            if not isinstance(response, dict):
                logger.error(f"Invalid response type: {type(response)}, content: {response}")
                return None
            
            if 'data' not in response:
                logger.warning(f"Response missing 'data' key. Available keys: {list(response.keys()) if isinstance(response, dict) else 'N/A'}")
                return {'data': []}
            
            return response
            
        except Exception as e:
            logger.error(f"Error fetching ads data by channel group: {str(e)}", exc_info=True)
            return None
    
    def _transform_single_structure_to_dataframe(self, structure_data):
        """
        Transform a single channel group's ad structure data to a flat DataFrame
        """
        try:
            flattened_data = []
            
            if 'ad_sets' in structure_data:
                self._flatten_channel_group_data(structure_data, flattened_data)
            else:
                logger.warning(f"Unexpected structure format: {structure_data}")
                return pd.DataFrame()
            
            df = pd.DataFrame(flattened_data)
            
            priority_columns = [
                'brand_id', 'campaign_id', 'channel_group_id', 'channel_group_name',
                'ad_set_id', 'ad_set_name', 'ad_id', 'ad_name', 'status'
            ]
            
            existing_priority = [col for col in priority_columns if col in df.columns]
            remaining_columns = [col for col in df.columns if col not in existing_priority]
            
            df = df[existing_priority + remaining_columns]
            
            return df
            
        except Exception as e:
            logger.error(f"Error transforming single structure to DataFrame: {str(e)}", exc_info=True)
            return pd.DataFrame()
    
    def _flatten_channel_group_data(self, channel_group_data, flattened_data):
        """
        Flatten a single channel group's data structure
        """
        try:
            channel_group_id = channel_group_data.get('id', 'N/A')
            channel_group_name = channel_group_data.get('name', 'N/A')
            
            if 'ad_sets' in channel_group_data:
                for ad_set in channel_group_data['ad_sets']:
                    ad_set_id = ad_set.get('id', 'N/A')
                    ad_set_name = ad_set.get('name', 'N/A')
                    
                    if 'ads' in ad_set:
                        for ad in ad_set['ads']:
                            ad_row = {
                                'brand_id': channel_group_data.get('brand_id', 'N/A'),
                                'campaign_id': channel_group_data.get('campaign_id', 'N/A'),
                                'channel_group_id': channel_group_id,
                                'channel_group_name': channel_group_name,
                                'ad_set_id': ad_set_id,
                                'ad_set_name': ad_set_name,
                                'ad_id': ad.get('id', 'N/A'),
                                'ad_name': ad.get('name', 'N/A'),
                                'status': ad.get('status', 'Active'),
                                'created_at': ad.get('created_at', 'N/A'),
                                'updated_at': ad.get('updated_at', 'N/A')
                            }
                            
                            for key, value in ad.items():
                                if key not in ['id', 'name', 'status', 'created_at', 'updated_at']:
                                    ad_row[f'ad_{key}'] = str(value) if value is not None else ''
                            
                            flattened_data.append(ad_row)
                    else:
                        ad_row = {
                            'brand_id': channel_group_data.get('brand_id', 'N/A'),
                            'campaign_id': channel_group_data.get('campaign_id', 'N/A'),
                            'channel_group_id': channel_group_id,
                            'channel_group_name': channel_group_name,
                            'ad_set_id': ad_set_id,
                            'ad_set_name': ad_set_name,
                            'ad_id': 'N/A',
                            'ad_name': 'N/A',
                            'status': 'No Ads',
                            'created_at': 'N/A',
                            'updated_at': 'N/A'
                        }
                        flattened_data.append(ad_row)
            else:
                ad_row = {
                    'brand_id': channel_group_data.get('brand_id', 'N/A'),
                    'campaign_id': channel_group_data.get('campaign_id', 'N/A'),
                    'channel_group_id': channel_group_id,
                    'channel_group_name': channel_group_name,
                    'ad_set_id': 'N/A',
                    'ad_set_name': 'N/A',
                    'ad_id': 'N/A',
                    'ad_name': 'N/A',
                    'status': 'No Ad Sets',
                    'created_at': 'N/A',
                    'updated_at': 'N/A'
                }
                flattened_data.append(ad_row)
                
        except Exception as e:
            logger.error(f"Error flattening channel group data: {str(e)}", exc_info=True)
    
    def _create_empty_excel_file(self, brand_id=None, campaign_id=None, project_id=None, channel_group_id=None):
        """
        Create an empty Excel file with proper headers when no data is found
        """
        try:
            logger.info("Creating empty Excel file with headers")
            
            # Create empty DataFrame with expected columns for the channel group export
            if channel_group_id:
                empty_data = {
                    'brand_id': [],
                    'campaign_id': [],
                    'channel_group_id': [],
                    'channel_group_name': [],
                    'ad_set_id': [],
                    'ad_set_name': [],
                    'ad_id': [],
                    'ad_name': [],
                    'status': [],
                    'created_at': [],
                    'updated_at': []
                }
            else:
                empty_data = {
                    'id': [],
                    'name': [],
                    'brand_name': [],
                    'campaign_name': [],
                    'project_name': [],
                    'ad_set_name': [],
                    'channel_name': [],
                    'status': [],
                    'created_at': []
                }
            
            df = pd.DataFrame(empty_data)
            
            excel_buffer = BytesIO()
            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Ads_Data', index=False)
                
                worksheet = writer.sheets['Ads_Data']
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 50)
                    worksheet.column_dimensions[column_letter].width = adjusted_width
            
            excel_buffer.seek(0)
            
            if channel_group_id:
                filename = f"ads_export_brand_{brand_id or 'all'}_campaign_{campaign_id or 'all'}_channel_group_{channel_group_id}_empty.xlsx"
            else:
                filename = f"ads_export_{brand_id or 'all'}_{campaign_id or 'all'}_{project_id or 'all'}_empty.xlsx"
                
            logger.info(f"Empty Excel file created: {filename}")
            
            return excel_buffer.getvalue(), filename, 200
            
        except Exception as e:
            logger.error(f"Error creating empty Excel file: {str(e)}", exc_info=True)
            return None, None, 500
