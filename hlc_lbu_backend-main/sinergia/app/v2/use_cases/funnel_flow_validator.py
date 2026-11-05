from abc import ABC, abstractmethod
from typing import Dict, List, Any, Tuple
from app.tools.strapi import StrapiClient
import logging
import requests
import math

logger = logging.getLogger(__name__)

ErrorType = Dict[str, Any]
class BaseValidator(ABC):
    @property
    @abstractmethod
    def key(self) -> str:
        pass

    @abstractmethod
    def validate_completion(self, context: Any) -> Tuple[bool, List[ErrorType]]:
        pass
class ChannelValidator(BaseValidator):
    @property
    def key(self) -> str:
        return "channel"

    def validate_completion(self, funnel_flow_channels: List[Any]) -> Tuple[bool, List[ErrorType]]:
        errors = []

        if not funnel_flow_channels:
            errors.append({"message": "No channels found for this funnel flow.", "code": "CHA_01"})
            return False, errors

        if not isinstance(funnel_flow_channels, list) or len(funnel_flow_channels) == 0:
            errors.append({"message": "Channels data is empty or invalid format.", "code": "CHA_02"})

        return len(errors) == 0, errors

class AdsStructureValidator(BaseValidator):
    @property
    def key(self) -> str:
        return "ads_structure"

    def validate_completion(self, ad_sets_data: List[Dict]) -> Tuple[bool, List[ErrorType]]:
        errors = []

        if not ad_sets_data:
            return False, [{"message": "No Ad Sets found.", "code": "ADS_STRUCT_01"}]

        for adset in ad_sets_data:
            ads = adset.get("ads", [])
            if not isinstance(ads, list) or len(ads) == 0:
                errors.append({
                    "message": f"Ad Set '{adset.get('name')}' has no ads created.",
                    "code": "ADS_STRUCT_02",
                    "metadata": {
                        "ad_set_name": adset.get('name')
                    }
                })

        return len(errors) == 0, errors

class AudiencesValidator(BaseValidator):
    @property
    def key(self) -> str:
        return "audiences"

    def validate_completion(self, ad_sets_data: List[Dict]) -> Tuple[bool, List[ErrorType]]:
        errors = []

        if not ad_sets_data:
            return False, [{"message": "No Ad Sets to validate audiences.", "code": "AUD_01"}]

        for adset in ad_sets_data:
            audiences = adset.get("audiences", [])
            ad_set_name = adset.get('name')

            if not audiences:
                errors.append({
                    "message": f"Ad Set '{ad_set_name}' has no proposal audiences neither preferred audiences.",
                    "code": "AUD_02",
                    "metadata": {
                        "ad_set_name": ad_set_name
                    }
                })
                continue

            has_preferred = False
            for aud in audiences:
                preferred_data = aud.get("preferred_audience", {})
                if preferred_data and preferred_data.get("preferred") == 1:
                    has_preferred = True
                    break

            if not has_preferred:
                errors.append({
                    "message": f"Ad Set '{ad_set_name}' is missing a Preferred Audience.",
                    "code": "AUD_03",
                    "metadata": {
                        "ad_set_name": ad_set_name
                    }
                })

        return len(errors) == 0, errors

class ExperimentsValidator(BaseValidator):
    @property
    def key(self) -> str:
        return "ads_experiment"

    def validate_completion(self, ad_sets_data: List[Dict]) -> Tuple[bool, List[ErrorType]]:
        errors = []

        if not ad_sets_data:
            return False, [{"message": "No Ad Sets to validate experiments.", "code": "EXP_01"}]

        for adset in ad_sets_data:
            experiments = adset.get("experiments", [])
            ad_set_name = adset.get('name')

            if not experiments:
                errors.append({
                    "message": f"Ad Set '{ad_set_name}' has no experiments.",
                    "code": "EXP_02",
                    "metadata": {
                        "ad_set_name": ad_set_name
                    }
                })
                continue

            valid_exp = False
            for exp in experiments:
                if exp:
                    valid_exp = True
                    break

            if not valid_exp:
                errors.append({
                    "message": f"Ad Set '{ad_set_name}' has empty experiment data.",
                    "code": "EXP_03",
                    "metadata": {
                        "ad_set_name": ad_set_name
                    }
                })

        return len(errors) == 0, errors

