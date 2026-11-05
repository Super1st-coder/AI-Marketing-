# Bugfix Requirements Document

## Introduction

La refactorización manual de la rama STANDARD del pre-check de Meta Ads (commits `175d429`, `efd4051`, `ac2797b` de HL-2496) modificó el contrato observable de `FacebookGeneratePreCheckCreativeUseCase` y de `FacebookSavePreCheckBaseUseCase` sin que las pruebas unitarias existentes fueran actualizadas. Como consecuencia, 44 pruebas unitarias fallan contra un código productivo que se considera correcto.

El defecto está **en las pruebas, no en el código productivo**. Las pruebas codifican suposiciones obsoletas sobre el valor de `ok`, la forma del objeto `call_to_action`, la firma de `_build_standard_creative_entry` y la tolerancia a valores desconocidos de `meta_campaign_mode`. Mientras persistan, la suite no puede usarse como red de seguridad: oculta 44 señales rojas permanentes que impiden distinguir una regresión nueva de un desalineamiento conocido.

Estado verificado ejecutando `venv/bin/python -m pytest` sobre los tres archivos afectados desde el directorio `sinergia/`:

```
44 failed, 283 passed, 12 warnings in 91.22s
```

Sobre la suite completa el estado reportado es `44 failed, 1632 passed`.

Archivos afectados (únicos artefactos que este bugfix modifica):

- `sinergia/tests/v2/unit/use_cases/test_facebook_generate_pre_check_creative.py` (34 fallos)
- `sinergia/tests/v2/unit/use_cases/test_facebook_save_pre_check_images.py` (5 fallos)
- `sinergia/tests/v2/unit/use_cases/test_facebook_save_pre_check_texts.py` (5 fallos)

Decisiones de alcance confirmadas con el usuario antes de redactar este documento:

- **`"ok": 1` fijo es el comportamiento intencional.** El retorno `{"ok": 1, # if has_errors else 1, ...}` de `execute()` se acepta como fuente de verdad; las pruebas que esperaban `ok=0` deben adaptarse y renombrarse.
- **La conversión estricta `CreativeType(meta_campaign_mode)` es el comportamiento intencional.** Un `meta_campaign_mode` ausente, vacío o desconocido representa un estado de datos corrupto y debe fallar con `ValueError`; las pruebas que documentaban tolerancia deben adaptarse para esperar la excepción.

## Bug Analysis

### Formalización de la condición de bug

La función bajo prueba no es el código productivo, sino la propia suite. Se define:

- **F**: la suite de pruebas en su estado actual (previo al arreglo).
- **F'**: la suite de pruebas después del realineamiento.
- **X**: un caso de prueba individual (nodo de pytest, incluida su parametrización).

```pascal
FUNCTION isBugCondition(X)
  INPUT: X of type PytestNodeId
  OUTPUT: boolean

  // X pertenece a uno de los tres archivos objetivo Y
  // X codifica al menos una suposicion obsoleta sobre el
  // contrato refactorizado de meta_ads.py
  RETURN X.file IN TARGET_TEST_FILES
         AND (
              expectsOkZero(X)                    // Grupo A - 23 casos
           OR buildsFlatCallToActionType(X)       // Grupo B -  8 casos
           OR passesAdCreativeAsThirdArgument(X)  // Grupo C -  3 casos
           OR assumesUnknownModeTolerance(X)      // Grupo D - 10 casos
         )
END FUNCTION
```

```pascal
// Property: Fix Checking
FOR ALL X WHERE isBugCondition(X) DO
  result <- runTest(F', X)
  ASSERT result.outcome = PASSED
  ASSERT productionSourceUnchanged() = TRUE
END FOR
```

```pascal
// Property: Preservation Checking
FOR ALL X WHERE NOT isBugCondition(X) DO
  ASSERT runTest(F, X).outcome = runTest(F', X).outcome
END FOR
```

Las cuatro sub-condiciones del Grupo A–D se corresponden con las cláusulas 1.1/1.2, 1.3/1.4, 1.5/1.6 y 1.7/1.8 respectivamente.

### Current Behavior (Defect)

Los 44 casos se agrupan en cuatro causas raíz, cada una trazada al cambio productivo que la originó.

**Grupo A — `execute()` devuelve `ok=1` incondicionalmente (23 casos).** El commit `175d429` sustituyó `"ok": 0 if has_errors else 1` por `"ok": 1, # if has_errors else 1` en `FacebookGeneratePreCheckCreativeUseCase.execute()`. La variable `has_errors` se sigue calculando pero ya no influye en la respuesta.

