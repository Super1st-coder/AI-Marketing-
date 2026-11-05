# Implementation Plan: Meta Ads Leads Offsite Conversions

## Overview

Implementación incremental en Python (Flask, `sinergia/`) de la combinación `OUTCOME_LEADS` + `OFFSITE_CONVERSIONS` en PreCheck, Save PreCheck y Launch, más la corrección global de la anotación del CTA STANDARD (Req 15). El orden sigue el flujo de datos: constantes del validador → helpers y estado de `meta_ads.py` → recurso `external.py` → catálogo → PreCheck → corrección CTA STANDARD → cobertura Save PreCheck → Launch → regresión.

Todas las pruebas viven en `sinergia/tests/v2/unit/use_cases/` y usan `pytest`, `pytest-mock` e `hypothesis` del virtualenv `sinergia/venv`. Cada prueba de propiedad usa `@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])` y el comentario `# Feature: meta-ads-leads-offsite-conversions, Property <n>: <texto>`. Comando (desde `sinergia/`): `venv/bin/python -m pytest tests/v2/unit/use_cases/ -q`.

## Tasks

- [x] 1. Constantes de soporte en el Servicio_Validador
  - [x] 1.1 Agregar constantes en `app/v2/use_cases/facebook_validator_service.py`
    - Agregar el miembro `OFFSITE_CONVERSIONS = "OFFSITE_CONVERSIONS"` a `LeadsOptimizationGoal`
    - Agregar la entrada `LeadsOptimizationGoal.OFFSITE_CONVERSIONS.value` con los 20 CTAs_Leads_Offsite en `LEADS_GOAL_ALLOWED_CTAS`, sin tocar las entradas existentes
    - Definir `LEADS_ALLOWED_CONVERSION_EVENTS: Set[str]` con los 7 eventos
    - Agregar `"SEE_MENU"` y `"SEE_DETAILS"` a `MetaAdsValidator.VALID_CTA_VALUES`
    - No modificar `SALES_GOAL_ALLOWED_CTAS`, `AWARENESS_GOAL_ALLOWED_CTAS`, `SALES_ALLOWED_CUSTOM_EVENTS`, `META_ODAX_CTA_MAPPING` ni `validate_promoted_object`
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.8, 1.9_

  - [x] 1.2 Escribir prueba de propiedad de validación de CTA Leads_Offsite
    - Archivo nuevo `test_facebook_validator_leads_offsite_conversions.py`, clase `TestLeadsOffsiteCtaValidation`
    - Generador `cta_variants(cta)` (mayúsculas/minúsculas, padding, `_`↔` `), strings arbitrarios, blancos y `None`; verificar retorno con `throw=False` y mensajes de `ValueError` con `throw=True`
    - **Property 1: Validación de CTA para Combinación_Leads_Offsite**
    - **Validates: Requirements 1.5, 1.6, 1.7**

  - [x] 1.3 Escribir pruebas unitarias de constantes
    - Clase `TestLeadsOffsiteConstants` en `test_facebook_validator_leads_offsite_conversions.py`
    - Enum con exactamente 4 miembros y valores; 7 eventos exactos; 20 CTAs exactos y entradas previas intactas; CTAs ⊂ `VALID_CTA_VALUES`; `validate_optimization_goal_for_objective` con `throw=True/False`; regresión `("OFFSITE_CONVERSIONS", "OUTCOME_AWARENESS")` → `False`
    - Parametrizar los 20 CTAs como válidos y `CALL_NOW` / `WHATSAPP_MESSAGE` como inválidos
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.8, 1.9, 14.7_