class AdsContentValidator(BaseValidator):
    @property
    def key(self) -> str:
        return "ads"
    
    def _get_max_length_allowed(self, original_payload_length):
        max = original_payload_length + min(math.ceil(original_payload_length * 0.2), 10)
        return max

    def validate_completion(self, ad_sets_data: List[Dict]) -> Tuple[bool, List[ErrorType]]:
        errors = []

        if not ad_sets_data:
            return False, [{"message": "No Ad Sets to validate ads.", "code": "ADS_01"}]
        
        audiences_validator = AudiencesValidator()
        is_valid, _ = audiences_validator.validate_completion(ad_sets_data)
        if not is_valid:
            errors.append({
                "message": f"Audiences is not completed.",
                "code": "ADS_02",
                "metadata": {}
            })

        for adset in ad_sets_data:
            ads = adset.get("ads", [])
            ad_set_name = adset.get('name')
            media_platform_project_id = adset.get('media_platform_project_id')

            if not media_platform_project_id:
                errors.append({
                    "message": f"Ad Set '{ad_set_name}' is missing Media Platform Project ID.",
                    "code": "ADS_09",
                    "metadata": {
                        "ad_set_name": adset.get('name')
                    }
                })
                continue

            if not ads:
                errors.append({
                    "message": f"Ad Set '{ad_set_name}' has no ads.",
                    "code": "ADS_03",
                    "metadata": {"ad_set_name": ad_set_name}
                })
                continue

            for ad in ads:
                attributes = ad.get("attributes", {})
                ad_name = attributes.get("name", "Unknown Ad")
                ad_channels = attributes.get("ad_channels", [])

                if not attributes.get("url"):
                    errors.append({
                        "message": f"Ad '{ad_name}' missing redirect url",
                        "code": "ADS_06",
                        "metadata": {
                            "ad_name": ad_name
                        }
                    })

                if not ad_channels:
                    errors.append({
                        "message": f"Ad '{ad_name}' in '{ad_set_name}' has no Variants configured.",
                        "code": f"ADS_04",
                        "metadata": {
                            "ad_set_name": ad_set_name,
                            "ad_name": ad_name
                        }
                    })
                    continue

                channel = next((ch for ch in ad_channels if ch.get("selected")), None)
                if not channel:
                    errors.append({
                        "message": f"Ad '{ad_name}' in '{ad_set_name}' has no Variant selected.",
                        "code": f"ADS_04_01",
                        "metadata": {
                            "ad_set_name": ad_set_name,
                            "ad_name": ad_name
                        }
                    })
                    continue

                #for channel in ad_channels:
                media_data = channel.get("media", {})
                channel_attrs = channel.get("channel_attributes")
                channel_name = channel.get("channel_name", "Unknown Channel")

                if not isinstance(channel_attrs, list) or len(channel_attrs) == 0:
                    errors.append({
                        "message": f"Ad '{ad_name}' missing attributes in channel '{channel_name}'.",
                        "code": "ADS_05",
                        "metadata": {
                            "ad_name": ad_name,
                            "channel_name": channel_name
                        }
                    })

                payload_error_found = False

                for channel_attr in channel_attrs:
                    payloads = channel_attr.get("payloads", [])
                    for payload in payloads:
                        if payload.get("payload", "") == "":
                            payload_error_found = True
                            break
                        elif channel_attr.get('name', '').lower() != 'cta':
                            payload_length = len(payload.get("payload", ""))
                            if payload_length > channel_attr.get('max_char', 255):
                                errors.append({
                                    "message": f"Ad '{ad_name}' has a payload that exceeds the maximum allowed length in channel attributes, in channel '{channel_name}'.",
                                    "code": f"ADS_05_02",
                                    "metadata": {
                                        "ad_name": ad_name,
                                        "channel_name": channel_name,
                                        "payload_length": payload_length,
                                        "max_allowed_length": channel_attr.get('max_char', 255),
                                        "attribute_name": channel_attr.get("name", "Unknown Attribute")
                                    }
                                })

                    if payload_error_found:
                        break

                if payload_error_found:
                    errors.append({
                        "message": f"Ad '{ad_name}' missing at least one payload in channel '{channel_name}'.",
                        "code": "ADS_05_01",
                        "metadata": {
                            "ad_name": ad_name,
                            "channel_name": channel_name
                        }
                    })

                # if not channel.get("url"):
                #     errors.append({
                #         "message": f"Ad '{ad_name}' missing redirect url in channel '{channel_name}'.",
                #         "code": "ADS_06",
                #         "metadata": {
                #             "ad_name": ad_name,
                #             "channel_name": channel_name
                #         }
                #     })

                for key in ["elements", "images_banner", "formats"]:
                    val = media_data.get(key)
                    if not isinstance(val, list) or len(val) == 0:
                        errors.append({
                            "message": f"Ad '{ad_name}' missing media '{key}' in channel '{channel_name}'.",
                            "code": f"ADS_07",
                            "metadata": {
                                "ad_name": ad_name,
                                "media_element": key,
                                "channel_name": channel_name
                            }
                        })
                        continue

                    if key == "formats":
                        formats = media_data[key]
                        # Validar que exista un y solo un formato con el atributo pinned == true
                        pinned_formats = []
                        for format in formats:
                            visual_id = format.get('visual_id')
                            visual_url = format.get('visual_url')
                            pinned = format.get('pinned', False)
                            if pinned:
                                pinned_formats.append(format.get('id', ''))
                            
                            if visual_id == "":
                                errors.append({
                                    "message": f"Ad '{ad_name}' visual id not found in media '{key}', in channel '{channel_name}'.",
                                    "code": f"ADS_07_01",
                                    "metadata": {
                                        "ad_name": ad_name,
                                        "media_element": key,
                                        "channel_name": channel_name
                                    }
                                })

                            if visual_url == "":
                                errors.append({
                                    "message": f"Ad '{ad_name}' image link not found in media '{key}', in channel '{channel_name}'.",
                                    "code": f"ADS_07_02",
                                    "metadata": {
                                        "ad_name": ad_name,
                                        "media_element": key,
                                        "channel_name": channel_name
                                    }
                                })

                        if len(pinned_formats) != 1:
                            errors.append({
                                "message": f"Ad '{ad_name}' exactly one pinned format is required in media '{key}', in channel '{channel_name}'.",
                                "code": f"ADS_07_03",
                                "metadata": {
                                    "ad_name": ad_name,
                                    "media_element": key,
                                    "channel_name": channel_name
                                }
                            })

                    if key == "elements":
                        elements = media_data[key]
                        for element in elements:
                            if element.get('original_payload') and len(element.get('original_payload', "")) > 0:
                                original_payload_length = len(element.get('original_payload', ""))
                                max = self._get_max_length_allowed(original_payload_length)

                            if element.get('payload'):
                                payload_length = len(element.get('payload', ""))
                                if payload_length > max:
                                    errors.append({
                                        "message": f"Ad '{ad_name}' has a payload that exceeds the maximum allowed length in media '{key}', in channel '{channel_name}'.",
                                        "code": f"ADS_08_02",
                                        "metadata": {
                                            "ad_name": ad_name,
                                            # "media_element": key,
                                            "channel_name": channel_name,
                                            "payload_length": payload_length,
                                            "max_allowed_length": max,
                                            "element_name": element.get('name')
                                        }
                                    })

                            intention = element.get('intention')

                            if intention is None:
                                errors.append({
                                    "message": f"Ad '{ad_name}' intention not found in media '{key}', in channel '{channel_name}'.",
                                    "code": f"ADS_08_01",
                                    "metadata": {
                                        "ad_name": ad_name,
                                        "media_element": key,
                                        "channel_name": channel_name
                                    }
                                })
                                break

        return len(errors) == 0, errors