1.1 WHEN se ejecutan los 18 casos de `TestExecuteMissingCreative` y `TestExecuteDynamicBranch` que aseveran `result["ok"] == 0` tras provocar un fallo de validación o un `adCreative` ausente THEN la suite falla con `AssertionError: assert 1 == 0`.

1.2 WHEN se ejecutan los 5 casos de `TestExecuteCreationBlock`, `TestExecuteAggregationAndStatus` y `TestExecuteCombinedScenarios` que aseveran `result["ok"] == 0` tras forzar entradas con `status == "Failed"` en el bloque de creación THEN la suite falla con `AssertionError: assert 1 == 0`, pese a que el `status_code == 200` aseverado en el mismo caso sí se cumple.

**Grupo B — `call_to_action.type` pasó a ser un objeto anidado (8 casos).** `_validate_standard_cta` obtiene el texto del CTA mediante `cta.get('type', {}).get('value')`. La forma canónica que produce el resto del sistema es `link_data['call_to_action'] = {'type': {'value': <str>, 'valid': <bool>}}`, tal como la escribe `FacebookSavePreCheckCTAsUseCase._validate_ctas_standard`. Las pruebas construyen la forma plana previa, `{'type': <str>}`.

1.3 WHEN se ejecutan los 4 casos de `TestStandardCtaValidation` y `TestStandardAnnotationContract` que invocan `_validate_standard_cta` con un `call_to_action` cuyo `type` es una cadena THEN la suite falla con `AttributeError: 'str' object has no attribute 'get'` lanzado desde `meta_ads.py` al evaluar `cta.get('type', {}).get('value')`.

1.4 WHEN se ejecutan los 4 casos parametrizados de `TestStandardCombinationSuccessScenarios::test_full_success_scenario_yields_ok_1_and_all_seven_success_annotations_true` (`awareness-reach`, `leads-conversations`, `leads-lead-generation`, `sales-offsite-conversions`), que recorren `execute()` completo con un `call_to_action` de `type` plano THEN la suite falla con `AttributeError: 'str' object has no attribute 'get'` antes de poder evaluar cualquiera de las siete anotaciones de éxito.

**Grupo C — `_build_standard_creative_entry` cambió de firma y de composición de `name` (3 casos).** El tercer parámetro pasó de `ad_creative` a `ad`, y el método ahora desciende él mismo con `ad.get('adCreative')`. Además `name` pasó a ser `f"{ad_set_to_publish.get('name')} - {ad.get('name')}"`. Al recibir un `ad_creative`, la expresión `ad.get('adCreative')` devuelve `None`, se sustituye por `{}` y todo el resultado degenera silenciosamente a los valores por defecto.

1.5 WHEN se ejecuta `TestStandardCreativesEntry::test_object_story_spec_completely_absent_uses_every_documented_default` pasando `ad_creative` como tercer argumento THEN la suite falla con `AssertionError` sobre la comparación completa del diccionario, porque `ad_id` resulta `None` en lugar de `"ad-absent-oss"` y `name` no incorpora el sufijo `" - {ad.name}"`.

1.6 WHEN se ejecutan los 2 casos `TestExecuteStandardAdChannelIdReading::test_build_standard_creative_entry_distinguishes_explicit_none_from_absent_key` con los identificadores `explicit-none` y `positive-integer` THEN la suite falla con `assert 0 == None` y `assert 0 == 42` respectivamente, porque `object_story_spec` nunca se alcanza y `adchannel_id` cae al valor por defecto `0`.

**Grupo D — `_set_creative_type` convierte el modo de campaña de forma estricta (10 casos).** El commit `efd4051` añadió a `FacebookSavePreCheckBaseUseCase` el método nuevo `_set_creative_type`, que ejecuta `CreativeType(campaign_setup.get('attributes', {}).get('meta_campaign_mode')).value` antes del bloque de validación. Cualquier valor fuera de `{"STANDARD", "DYNAMIC"}` aborta `execute()` con `ValueError`.

1.7 WHEN se ejecutan los 8 casos de `TestUnknownMetaCampaignMode` de `test_facebook_save_pre_check_images.py` y `test_facebook_save_pre_check_texts.py` con `meta_campaign_mode` igual a cadena vacía, `None`, un valor arbitrario o con la clave ausente THEN la suite falla con `ValueError: None is not a valid CreativeType`, `ValueError: '' is not a valid CreativeType` o `ValueError: 'SOME_OTHER_MODE' is not a valid CreativeType`, en lugar de observar el no-op sin mutación que los casos aseveran.