- [x] 2. Helpers de módulo y estado de construcción en `meta_ads.py`
  - [x] 2.1 Implementar helpers, `CampaignDataDict` y lectura en `FacebookTestCreativeUploadUseCase.__init__`
    - Importar `LEADS_ALLOWED_CONVERSION_EVENTS` desde el Servicio_Validador
    - Funciones de módulo `_is_leads_offsite(objective, optimization_goal)`, `_normalize_conversion_event(value)` (`strip().upper()` o `None`, nunca lanza) y `_is_blank(value)`
    - Agregar `conversion_event: Optional[str]` a `CampaignDataDict`
    - En `__init__`, asignar `self.conversion_event = _normalize_conversion_event(complete_campaign_data.get('conversion_event') if complete_campaign_data else None)` con la misma guarda que `pixel_id`, sin alterar el `AttributeError` previo con `complete_campaign_data=None`
    - _Requirements: 3.4, 3.5, 3.6, 3.7_

  - [x] 2.2 Escribir prueba de propiedad de normalización de Conversion_Event
    - Clase `TestLeadsOffsiteConversionEventNormalization` en `test_facebook_generate_pre_check_creative.py`
    - Generador `raw_conversion_events()` × pares (objective, optimization_goal) arbitrarios
    - **Property 2: Normalización de Conversion_Event en la construcción**
    - **Validates: Requirements 3.5, 3.6, 3.7**

  - [x] 2.3 Escribir pruebas unitarias de `CampaignDataDict` y construcción
    - Verificar `CampaignDataDict.__annotations__['conversion_event']`, el ejemplo `"  lead "` → `"LEAD"` y que la caracterización `complete_campaign_data=None` → `AttributeError` se mantiene
    - _Requirements: 3.4, 3.5, 3.6_

- [x] 3. Recepción de `conversion_event` en el Recurso_PreCheck
  - [x] 3.1 Actualizar `app/v2/resources/external.py`
    - Agregar `'conversion_event': fields.String()` (opcional) a `GeneratePreCheckCampaignLaunchStruct`, junto a `pixel_id`
    - En `FacebookResourceCampaignLaunchPreCheckGenerate.post`, asignar `complete_campaign_data['conversion_event'] = payload.get('conversion_event')` sin transformar; no tocar las demás claves
    - Verificación por revisión (Req 14.1 limita las pruebas a `use_cases/`)
    - _Requirements: 3.1, 3.2, 3.3, 13.5_

- [x] 4. Catálogo de objetivos (Caso_Objetivos)
  - [x] 4.1 Agregar `OFFSITE_CONVERSIONS` a `FacebookGetCampaignObjectiveUseCase`
    - Agregar `{'id': LeadsOptimizationGoal.OFFSITE_CONVERSIONS.value, 'billing_event': 'IMPRESSIONS'}` al final de `leads['goals']`
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

  - [x] 4.2 Escribir pruebas unitarias del catálogo
    - Archivo nuevo `test_facebook_get_campaign_objective.py`, clase `TestCampaignObjectiveCatalog`
    - Catálogo literal previo + elemento nuevo en índice 2; 4 objetivos en orden; `OUTCOME_LEADS` activo sin `QUALITY_LEAD`; `requests` y `redis_client` parcheados para fallar si se invocan; mismo resultado para distintos `user_id`
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 13.6, 14.13_