class SummaryContentValidator(BaseValidator):
    @property
    def key(self) -> str:
        return "summary"
    def validate_completion(self, ad_sets_data: List[Dict]) -> Tuple[bool, List[ErrorType]]:
        errors = []

        ads_channel_validator = ChannelValidator()
        is_valid, _ = ads_channel_validator.validate_completion(ad_sets_data)
        if not is_valid:
            errors.append({
                "message": f"Ad Channel is not completed.",
                "code": "SUM_01",
                "metadata": {}
            })

        ads_structure_validator = AdsStructureValidator()
        is_valid, _ = ads_structure_validator.validate_completion(ad_sets_data)
        if not is_valid:
            errors.append({
                "message": f"Ads Structure is not completed.",
                "code": "SUM_02",
                "metadata": {}
            })

        audiences_validator = AudiencesValidator()
        is_valid, _ = audiences_validator.validate_completion(ad_sets_data)
        if not is_valid:
            errors.append({
                "message": f"Audiences is not completed.",
                "code": "SUM_03",
                "metadata": {}
            })

        experiments_validator = ExperimentsValidator()
        is_valid, _ = experiments_validator.validate_completion(ad_sets_data)
        if not is_valid:
            errors.append({
                "message": f"Ads Experiment is not completed.",
                "code": "SUM_04",
                "metadata": {}
            })

        ads_validator = AdsContentValidator()
        is_valid, _ = ads_validator.validate_completion(ad_sets_data)
        if not is_valid:
            errors.append({
                "message": f"Ads is not completed.",
                "code": "SUM_05",
                "metadata": {}
            })

        return len(errors) == 0, errors