1.8 WHEN se ejecutan los 2 casos de orden de operaciones `TestExecuteOrchestration::test_execute_calls_operations_in_exact_order` y `TestExecuteOrchestrationAndShortCircuit::test_execute_calls_operations_in_exact_order`, que usan `make_campaign_setup(meta_campaign_mode=None)` únicamente como atajo para neutralizar la rama de validación sin parchear `MetaAdsValidator` THEN la suite falla con `ValueError: None is not a valid CreativeType` antes de registrar las llamadas a `_save_creative_to_publish` y `_build_response` en el mock manager.

### Expected Behavior (Correct)

Las cláusulas 2.1 a 2.8 se corresponden una a una con las cláusulas 1.1 a 1.8. Las cláusulas 2.9 a 2.13 son transversales.

2.1 WHEN se ejecutan los 18 casos de `TestExecuteMissingCreative` y `TestExecuteDynamicBranch` referidos en 1.1 THEN la suite de pruebas SHALL aseverar `result["ok"] == 1` y SHALL pasar, preservando intactas todas las demás aserciones de cada caso sobre anotaciones presentes, ausentes o removidas del creativo.

2.2 WHEN se ejecutan los 5 casos de `TestExecuteCreationBlock`, `TestExecuteAggregationAndStatus` y `TestExecuteCombinedScenarios` referidos en 1.2 THEN la suite de pruebas SHALL aseverar `result["ok"] == 1` junto con `status_code == 200` y SHALL pasar, preservando las aserciones sobre la composición y el reindexado de `data["creatives"]`.

2.3 WHEN se ejecutan los 4 casos de `TestStandardCtaValidation` y `TestStandardAnnotationContract` referidos en 1.3 THEN la suite de pruebas SHALL construir el `call_to_action` con la forma anidada `{'type': {'value': <cta_text>}}`, SHALL aseverar que la anotación de validez se escribe en `call_to_action['valid']` y SHALL pasar.

2.4 WHEN se ejecutan los 4 casos parametrizados de `TestStandardCombinationSuccessScenarios` referidos en 1.4 THEN la suite de pruebas SHALL construir el `call_to_action` con la forma anidada incluyendo `{'type': {'value': <cta_text>, 'valid': True}}`, SHALL leer la anotación `call_to_action_types_valid_amount` desde `call_to_action['type']['valid']` conforme a `_build_standard_creative_entry`, y SHALL pasar aseverando `ok == 1` y las siete anotaciones de éxito en `True`.

2.5 WHEN se ejecuta `TestStandardCreativesEntry::test_object_story_spec_completely_absent_uses_every_documented_default` THEN la suite de pruebas SHALL invocar `_build_standard_creative_entry(idx, ad_set_to_publish, ad)` pasando el diccionario del *ad* completo como tercer argumento, SHALL esperar `name` igual a `f"{ad_set_to_publish['name']} - {ad['name']}"` y SHALL pasar la comparación completa del diccionario de valores por defecto.

2.6 WHEN se ejecutan los 2 casos `TestExecuteStandardAdChannelIdReading` referidos en 1.6 THEN la suite de pruebas SHALL pasar el diccionario del *ad* como tercer argumento y SHALL aseverar `adchannel_id` igual a `None` para `explicit-none`, `0` para `absent-key` y `42` para `positive-integer`.

2.7 WHEN se ejecutan los 8 casos de `TestUnknownMetaCampaignMode` referidos en 1.7 THEN la suite de pruebas SHALL aseverar mediante `pytest.raises(ValueError)` que `execute()` propaga la excepción de conversión de `CreativeType`, SHALL aseverar que ningún validador de `MetaAdsValidator` fue invocado y que ni `asset_feed_spec` ni `object_story_spec` fueron mutados, y SHALL aseverar que `ad_channel_repository.update` y `_build_response` no fueron invocados.

2.8 WHEN se ejecutan los 2 casos de orden de operaciones referidos en 1.8 THEN la suite de pruebas SHALL usar un `meta_campaign_mode` válido para que `_set_creative_type` tenga éxito, SHALL neutralizar la rama de validación por un medio distinto al modo inválido, y SHALL pasar aseverando la secuencia exacta `_get_decoded_access_token`, `_get_ad_channel`, `_set_channel_id`, `_get_campaign_setup`, bloque de validación, `_save_creative_to_publish`, `_build_response` sobre `manager.mock_calls`.