- [x] 5. Checkpoint - Asegurar que todas las pruebas pasan
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Soporte de Combinación_Leads_Offsite en el PreCheck (`FacebookGeneratePreCheckCreativeUseCase`)
  - [x] 6.1 Actualizar el default de `make_campaign_data_dict` en `test_facebook_generate_pre_check_creative.py`
    - Agregar `"conversion_event": "LEAD"` al dict por defecto (decisión aprobada en el design); es inerte para Otras_Combinaciones y evita `META013` en las pruebas existentes que derivan de `_STANDARD_SUPPORTED_COMBINATIONS`
    - _Requirements: 13.3, 13.4_

  - [x] 6.2 Implementar `_STANDARD_SUPPORTED_COMBINATIONS` y `_validate_leads_offsite_params`
    - Agregar la tupla `(OUTCOME_LEADS, OFFSITE_CONVERSIONS)` a `_STANDARD_SUPPORTED_COMBINATIONS` sin tocar la guarda `META011`
    - Implementar `_validate_leads_offsite_params()` con `META012` → `META013` → `META014` (mensaje con valor normalizado y los 7 eventos ordenados)
    - Invocarlo dentro del bloque `if self.objective == CampaignObjective.LEADS.value:` de `execute()`, tras las guardas de `LEAD_GENERATION`/`CONVERSATIONS` y antes de `META002`/`META011`, el bucle y `_save_campaign_channel_publish`
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 5.1, 5.2, 5.4, 5.5, 9.6_

  - [x] 6.3 Escribir prueba de propiedad de validaciones obligatorias
    - Clase `TestLeadsOffsiteMandatoryParams`; generadores `pixel_ids()` × `raw_conversion_events()` × rama (`DYNAMIC`, `STANDARD`) contra el modelo de referencia `expected(pixel, event)`
    - Verificar que con excepción no se invocan `save_or_update`, `ad_channel_repository.update` ni `validate_images_precheck`
    - **Property 3: Validaciones obligatorias del PreCheck como modelo de referencia**
    - **Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 8.5, 9.6**

  - [x] 6.4 Escribir prueba de propiedad de `conversion_event` inerte
    - Clase `TestLeadsOffsiteOtherCombinationsIgnoreEvent`; Otras_Combinaciones soportadas por rama × `conversion_event` arbitrario
    - Sin `META012`–`META014`, sin `meta_conversion_event` en `save_or_update` y respuesta/persistencia iguales a la ejecución sin `conversion_event`
    - **Property 4: `conversion_event` es inerte para Otras_Combinaciones**
    - **Validates: Requirements 4.7, 9.3, 13.4**

  - [x] 6.5 Escribir pruebas unitarias parametrizadas de parámetros obligatorios
    - En `TestLeadsOffsiteMandatoryParams`: `pixel_id`/`conversion_event` omitido, `None` y `""` × DYNAMIC/STANDARD (`META012`, `META013`), sin `save_or_update` ni `requests.get`
    - Aceptación de los 7 eventos y de `"  lead "` (persistido como `"LEAD"`); rechazo `META014` de `PURCHASE` y `FOO`
    - `_STANDARD_SUPPORTED_COMBINATIONS` con exactamente 5 tuplas; Combinación_Leads_Offsite STANDARD sin `META011`/`META002`
    - En `TestLeadsOffsiteOtherCombinationsIgnoreEvent`: Otras_Combinaciones con `conversion_event` no permitido en DYNAMIC y STANDARD
    - _Requirements: 4.1, 4.2, 4.3, 4.5, 4.6, 5.1, 5.2, 14.5, 14.6, 14.14_

  - [x] 6.6 Implementar `_validate_leads_offsite_dynamic_url` e insertarlo en el bucle DYNAMIC
    - Normalizar `website_url = None` a `''`, unir solo URLs no vacías, `url-error` por URL ausente o formato inválido, asignar `link_url_valid`
    - Envolver el bloque `try` de URL actual en el `else` de `if _is_leads_offsite(...)`, sin cambiarlo para Otras_Combinaciones
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6_

  - [x] 6.7 Escribir prueba de propiedad de URL DYNAMIC Leads_Offsite
    - Clase `TestLeadsOffsiteDynamicUrl`; generador `link_urls_lists()` invocando el helper directamente
    - **Property 5: URL DYNAMIC de Combinación_Leads_Offsite**
    - **Validates: Requirements 7.1, 7.2, 7.3**

  - [x] 6.8 Escribir prueba de propiedad de URL DYNAMIC en Otras_Combinaciones
    - Clase `TestLeadsOffsiteDynamicUrl`; combinaciones DYNAMIC distintas × `link_urls` con `website_url` string
    - **Property 6: Otras_Combinaciones DYNAMIC nunca registran `url-error`**
    - **Validates: Requirements 7.6**

  - [x] 6.9 Escribir pruebas unitarias de URL DYNAMIC con `execute()`
    - Ejecución con 2 ads (uno con URL ausente y otro con URL inválida): `proposal_url_valid = False`, `url-error` en `results` con `status = Failed`, demás anotaciones intactas; caso Otras_Combinaciones con URL ausente sin `url-error`
    - _Requirements: 7.4, 14.8_

  - [x] 6.10 Implementar post-proceso de `promoted_object_valid` y persistencia de `meta_conversion_event`
    - En el bucle que renumera `idx`, asignar `item['promoted_object_valid'] = True` solo si `_is_leads_offsite(...)`
    - En la construcción de `campaign_channel_publish`, agregar `meta_conversion_event = self.conversion_event` solo si `_is_leads_offsite(...)`, sin tocar las demás claves
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.6, 9.1, 9.2, 9.3, 9.4, 9.5_

  - [x] 6.11 Escribir prueba de propiedad de CTAs DYNAMIC
    - Clase `TestLeadsOffsiteDynamicCtas`; listas de CTAs con `value` permitido, no permitido, ausente, `None` o vacío
    - **Property 7: Anotación de CTAs DYNAMIC en el PreCheck**
    - **Validates: Requirements 6.1, 6.2**

  - [x] 6.12 Escribir prueba de propiedad de invariantes de la Respuesta_PreCheck
    - Clase `TestLeadsOffsitePreCheckSuccess`; 1–3 ad sets con 1–3 ads (STANDARD) o 1 ad (DYNAMIC) con validez por-ad mixta; `validate_promoted_object` como espía nunca invocado
    - Depende de 7.6: guarda de CTA no-dict (contraejemplo encontrado: un ad set STANDARD con 2 ads, el segundo con `call_to_action='LEARN_MORE'`, hacía lanzar `AttributeError` a `execute()`)
    - **Property 8: Invariantes de la Respuesta_PreCheck exitosa**
    - **Validates: Requirements 5.3, 6.7, 8.1, 8.2, 8.3, 8.4**

  - [x] 6.13 Escribir prueba de propiedad de persistencia en Campaign_Setup
    - Clase `TestLeadsOffsitePersistence`; `pixel_id` no blanco × variantes de eventos permitidos × patrón de ads fallidos; `get_billing_event` mockeado a `"IMPRESSIONS"`
    - **Property 9: Persistencia en Campaign_Setup para Combinación_Leads_Offsite**
    - **Validates: Requirements 9.1, 9.2, 9.5**

  - [x] 6.14 Escribir pruebas unitarias de casos felices del PreCheck
    - Caso feliz DYNAMIC y STANDARD: `valid_ctas` == CTAs_Leads_Offsite, `promoted_object_valid is True`, `meta_pixel_id` y `meta_conversion_event` normalizado en `save_or_update`; claves preexistentes de Campaign_Setup intactas
    - _Requirements: 5.3, 6.7, 8.1, 8.2, 9.1, 9.2, 9.4, 14.4_