class ReviewContentValidator(BaseValidator):
    @property
    def key(self) -> str:
        return "review"
    def validate_completion(self, ad_sets_data: List[Dict]) -> Tuple[bool, List[ErrorType]]:
        errors = []

        ads_channel_validator = ChannelValidator()
        is_valid, _ = ads_channel_validator.validate_completion(ad_sets_data)
        if not is_valid:
            errors.append({
                "message": f"Ad Channel is not completed.",
                "code": "REV_01",
                "metadata": {}
            })

        ads_structure_validator = AdsStructureValidator()
        is_valid, _ = ads_structure_validator.validate_completion(ad_sets_data)
        if not is_valid:
            errors.append({
                "message": f"Ads Structure is not completed.",
                "code": "REV_02",
                "metadata": {}
            })

        audiences_validator = AudiencesValidator()
        is_valid, _ = audiences_validator.validate_completion(ad_sets_data)
        if not is_valid:
            errors.append({
                "message": f"Audiences is not completed.",
                "code": "REV_03",
                "metadata": {}
            })

        experiments_validator = ExperimentsValidator()
        is_valid, _ = experiments_validator.validate_completion(ad_sets_data)
        if not is_valid:
            errors.append({
                "message": f"Ads Experiment is not completed.",
                "code": "REV_04",
                "metadata": {}
            })

        ads_validator = AdsContentValidator()
        is_valid, _ = ads_validator.validate_completion(ad_sets_data)
        if not is_valid:
            errors.append({
                "message": f"Ads is not completed.",
                "code": "REV_05",
                "metadata": {}
            })

        return len(errors) == 0, errors