2.9 IF el nombre de un caso de prueba o de una clase contradice el comportamiento aseverado tras el realineamiento THEN la suite de pruebas SHALL renombrarlo para reflejar el comportamiento real, de modo que ningún identificador que contenga `yields_ok_zero` o `ok_zero` aseveré `ok == 1`, ni ninguna clase llamada `TestUnknownMetaCampaignMode` describa tolerancia.

2.10 The suite de pruebas SHALL actualizar el docstring de cada caso modificado para describir el contrato vigente, incluidas las copias literales de código productivo embebidas en docstrings que hayan quedado desfasadas respecto de `_save_creative_to_publish` y `_build_standard_creative_entry`.

2.11 The suite de pruebas SHALL alcanzar `0 failed` al ejecutarse sobre los tres archivos objetivo desde el directorio `sinergia/` con el intérprete de `venv/`, y `1676 passed` al ejecutarse sobre la suite completa.

2.12 The archivo `sinergia/app/v2/use_cases/meta_ads.py` y todo archivo bajo `sinergia/app/` SHALL permanecer sin modificaciones, verificable mediante `git diff --stat -- app/`.

2.13 WHILE se adaptan las pruebas, IF una aserción obsoleta resulta imposible de realinear sin cambiar el código productivo THEN la suite de pruebas SHALL NOT eliminar ni marcar como `xfail` o `skip` el caso afectado, y el hallazgo SHALL ser escalado al usuario como una ambigüedad de alcance no resuelta.

### Unchanged Behavior (Regression Prevention)

3.1 WHEN se ejecuta la suite completa THEN los 1632 casos que actualmente pasan SHALL CONTINUE TO pasar, sin que ninguno cambie a `failed`, `error`, `skipped` o `xfail`.

3.2 WHEN se ejecutan los tres archivos objetivo THEN los 283 casos que actualmente pasan dentro de esos mismos archivos SHALL CONTINUE TO pasar sin modificación de sus aserciones.

3.3 WHEN se ejecuta cualquier caso de prueba de la rama DYNAMIC de `FacebookGeneratePreCheckCreativeUseCase`, `FacebookSavePreCheckImagesUseCase` o `FacebookSavePreCheckTextsUseCase` THEN la suite SHALL CONTINUE TO aseverar el contrato basado en `asset_feed_spec` sin ninguna adaptación derivada de este bugfix.

3.4 WHEN se modifica una función auxiliar o *fixture* compartida (`make_object_story_spec`, `make_ad_set`, `make_campaign_setup`, `make_creative`, `make_ad_channel`, `use_case_factory`, `patch_redis_client`, el centinela `ABSENT`) THEN todos los casos que ya la consumían y pasaban SHALL CONTINUE TO pasar con la misma semántica de valores por defecto.

3.5 WHEN se ejecuta cualquier caso adaptado THEN `AdChannelRepository` y `CampaignChannelPublishRepository` SHALL CONTINUE TO estar sustituidos por dobles de prueba parcheados en `app.v2.use_cases.meta_ads`, y `redis_client` junto con toda llamada HTTP a la Graph API SHALL CONTINUE TO estar parcheados, de modo que ninguna prueba realice acceso real a Strapi, a Redis ni a la red.

3.6 WHERE un caso de prueba verifica el número de instanciaciones de repositorios o la identidad por referencia del objeto `creative` que fluye hacia `_save_creative_to_publish` y `_build_response`, THEN esas aserciones SHALL CONTINUE TO cumplirse sin cambios.

3.7 WHEN se ejecutan los casos de `TestStandardCombinationSuccessScenarios` sobre las cuatro combinaciones soportadas de `_STANDARD_SUPPORTED_COMBINATIONS` THEN la suite SHALL CONTINUE TO cubrir exactamente esas cuatro parametrizaciones (`awareness-reach`, `leads-conversations`, `leads-lead-generation`, `sales-offsite-conversions`), sin añadir ni quitar combinaciones.

3.8 WHEN se ejecuta la suite completa tras el arreglo THEN el tiempo de ejecución de los tres archivos objetivo SHALL CONTINUE TO mantenerse en el orden de magnitud actual (aproximadamente 90 segundos), sin introducir esperas reales, reintentos ni entrada/salida de red.