- [x] 7. Corrección global de `_validate_standard_cta` (Requirement 15)
  - [x] 7.1 Reescribir `_validate_standard_cta` en `meta_ads.py`
    - Escribir el mismo booleano en `call_to_action['type']['valid']` y en `call_to_action['valid']`; normalizar `type` ausente/no-dict a `{'value': <original o None>, 'valid': False}` sin invocar `validate_cta_for_goal`; exactamente un `cta-error` cuando es `False`
    - Conservar los argumentos con nombre de `validate_cta_for_goal(cta_text=..., objective=..., goal=..., throw=False)` y los casos falsy / no-dict sin cambios
    - No modificar `_build_standard_creative_entry`, `_is_campaign_valid` ni `_validate_ctas_standard` (excepción: la guarda de `call_to_action` no-dict en `_build_standard_creative_entry` y constructores STANDARD análogos se aplica en 7.6, Req 15.8)
    - _Requirements: 6.3, 6.4, 6.5, 6.6, 13.7, 15.1, 15.2, 15.3, 15.4, 15.5, 15.6, 15.7, 15.8, 15.9, 15.10_

  - [x] 7.2 Actualizar los 4 docstrings de herencia de `type.valid` en `test_facebook_generate_pre_check_creative.py`
    - Solo texto, sin tocar aserciones: `make_standard_link_data_full`, `make_standard_cta`, docstring de clase de `TestStandardCtaValidation` y `TestStandardCombinationSuccessScenarios.test_full_success_scenario_yields_ok_1_and_all_seven_success_annotations_true`
    - Describir que el método escribe el mismo booleano en `type.valid` y en la raíz (Req 15)
    - _Requirements: 13.8_

  - [x] 7.3 Escribir prueba de propiedad de anotación corregida del CTA STANDARD
    - Clase `TestStandardCtaAnnotationFix`; generador `standard_cta_shapes(combo)` sobre las 5 combinaciones de `_STANDARD_SUPPORTED_COMBINATIONS`
    - **Property 10: Anotación corregida del CTA STANDARD (global)**
    - **Validates: Requirements 6.3, 6.4, 15.1, 15.2, 15.3, 15.6**

  - [x] 7.4 Escribir prueba de propiedad de `call_to_action_types_valid_amount`
    - Clase `TestStandardCtaAnnotationFix`; `execute()` STANDARD con CTA permitido o no × `type.valid` de entrada ausente/`True`/`False`
    - **Property 11: `call_to_action_types_valid_amount` refleja la validación real**
    - **Validates: Requirements 15.7, 13.7**

  - [x] 7.5 Escribir pruebas unitarias parametrizadas del Requirement 15
    - Por cada una de las 5 combinaciones, con un CTA permitido y otro no permitido según `get_allowed_ctas_for_goal`: no permitido con `type.valid=True` → `False` + un `cta-error` + `call_to_action_types_valid_amount False`; permitido sin `valid` → `True`; raíz == `type.valid`
    - `call_to_action` sin `type` y con `type = "LEARN_MORE"` → normalización del criterio 15.3 sin excepción
    - _Requirements: 14.16, 14.17, 14.18, 14.19, 14.20, 15.3_

  - [x] 7.6 Agregar guarda de `call_to_action` no-dict en `_build_standard_creative_entry` y constructores STANDARD análogos
    - Aplicar `if not isinstance(call_to_action, dict): call_to_action = {}` antes de leer `type` en `_build_standard_creative_entry` (~líneas 1596/1601 de `meta_ads.py`) y en los constructores análogos de `meta_ads.py` que usan `call_to_action.get('type', ...)` (~2667/2672 y ~3721/3726)
    - Ningún otro cambio en esos constructores
    - Agregar pruebas unitarias parametrizadas en `tests/v2/unit/use_cases/test_facebook_generate_pre_check_creative.py` para `call_to_action` en `'LEARN_MORE'`, `1`, `['SIGN_UP']` × combinaciones (incluidas Combinación_Leads_Offsite y al menos una Otra_Combinación): `execute()` sin excepción, exactamente un `cta-error` para el ad, `call_to_action_types == []` y `call_to_action_types_valid_amount is False`
    - _Requirements: 5.3, 6.5, 8.2, 15.5, 15.8, 15.11_