class LaunchPadContentValidator(BaseValidator):
    @property
    def key(self) -> str:
        return "launchpad"
    def validate_completion(self, ad_sets_data: List[Dict]) -> Tuple[bool, List[ErrorType]]:
        errors = []

        ads_channel_validator = ChannelValidator()
        is_valid, _ = ads_channel_validator.validate_completion(ad_sets_data)
        if not is_valid:
            errors.append({
                "message": f"Ad Channel is not completed.",
                "code": "LAUNCH_01",
                "metadata": {}
            })

        ads_structure_validator = AdsStructureValidator()
        is_valid, _ = ads_structure_validator.validate_completion(ad_sets_data)
        if not is_valid:
            errors.append({
                "message": f"Ads Structure is not completed.",
                "code": "LAUNCH_02",
                "metadata": {}
            })

        audiences_validator = AudiencesValidator()
        is_valid, _ = audiences_validator.validate_completion(ad_sets_data)
        if not is_valid:
            errors.append({
                "message": f"Audiences is not completed.",
                "code": "LAUNCH_03",
                "metadata": {}
            })

        experiments_validator = ExperimentsValidator()
        is_valid, _ = experiments_validator.validate_completion(ad_sets_data)
        if not is_valid:
            errors.append({
                "message": f"Ads Experiment is not completed.",
                "code": "LAUNCH_04",
                "metadata": {}
            })

        ads_validator = AdsContentValidator()
        is_valid, _ = ads_validator.validate_completion(ad_sets_data)
        if not is_valid:
            errors.append({
                "message": f"Ads is not completed.",
                "code": "LAUNCH_05",
                "metadata": {}
            })

        return len(errors) == 0, errors

