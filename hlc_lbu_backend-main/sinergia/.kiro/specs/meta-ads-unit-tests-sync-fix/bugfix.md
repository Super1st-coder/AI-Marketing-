# Documento de Requisitos del Bugfix

## Introduction

Dos cambios manuales en el código de producción `sinergia/app/v2/use_cases/meta_ads.py` (ticket HL-2671) modificaron el contrato observable de dos casos de uso, pero las suites unitarias no se actualizaron. Resultado: 16 tests fallan (2875 pasan).

El código de producción es la fuente de verdad y NO se modifica. El defecto está en los tests, que todavía afirman el contrato anterior, y en los nombres de algunos tests, que lo siguen describiendo.

Cambios de producción que definen el nuevo contrato:

- Commit `99a93414` (`FacebookGetLaunchCampaignCreativesUseCase`): el bloque `campaign` del Resultado_de_Consulta incorpora una séptima clave, `'conversion_event'`, con el valor de `setup_attributes.get('meta_conversion_event')`, situada después de `'mode'`. El orden queda: `name`, `channel_name`, `creatives_no`, `objective`, `optimization_goal`, `mode`, `conversion_event`. Por tanto, el Campaign_Setup también se consulta por el atributo `meta_conversion_event`.
- Commit `7ef9a47d` (`FacebookLaunchCampaignUseCase._build_leads_offsite_tracking_specs`): en la Combinación_Leads_Offsite (`OUTCOME_LEADS` + `OFFSITE_CONVERSIONS`), el `tracking_specs` del Payload_Ad cambia de `[{"action.type": ["offsite_conversion"], "dataset": [pixel_id]}]` a `[{"action.type": ["offsite_conversion"], "fb_pixel": [pixel_id]}]`.

Suites afectadas:
- `sinergia/tests/v2/unit/use_cases/test_facebook_get_launch_campaign_creatives.py` (13 tests: `TestResultComposition`, `TestCampaignBlock`, `TestMetaUrl`)
- `sinergia/tests/v2/unit/use_cases/test_facebook_launch_campaign.py` (3 tests: `TestLeadsOffsiteAdPayload`, `TestLeadsOffsiteLaunchRollback`)

## Bug Analysis

### Current Behavior (Defect)

1.1 CUANDO la suite `test_facebook_get_launch_campaign_creatives.py` compara el bloque `campaign` contra el diccionario esperado (`_expected_campaign_block`) ENTONCES la aserción falla porque el diccionario esperado solo contiene seis claves y el resultado real incluye además `'conversion_event'` (con valor `None` en los fixtures canónicos). Afecta a `TestResultComposition::test_campaign_block_equals_the_six_keys_derived_from_the_fixtures`, `TestResultComposition::test_campaign_block_reflects_the_values_of_a_non_canonical_fixture`, `TestCampaignBlock::test_campaign_block_equals_the_six_keys_derived_from_the_fixtures`, `TestCampaignBlock::test_the_block_is_the_same_in_both_modes_except_for_the_mode_key[DYNAMIC|STANDARD]`, `TestCampaignBlock::test_creatives_no_follows_the_size_of_the_fixture[one-creative|two-creatives|four-creatives]`, `TestCampaignBlock::test_name_is_the_name_attribute_of_the_resolved_campaign` y `TestCampaignBlock::test_the_three_remaining_keys_come_from_the_campaign_setup`.

1.2 CUANDO un test compara la tupla de claves del bloque `campaign` contra la constante `CAMPAIGN_BLOCK_KEYS` ENTONCES la aserción falla porque la constante declara seis claves y el resultado real tiene siete, con `'conversion_event'` al final (`TestResultComposition::test_absent_setup_attributes_yield_none_in_the_three_keys`).

1.3 CUANDO `TestResultComposition::test_meta_resources_is_never_read` compara el conjunto de atributos consultados del Campaign_Setup durante `_build_result` contra el conjunto esperado de cinco atributos ENTONCES la aserción falla porque la composición también consulta `'meta_conversion_event'`.

1.4 CUANDO `TestMetaUrl::test_meta_resources_is_never_read_end_to_end` compara los atributos consultados en todo el flujo `execute()` contra `SETUP_ATTRIBUTES_READ_END_TO_END` (seis atributos) ENTONCES la aserción falla porque el flujo también consulta `'meta_conversion_event'`.

1.5 CUANDO `TestLeadsOffsiteAdPayload::test_tracking_specs_only_for_leads_offsite` (property-based, Hypothesis) publica un ad en la Combinación_Leads_Offsite ENTONCES la aserción falla porque espera `[{"action.type": ["offsite_conversion"], "dataset": [pixel]}]` y el payload real contiene `[{"action.type": ["offsite_conversion"], "fb_pixel": [pixel]}]` (contraejemplo mínimo: `pixel='0'`).

1.6 CUANDO `TestLeadsOffsiteLaunchRollback::test_happy_path_publishes_website_adset_and_tracked_ads[DYNAMIC|STANDARD]` verifica el `tracking_specs` de los ads publicados ENTONCES la aserción falla porque espera la clave `"dataset"` con `["pixel-123"]` y el payload real usa la clave `"fb_pixel"` con `["pixel-123"]`.