- [x] 8. Checkpoint - Asegurar que todas las pruebas pasan
  - Ensure all tests pass, ask the user if questions arise.

- [x] 9. Cobertura de Casos_Save_PreCheck (sin cambios productivos)
  - [x] 9.1 Escribir pruebas de `FacebookSavePreCheckImagesUseCase`
    - Clase `TestLeadsOffsiteSaveImages` en `test_facebook_save_pre_check_images.py`; casos felices DYNAMIC y STANDARD con `make_campaign_setup` de Combinación_Leads_Offsite; diferencial campo por campo vs `LEAD_GENERATION`; `promoted_object_valid` persistido intacto; un caso `LEAD_GENERATION` y uno `SALES/OFFSITE_CONVERSIONS`
    - _Requirements: 10.5, 10.6, 10.7, 10.8, 14.9_

  - [x] 9.2 Escribir pruebas de `FacebookSavePreCheckTextsUseCase`
    - Clase `TestLeadsOffsiteSaveTexts` en `test_facebook_save_pre_check_texts.py`; mismo patrón que 9.1
    - _Requirements: 10.5, 10.6, 10.7, 10.8, 14.9_

  - [x] 9.3 Escribir pruebas unitarias de `FacebookSavePreCheckCTAsUseCase`
    - Clase `TestLeadsOffsiteSaveCtas` en `test_facebook_save_pre_check_ctas.py`; casos felices DYNAMIC y STANDARD; STANDARD con 0 y con más de un CTA igual que `LEAD_GENERATION`; `promoted_object_valid` intacto
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.6, 10.7, 10.8, 14.9_

  - [x] 9.4 Escribir prueba de propiedad de Save PreCheck de CTAs
    - Clase `TestLeadsOffsiteSaveCtas`; listas de CTAs de 0 a N con valores arbitrarios en DYNAMIC y un CTA en STANDARD
    - **Property 12: Save PreCheck de CTAs para Combinación_Leads_Offsite**
    - **Validates: Requirements 10.1, 10.2, 10.3, 10.6**

  - [x] 9.5 Escribir pruebas de `FacebookSavePreCheckBudgetUseCase`
    - Clase `TestLeadsOffsiteSaveBudget` en `test_facebook_save_pre_check_budget.py`; parchear `_get_account_details` y `_get_minimum_budget`; mismo patrón que 9.1
    - _Requirements: 10.5, 10.6, 10.7, 10.8, 14.9_

  - [x] 9.6 Escribir pruebas de `FacebookSavePreCheckProposalURLUseCase`
    - Clase `TestLeadsOffsiteSaveProposalUrl` en `test_facebook_save_pre_check_proposal_url.py`; mismo patrón que 9.1
    - _Requirements: 10.5, 10.6, 10.7, 10.8, 14.9_

  - [x] 9.7 Escribir pruebas de `FacebookSavePreCheckLocationsUseCase`
    - Clase `TestLeadsOffsiteSaveLocations` en `test_facebook_save_pre_check_locations.py`; mismo patrón que 9.1
    - _Requirements: 10.5, 10.6, 10.7, 10.8, 14.9_