class FunnelFlowValidatorUseCase:
    def __init__(self, campaign_id: str):
        self.strapi_service = StrapiClient()
        self.campaign_id = campaign_id

        self._state_map = {
            "channel": {"completed": False, "errors": [], "message": "Pending validation"},
            "ads_structure": {"completed": False, "errors": [], "message": "Pending validation"},
            "audiences": {"completed": False, "errors": [], "message": "Pending validation"},
            "ads_experiment": {"completed": False, "errors": [], "message": "Pending validation"},
            "ads": {"completed": False, "errors": [], "message": "Pending validation"},
            "summary": {"completed": False, "errors": [], "message": "Pending validation"},
            "review": {"completed": False, "errors": [], "message": "Pending validation"},
            "launchpad": {"completed": False, "errors": [], "message": "Pending validation"}
        }

        self.validators: List[BaseValidator] = [
            ChannelValidator(),
            AdsStructureValidator(),
            AudiencesValidator(),
            ExperimentsValidator(),
            AdsContentValidator(),
            SummaryContentValidator(),
            ReviewContentValidator(),
            LaunchPadContentValidator()
        ]

    def _fetch_bulk(self, endpoint, params):
        return self.strapi_service.get(endpoint, params=params).get('data', [])

    def execute(self):
        logger.info(f"Starting FunnelFlowValidatorUseCase for campaign_id: {self.campaign_id}")
        # A. Funnel Flows
        try:
            funnel_flows = self.strapi_service.find_by_filters("funnel-flows", filters={"campaign_ref": self.campaign_id})
            funnel_flows_data = funnel_flows.get('data', [])
            funnel_flow_ids = [f['id'] for f in funnel_flows_data]
            logger.info(f"Fetched {len(funnel_flow_ids)} funnel flows: {funnel_flow_ids}")
        except Exception as e:
            logger.error(f"Error fetching funnel flows: {str(e)}")
            raise

        if not funnel_flow_ids:
             logger.warning(f"No funnel flows found for campaign_id: {self.campaign_id}")
             return {'ok': 1, 'data': self._build_response([])}, 200

        # B. Channels
        try:
            channels_res = self.strapi_service.find_by_filters("funnel-flow-channels", filters={"funnel_flow_ref": funnel_flow_ids})
            channels_data = channels_res.get('data', [])
            logger.info(f"Fetched {len(channels_data)} channels")
        except Exception as e:
            logger.error(f"Error fetching channels: {str(e)}")
            raise

        # C. AdSets
        try:
            params_adsets = {
                f"filters[funnel_flow_ref][id][$in][{i}]": fid for i, fid in enumerate(funnel_flow_ids)
            }
            params_adsets["populate"] = "ads,media_platform_project_id"
            adsets_res = self.strapi_service.get("ad-sets", params=params_adsets)
            adsets_data = adsets_res.get('data', [])
            adset_ids = [ad['id'] for ad in adsets_data]
            logger.info(f"Fetched {len(adset_ids)} adsets: {adset_ids}")
        except Exception as e:
            logger.error(f"Error fetching adsets: {str(e)}")
            raise

        all_ad_ids = []
        for adset in adsets_data:
            ads_in_set = adset.get('attributes', {}).get('ads', {}).get('data', [])
            for ad in ads_in_set:
                all_ad_ids.append(ad['id'])
        logger.info(f"Identified {len(all_ad_ids)} total ads")

        # D. Fetch Relations (Audiencias, Experimentos, AdChannels)
        try:
            # D.1 Audiencias
            params_aud = {f"filters[ad_set_ref][id][$in][{i}]": aid for i, aid in enumerate(adset_ids)}
            params_aud["populate"] = "channel_ref,ad_set_ref"
            raw_audiences = self._fetch_bulk("audience-audiences", params_aud) if adset_ids else []
            logger.info(f"Fetched {len(raw_audiences)} audiences")

            # D.2 Experimentos
            params_exp = {f"filters[ad_set_ref][id][$in][{i}]": aid for i, aid in enumerate(adset_ids)}
            params_exp["populate"] = "ad_set_ref,subcategory_ref.category_ref"
            raw_experiments = self._fetch_bulk("experiment-experiments", params_exp) if adset_ids else []
            logger.info(f"Fetched {len(raw_experiments)} experiments")

            # D.3 Ad Channels
            raw_ad_channels = []
            if all_ad_ids:
                params_ad_chan = {f"filters[ad_ref][id][$in][{i}]": adid for i, adid in enumerate(all_ad_ids)}
                params_ad_chan["populate"] = "channel_ref,ad_ref"
                params_ad_chan["pagination[pageSize]"] = 1000  # Adjust page size as needed 
                raw_ad_channels = self._fetch_bulk("ad-channels", params_ad_chan)
            logger.info(f"Fetched {len(raw_ad_channels)} ad channels")
        except Exception as e:
            logger.error(f"Error fetching relations (audiences/experiments/ad_channels): {str(e)}")
            raise

        # Map: AdSet ID -> Audiencias Procesadas
        audiences_map = {aid: [] for aid in adset_ids}
        for aud in raw_audiences:
            try:
                parent_id = aud.get('attributes', {}).get('ad_set_ref', {}).get('data', {}).get('id')
                if parent_id in audiences_map:
                    attr = aud.get('attributes', {})
                    ch_ref = attr.get('channel_ref', {}).get('data', {}) or {}
                    audiences_map[parent_id].append({
                        "channel_id": ch_ref.get('id'),
                        "channel_name": ch_ref.get('attributes', {}).get('name'),
                        "generation_method": attr.get('generation_method'),
                        "preferred_audience": attr.get('preferred_audience'),
                        "proposal_audiences": attr.get('proposal_audiences')
                    })
            except Exception as e:
                logger.error(f"Error processing audience {aud.get('id')}: {str(e)}")

        # Map: AdSet ID -> Experimentos
        experiments_map = {aid: [] for aid in adset_ids}
        for exp in raw_experiments:
            try:
                parent_id = exp.get('attributes', {}).get('ad_set_ref', {}).get('data', {}).get('id')
                if parent_id in experiments_map:
                    attr = exp.get('attributes', {})
                    subcategory = attr.get('subcategory_ref', {}).get('data') or {}
                    category = subcategory.get("attributes", {}).get("category_ref", {}).get("data") or {}
                    experiments_map[parent_id].append({
                        'id': exp.get('id'),
                        'type': attr.get('type'),
                        'subcategory': {
                            'id': subcategory.get('id'),
                            'name': subcategory.get("attributes", {}).get('name'),
                            "description": subcategory.get("attributes", {}).get("description"),
                            "category": {
                                "id": category.get("id"),
                                "name": category.get("attributes", {}).get("name"),
                                "description": category.get("attributes", {}).get("description")
                            }
                        }
                    })
            except Exception as e:
                logger.error(f"Error processing experiment {exp.get('id')}: {str(e)}")

        # Map: Ad ID -> Ad Channels Procesados
        ad_channels_map = {adid: [] for adid in all_ad_ids}
        for chan in raw_ad_channels:
            try:
                parent_ad_id = chan.get('attributes', {}).get('ad_ref', {}).get('data', {}).get('id')
                if parent_ad_id in ad_channels_map:
                    attr = chan.get('attributes', {})
                    ch_ref = attr.get('channel_ref', {}).get('data', {}) or {}
                    ad_channels_map[parent_ad_id].append({
                        'channel_id': ch_ref.get('id'),
                        'channel_name': ch_ref.get('attributes', {}).get('name'),
                        'media': {
                            'template_id': attr.get('media_template_id'),
                            'elements': attr.get('media_elements'),
                            'images_banner': attr.get('media_images_banner'),
                            'formats': attr.get('media_formats'),
                        },
                        'channel_attributes': attr.get('channel_attributes'),
                        'url': attr.get('redirect_url'),
                        'selected': attr.get('selected', False)
                    })
            except Exception as e:
                logger.error(f"Error processing ad channel {chan.get('id')}: {str(e)}")

        final_structure = []

        for adset in adsets_data:
            adset_id = adset.get('id')
            media_platform_project_data = adset.get('attributes', {}).get('media_platform_project_id', {}).get('data')
            media_platform_project_id = media_platform_project_data.get('attributes', {}).get('project_id') if media_platform_project_data else None

            ads_list = []
            raw_ads = adset.get('attributes', {}).get('ads', {}).get('data', [])

            for ad in raw_ads:
                ad_id = ad.get('id')
                ads_list.append({
                    "id": ad_id,
                    "attributes": {
                        "name": ad.get('attributes', {}).get('name'),
                        "ad_channels": ad_channels_map.get(ad_id, []),
                        "url": ad.get('attributes', {}).get('redirect_url')
                    }
                })

            final_structure.append({
                "id": adset_id,
                "name": adset.get('attributes', {}).get('name'),
                "media_platform_project_id": media_platform_project_id,
                "ads": ads_list,
                "audiences": audiences_map.get(adset_id, []),
                "experiments": experiments_map.get(adset_id, [])
            })

        self._run_validator("channel", channels_data)

        self._run_validator("ads_structure", final_structure)
        self._run_validator("audiences", final_structure)
        self._run_validator("ads_experiment", final_structure)
        self._run_validator("ads", final_structure)
        self._run_validator("summary", final_structure)
        self._run_validator("review", final_structure)
        self._run_validator("launchpad", final_structure)

        logger.info(f"Validator execution completed successfully for campaign_id: {self.campaign_id}")

        return {
            'ok': 1,
            "data": self._build_response(final_structure)
        }, 200

    def _run_validator(self, key: str, context: Any):
        validator = next((v for v in self.validators if v.key == key), None)

        if validator:
            is_valid, errors = validator.validate_completion(context)

            self._state_map[key] = {
                "completed": is_valid,
                "errors": errors
            }
        else:
            self._state_map[key] = {
                "completed": False,
                "errors": [{"message": "Validator implementation missing", "code": "SYS_ERR"}]
            }

    def _build_response(self, funnel_data):
        state_list = []
        for key, value in self._state_map.items():
            item = {"step": key}
            item.update(value)
            if "completed" not in item: item["completed"] = False
            if "errors" not in item: item["errors"] = []
            state_list.append(item)

        return {
            "state": state_list,
            "funnel_flow_data": funnel_data
        }