1.7 CUANDO se leen los identificadores de pytest de `test_facebook_get_launch_campaign_creatives.py` ENTONCES cuatro nombres de test describen el contrato anterior ("six keys", "three keys", "three remaining keys"), aunque el bloque tenga siete claves y cuatro de ellas provengan del Campaign_Setup.

### Expected Behavior (Correct)

2.1 CUANDO la suite compara el bloque `campaign` contra el diccionario esperado ENTONCES el diccionario esperado DEBERÁ contener exactamente las siete claves del nuevo contrato, en el orden `name`, `channel_name`, `creatives_no`, `objective`, `optimization_goal`, `mode`, `conversion_event`. El valor esperado de `conversion_event` DEBERÁ ser el `meta_conversion_event` del Campaign_Setup del fixture, o `None` si el fixture no declara ese atributo (caso de los fixtures canónicos). Así, los tests enumerados en 1.1 pasan sin cambiar su intención.

2.2 CUANDO un test compara la tupla de claves del bloque `campaign` contra `CAMPAIGN_BLOCK_KEYS` ENTONCES la constante DEBERÁ declarar las siete claves en el orden de 2.1. Además, CUANDO el Campaign_Setup no tiene nodo `attributes`, el test DEBERÁ afirmar que `objective`, `optimization_goal`, `mode` y `conversion_event` valen `None`.

2.3 CUANDO `TestResultComposition::test_meta_resources_is_never_read` evalúa los atributos consultados durante `_build_result` ENTONCES el conjunto esperado DEBERÁ ser exactamente `{'meta_campaign_objective', 'meta_optimization_goal', 'meta_campaign_mode', 'meta_conversion_event', 'meta_account_id', 'meta_campaign_id'}`. El test DEBERÁ seguir afirmando que `'meta_resources'` no se consulta.

2.4 CUANDO `TestMetaUrl::test_meta_resources_is_never_read_end_to_end` evalúa los atributos consultados en todo el flujo `execute()` ENTONCES `SETUP_ATTRIBUTES_READ_END_TO_END` DEBERÁ ser exactamente `{'meta_published', 'meta_campaign_mode', 'meta_campaign_objective', 'meta_optimization_goal', 'meta_conversion_event', 'meta_account_id', 'meta_campaign_id'}`. El test DEBERÁ seguir afirmando que `'meta_resources'` no se consulta y que `meta_url` es la URL esperada.

2.5 CUANDO `TestLeadsOffsiteAdPayload::test_tracking_specs_only_for_leads_offsite` publica un ad en la Combinación_Leads_Offsite ENTONCES el test DEBERÁ esperar `tracking_specs == [{"action.type": ["offsite_conversion"], "fb_pixel": [pixel]}]` para todo `pixel` generado. Para cualquier otra combinación DEBERÁ seguir esperando que `tracking_specs` no exista.

2.6 CUANDO `TestLeadsOffsiteLaunchRollback::test_happy_path_publishes_website_adset_and_tracked_ads[DYNAMIC|STANDARD]` verifica los ads publicados ENTONCES el test DEBERÁ esperar `tracking_specs == [{"action.type": ["offsite_conversion"], "fb_pixel": ["pixel-123"]}]`, con una sola entrada y sin clave `"dataset"`.

2.7 MIENTRAS un docstring, comentario de sección (por ejemplo `# -- The ``campaign`` block of six keys`) o etiqueta `# Feature: ... Property 14` de las suites afectadas describa el contrato anterior (por ejemplo, "six keys", "three keys", "five attributes", "six attributes" o `"dataset": [pixel]`), la documentación del test DEBERÁ actualizarse para describir el nuevo contrato (siete claves, cuatro claves derivadas del Campaign_Setup, `meta_conversion_event` entre los atributos leídos, `"fb_pixel": [pixel]`). Esto incluye el docstring de `make_campaign_setup`, que enumera los atributos que lee el caso de uso.

2.8 CUANDO se ejecuten `TestResultComposition::test_campaign_block_reflects_the_values_of_a_non_canonical_fixture` y `TestCampaignBlock::test_the_four_remaining_keys_come_from_the_campaign_setup` ENTONCES cada uno DEBERÁ construir el Campaign_Setup con un `meta_conversion_event` no nulo (por ejemplo `'LEAD'`) y DEBERÁ afirmar que ese valor aparece tal cual en `campaign['conversion_event']`. El builder `make_campaign_setup` ya acepta ese atributo mediante `**attribute_overrides`, así que no necesita parámetros nuevos.