- [x] 10. Soporte de Combinación_Leads_Offsite en el Launch (`FacebookLaunchCampaignUseCase`)
  - [x] 10.1 Agregar estado, lectura del Campaign_Setup y helpers de construcción
    - `__init__`: `self.pixel_id = None`, `self.conversion_event = None`
    - `_get_campaign_setup`: leer `meta_pixel_id` y `meta_conversion_event` de `attributes` sin transformar
    - `_build_leads_offsite_promoted_object()` (lanza `ParametersNotFoundException` por píxel blanco, evento blanco o evento fuera de `LEADS_ALLOWED_CONVERSION_EVENTS`, con comparación exacta) y `_build_leads_offsite_tracking_specs()`
    - _Requirements: 11.1, 11.3, 11.5, 11.9, 12.1_

  - [x] 10.2 Agregar la rama Leads_Offsite en `_publish_adset`
    - Dentro del bloque `OUTCOME_LEADS`, si `_is_leads_offsite(...)`: `promoted_object` desde el helper, `destination_type = "WEBSITE"`, `optimization_goal = "OFFSITE_CONVERSIONS"`, `billing_event = "IMPRESSIONS"`; en el `else`, el código actual de `page_id`/`CONVERSATIONS`/`LEAD_GENERATION` sin cambios
    - La rama `SALES` no cambia; el rollback existente de `execute()` cubre la excepción
    - _Requirements: 11.2, 11.3, 11.4, 11.5, 11.6, 11.7, 11.8, 11.9, 11.10, 11.11_

  - [x] 10.3 Escribir prueba de propiedad del Payload_AdSet
    - Clase `TestLeadsOffsiteAdsetPayload` en `test_facebook_launch_campaign.py`; `_publish_adset` real con `requests.post` y `_get_account_details` parcheados; píxel/evento blancos, inválidos o válidos × `promoted_object` ruidoso × rama
    - **Property 13: Payload_AdSet de Combinación_Leads_Offsite**
    - **Validates: Requirements 11.1, 11.2, 11.3, 11.4, 11.5, 11.7, 11.9**

  - [x] 10.4 Agregar `tracking_specs` en `_publish_ad` y la guarda en `_build_object_story_spec`
    - En `_publish_ad`, agregar `payload["tracking_specs"] = self._build_leads_offsite_tracking_specs()` solo si `_is_leads_offsite(...)`
    - En `_build_object_story_spec`, agregar `and not _is_leads_offsite(...)` a la condición que inyecta `lead_gen_form_id`
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6_

  - [x] 10.5 Escribir prueba de propiedad de `tracking_specs`
    - Clase `TestLeadsOffsiteAdPayload`; combinaciones arbitrarias × `meta_pixel_id` no blanco sobre `_publish_ad` real
    - **Property 14: `tracking_specs` en Payload_Ad solo para Combinación_Leads_Offsite**
    - **Validates: Requirements 12.1, 12.2, 12.4**

  - [x] 10.6 Escribir prueba de propiedad de los builders de creativo
    - Clase `TestLeadsOffsiteCreativeBuilders`; `lead_gen_form_id` `None` o string × `link_data` / `asset_feed_spec` arbitrarios sobre `_build_object_story_spec` y `_build_asset_feed_spec`
    - **Property 15: El creativo de Combinación_Leads_Offsite no se convierte en lead form**
    - **Validates: Requirements 12.5**

  - [x] 10.7 Escribir pruebas unitarias de casos felices y rollback del Launch
    - Clase `TestLeadsOffsiteLaunchRollback`: `launch_scenario` con `_publish_adset` real; `meta_pixel_id` y `meta_conversion_event` como `None` y `""`; `ParametersNotFoundException`, `_rollback_publish` (espía con `wraps`) una vez, `_publish_ad` no invocado
    - Casos felices DYNAMIC y STANDARD: `destination_type == "WEBSITE"`, `promoted_object` con píxel/evento del Campaign_Setup y `tracking_specs` en cada Payload_Ad (2 ads)
    - _Requirements: 11.6, 12.3, 12.6, 14.10, 14.11_