2.9 CUANDO se ejecute la suite `test_facebook_get_launch_campaign_creatives.py` ENTONCES los tests cuyo nombre describe el contrato anterior DEBERÁN renombrarse así, manteniendo el estilo de nombres existente:
- `TestResultComposition::test_campaign_block_equals_the_six_keys_derived_from_the_fixtures` → `TestResultComposition::test_campaign_block_equals_the_seven_keys_derived_from_the_fixtures`
- `TestResultComposition::test_absent_setup_attributes_yield_none_in_the_three_keys` → `TestResultComposition::test_absent_setup_attributes_yield_none_in_the_four_keys`
- `TestCampaignBlock::test_campaign_block_equals_the_six_keys_derived_from_the_fixtures` → `TestCampaignBlock::test_campaign_block_equals_the_seven_keys_derived_from_the_fixtures`
- `TestCampaignBlock::test_the_three_remaining_keys_come_from_the_campaign_setup` → `TestCampaignBlock::test_the_four_remaining_keys_come_from_the_campaign_setup`

En `test_facebook_launch_campaign.py` ningún nombre de test, clase ni id de `parametrize` describe la clave `"dataset"`, así que esa suite no tiene renombrados.

2.10 CUANDO `TestSuiteSelfAudit` recorra los casos de la suite ENTONCES los tests renombrados DEBERÁN conservar en su docstring la línea `Requirements: ...` con los mismos criterios que declaraban antes. La auditoría descubre los casos por AST y por los criterios de su docstring, sin enumerar nombres de test por cadena, así que no hay que actualizar ninguna lista de nombres.

### Unchanged Behavior (Regression Prevention)

3.1 El sistema DEBERÁ MANTENER sin modificaciones el código de producción bajo `sinergia/app/v2/` (en particular `sinergia/app/v2/use_cases/meta_ads.py`, repositorios y recursos). El fix solo toca archivos bajo `sinergia/tests/v2/unit/use_cases/`.

3.2 CUANDO se ejecute la suite unitaria completa con `venv/bin/python -m pytest` desde `sinergia/` ENTONCES el sistema DEBERÁ CONTINUAR haciendo pasar los 2875 tests que hoy pasan. Los 16 tests enumerados en 1.1–1.6 (con los nombres nuevos de 2.9 donde aplique) también DEBERÁN pasar, con 0 fallos en total y el mismo número total de tests (2891).

3.3 CUANDO los tests verifiquen que `'meta_resources'` no se lee ENTONCES el sistema DEBERÁ CONTINUAR afirmando que `'meta_resources'` está presente en el fixture y que no aparece entre los atributos consultados.

3.4 CUANDO los tests verifiquen el bloque `campaign` ENTONCES el sistema DEBERÁ CONTINUAR comparando por igualdad exacta de diccionario y de orden de claves (no por inclusión parcial). También DEBERÁ CONTINUAR verificando que `channel_name == 'Meta'`, que `creatives_no` sigue el tamaño del fixture, que `name` proviene de la campaña resuelta y que `objective`, `optimization_goal` y `mode` provienen del Campaign_Setup.

3.5 CUANDO la combinación de objetivo y optimización NO sea la Combinación_Leads_Offsite ENTONCES el sistema DEBERÁ CONTINUAR afirmando que el Payload_Ad no contiene `tracking_specs` y que `name`, `adset_id`, `creative`, `status` y `access_token` se conservan.

3.6 CUANDO se ejecute `TestLeadsOffsiteAdPayload::test_tracking_specs_only_for_leads_offsite` ENTONCES el sistema DEBERÁ CONTINUAR usando Hypothesis con la configuración actual (`max_examples=100`, `deadline=None`, `suppress_health_check=[HealthCheck.function_scoped_fixture]`) y la misma estrategia de generación.

3.7 CUANDO se ejecuten los tests de `TestLeadsOffsiteLaunchRollback` ENTONCES el sistema DEBERÁ CONTINUAR verificando la publicación del adset con destino website, el orden de llamadas y el rollback ante fallos.

3.8 CUANDO se ejecuten los tests unitarios ENTONCES el sistema DEBERÁ CONTINUAR sin tráfico de red saliente (`deny_network` activo) y con las mismas auditorías de `TestSuiteSelfAudit` y `TestBuildersIndependence`, que DEBERÁN seguir pasando.

3.9 CUANDO el nombre de un test de las suites afectadas siga describiendo con exactitud el nuevo contrato (por ejemplo `test_the_block_is_the_same_in_both_modes_except_for_the_mode_key`, `test_meta_resources_is_never_read`, `test_tracking_specs_only_for_leads_offsite` o `test_happy_path_publishes_website_adset_and_tracked_ads`) ENTONCES el sistema DEBERÁ CONTINUAR usando su identificador de pytest actual, incluidos los ids de `parametrize` (`DYNAMIC`, `STANDARD`, `one-creative`, `two-creatives`, `four-creatives`).

3.10 CUANDO un test se renombre según 2.9 ENTONCES el sistema DEBERÁ CONTINUAR conservando su clase, sus fixtures, su intención y sus aserciones, salvo las que actualicen 2.1, 2.2 y 2.8. Ningún otro archivo del repositorio (otras specs en `sinergia/.kiro/specs/`, `conftest.py`, configuración de CI o `Makefile`) referencia esos nombres por cadena, así que el renombrado no exige cambios fuera de la suite.