- [x] 11. Regresión y compatibilidad hacia atrás
  - [x] 11.1 Escribir pruebas de regresión de payloads del Launch
    - Clase `TestLaunchPayloadRegression` en `test_facebook_launch_campaign.py`; `LEAD_GENERATION` → `promoted_object == {"page_id": ...}` y `destination_type == "ON_AD"`; `CONVERSATIONS` → `WHATSAPP` y ajuste de `targeting`; SALES → `{"pixel_id": ..., "custom_event_type": "PURCHASE"}` sin `destination_type`; ninguno con `tracking_specs`
    - _Requirements: 11.8, 11.10, 11.11, 13.1, 13.2, 14.12_

  - [x] 11.2 Escribir pruebas de regresión del PreCheck para Otras_Combinaciones
    - En `test_facebook_generate_pre_check_creative.py`: STANDARD de otras combinaciones con `promoted_object_valid False`; DYNAMIC conserva la lógica SALES de `validate_promoted_object`; respuesta idéntica con y sin `conversion_event`
    - _Requirements: 8.6, 13.1, 13.4_

- [x] 12. Checkpoint final - Ejecutar la suite completa
  - Ejecutar desde `sinergia/`: `venv/bin/python -m pytest tests/v2/unit/use_cases/ -q`, sin red, con 0 fallos y 0 errores (incluidas las pruebas preexistentes)
  - Ensure all tests pass, ask the user if questions arise.
  - _Requirements: 13.3, 14.1, 14.2, 14.3, 14.15_

- [x] 13. Seguimiento (Requirement 16)
  - [x] 13.1 Guarda de CTA no-dict en `FacebookGetLaunchCampaignCreativesUseCase`
    - En `_build_standard_creative_published` de `meta_ads.py` (~líneas 5227/5228), agregar `if not isinstance(call_to_action, dict): call_to_action = {}` tras `call_to_action = link_data.get('call_to_action') or {}`, y `if not isinstance(call_to_action_type, dict): call_to_action_type = {}` tras `call_to_action_type = call_to_action.get('type') or {}`
    - Ningún otro cambio en el método (mismas 31 claves y valores para los casos dict)
    - Agregar pruebas unitarias parametrizadas en `tests/v2/unit/use_cases/test_facebook_get_launch_campaign_creatives.py` (clase nueva) para `call_to_action` en `'LEARN_MORE'`, `1`, `['SIGN_UP']`: sin excepción, `call_to_action_types == []` y `call_to_action_types_valid_amount is False`; y `{'type': 'LEARN_MORE'}`: `call_to_action_types == [{}]` y `call_to_action_types_valid_amount is False`
    - _Requirements: 16.1, 16.2, 16.3_

  - [x] 13.2 `proposal_url` sin `None` en `_build_dynamic_creative_entry`
    - En `FacebookGeneratePreCheckCreativeUseCase._build_dynamic_creative_entry` (~línea 1553), unir solo los `website_url` que no son `None` (conservando el default `''` para la clave ausente y los strings tal cual); no tocar el bloque de URL existente ni su slug `assets-budget-error`
    - Actualizar `TestOtherCombinationsPreCheckRegression.test_dynamic_website_url_none_keeps_assets_budget_error_slug` en `test_facebook_generate_pre_check_creative.py`: reemplazar `isinstance(outcome, TypeError)` por status 200, exactamente un `assets-budget-error`, ningún `url-error`, `link_url_valid` sin asignar y `proposal_url == ''` (sin `None`); actualizar su docstring
    - Agregar pruebas unitarias para Otras_Combinaciones DYNAMIC con `link_urls=[{"website_url": None}, {"website_url": "https://example.com/destino"}]`: `execute()` sin excepción y `proposal_url == "https://example.com/destino"`
    - _Requirements: 7.6, 13.1, 16.4, 16.5_

  - [x] 13.3 Actualizar docstrings de "4 combinaciones" a 5
    - Solo texto, sin tocar aserciones, en `test_facebook_generate_pre_check_creative.py`: docstrings de `make_standard_link_data_full` y de `TestStandardCombinationSuccessScenarios.test_full_success_scenario_yields_ok_1_and_all_seven_success_annotations_true`
    - Cambiar 4 por 5 `STANDARD_SUPPORTED_COMBINATIONS` y agregar `LEADS_GOAL_ALLOWED_CTAS[OFFSITE_CONVERSIONS]` a la lista de allow-lists que contienen `"LEARN_MORE"`
    - _Requirements: 16.6_

  - [x] 13.4 Checkpoint del seguimiento
    - Ejecutar desde `sinergia/`: `venv/bin/python -m pytest tests/v2/unit/use_cases/ -q`, sin red, con 0 fallos y 0 errores
    - Ensure all tests pass, ask the user if questions arise.
    - _Requirements: 13.3, 14.15_

## Notes

- Las sub-tareas marcadas con `*` son pruebas opcionales y se pueden omitir para un MVP más rápido; las tareas de implementación (y las actualizaciones obligatorias de pruebas existentes 6.1 y 7.2) son requeridas.
- Cada tarea referencia criterios de aceptación concretos para trazabilidad.
- Las pruebas de propiedades validan las 15 propiedades del design; las unitarias cubren ejemplos, regresiones y casos borde.
- `test_facebook_generate_pre_check_creative.py` lo modifican muchas sub-tareas; el grafo las ubica en waves distintas para evitar conflictos.
- La sección 13 es un seguimiento detectado durante la ejecución (Requirement 16); 13.1 y 13.3 tocan archivos distintos y comparten wave; 13.2 va en otra wave porque edita `meta_ads.py` (como 13.1) y `test_facebook_generate_pre_check_creative.py` (como 13.3).

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "3.1", "6.1"] },
    { "id": 1, "tasks": ["2.1", "1.2"] },
    { "id": 2, "tasks": ["4.1", "1.3", "2.2"] },
    { "id": 3, "tasks": ["6.2", "4.2", "2.3"] },
    { "id": 4, "tasks": ["6.6", "6.3"] },
    { "id": 5, "tasks": ["6.10", "6.4"] },
    { "id": 6, "tasks": ["7.1", "6.5", "9.1", "9.2", "9.3", "9.5", "9.6", "9.7"] },
    { "id": 7, "tasks": ["10.1", "6.7", "9.4"] },
    { "id": 8, "tasks": ["10.2", "6.8"] },
    { "id": 9, "tasks": ["10.4", "6.9", "10.3"] },
    { "id": 10, "tasks": ["6.11", "10.5"] },
    { "id": 11, "tasks": ["7.6"] },
    { "id": 12, "tasks": ["6.12", "10.6"] },
    { "id": 13, "tasks": ["6.13", "10.7"] },
    { "id": 14, "tasks": ["6.14", "11.1"] },
    { "id": 15, "tasks": ["7.2"] },
    { "id": 16, "tasks": ["7.3"] },
    { "id": 17, "tasks": ["7.4"] },
    { "id": 18, "tasks": ["7.5"] },
    { "id": 19, "tasks": ["11.2"] },
    { "id": 20, "tasks": ["13.1", "13.3"] },
    { "id": 21, "tasks": ["13.2"] },
    { "id": 22, "tasks": ["13.4"] }
  ]
}
```
