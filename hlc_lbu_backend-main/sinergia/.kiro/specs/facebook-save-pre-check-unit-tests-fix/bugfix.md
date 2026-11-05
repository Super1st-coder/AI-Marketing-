# Bugfix Requirements Document

## Introduction

El commit `be390b5630ea33751f7b5d9e4fd4f789109b5d79` (HL-2496, «fix campaign mode branch») sustituyó el criterio de despacho de `FacebookSavePreCheckBaseUseCase._build_response` en `sinergia/app/v2/use_cases/meta_ads.py`: donde antes se infería el modo del creativo a partir de la *forma* del `adCreative`, ahora se lee el modo *declarado* de la campaña desde `self.creative_type`.

```python
# antes de be390b56
if object_story_spec or not asset_feed_spec:
# desde be390b56 (línea 2533)
if self.creative_type == CreativeType.STANDARD.value:
```

Siete pruebas unitarias de `TestBuildResponse` invocan `_build_response` de forma **directa y aislada**, sin atravesar `execute()`. En esa ruta `_set_creative_type` nunca se ejecuta, por lo que `self.creative_type` conserva el `''` con el que lo inicializa el constructor del ancestro (`creative_type: str = ''`). Con `''` la comparación contra `CreativeType.STANDARD.value` es falsa y siempre se toma la rama `else` (extracción DYNAMIC), cuyos valores por defecto difieren de los de la rama STANDARD: `*_max_amount` vale `0` en lugar de `1`, y `adchannel_id` se lee de `asset_feed_spec` en lugar de `object_story_spec`.

El defecto está **en las pruebas, no en el código productivo**. `_build_response` tiene exactamente seis invocadores en `app/` —los `execute()` de `FacebookSavePreCheckImagesUseCase`, `FacebookSavePreCheckTextsUseCase`, `FacebookSavePreCheckCTAsUseCase`, `FacebookSavePreCheckBudgetUseCase`, `FacebookSavePreCheckProposalURLUseCase` y `FacebookSavePreCheckLocationsUseCase`— y los seis llaman `_set_creative_type(campaign_setup)` antes, método que convierte el modo de forma estricta con `CreativeType(...)` y aborta con `ValueError` ante cualquier valor distinto de `"DYNAMIC"` o `"STANDARD"`. El estado `creative_type == ''` es por tanto **inalcanzable en producción**: las siete aserciones fallidas describen un estado que sólo existe en la ruta de invocación aislada de las propias pruebas. El nuevo despacho es además estrictamente más correcto que la heurística anterior, que podía enrutar un anuncio STANDARD con `asset_feed_spec` presente hacia la extracción DYNAMIC, y viceversa.

Comportamiento verificado empíricamente sobre el código actual, invocando `_build_response` de forma aislada con `asset_feed_spec = {}`:

| `creative_type` | Rama tomada | `*_max_amount` |
|---|---|---|
| `''` (estado del constructor) | DYNAMIC (`else`) | `[0, 0, 0, 0, 0]` |
| `'DYNAMIC'` | DYNAMIC (`else`) | `[0, 0, 0, 0, 0]` |
| `'STANDARD'` | STANDARD (`if`) | `[1, 1, 1, 1, 1]` |

Estado verificado ejecutando `venv/bin/python -m pytest tests/v2/unit -q` desde el directorio `sinergia/`:

```
7 failed, 2567 passed in 53.00s
```

El alcance de referencia de este bugfix es `tests/v2/unit` (2574 casos recolectados). Ejecuciones más amplias arrastran fallos preexistentes y ajenos a este defecto que **no** forman parte del alcance: `tests/v2` añade `test_pin_format_ad_variant_integration.py::TestPinFormatAdVariantEndToEndWorkflow::test_end_to_end_pin_format_workflow_persists_pinned_state`, y la suite completa `tests/` añade fallos y errores de `tests/v1/`.

Archivos afectados (únicos artefactos que este bugfix modifica):

- `sinergia/tests/v2/unit/use_cases/test_facebook_save_pre_check_images.py` (4 fallos)
- `sinergia/tests/v2/unit/use_cases/test_facebook_save_pre_check_texts.py` (3 fallos)

Los otros dos commits señalados en la solicitud fueron inspeccionados y descartados como causa: `54ae199433e106d49b5da92e426d2a306bef15ca` introdujo `_get_meta_currency_offset` y el conjunto `_ZERO_DECIMAL_CURRENCIES` y ajustó `_get_minimum_budget`; `4c510b40496dc2ce31873e779da0b5c69ad8a32c` promovió ambos de miembros de clase a ámbito de módulo. Ninguno toca `_build_response` ni el despacho por modo, y ninguna prueba del alcance falla por ellos.

Decisión de alcance confirmada con el usuario antes de redactar este documento:

- **Los seis casos de valores por defecto se parametrizan sobre ambas ramas.** En lugar de elegir una sola rama, cada uno de los seis casos de defaults se parametriza sobre `creative_type`, aseverando los valores por defecto propios de DYNAMIC (`*_max_amount == 0`) y de STANDARD (`*_max_amount == 1`). Esto cierra además la cobertura de la rama STANDARD de `_build_response` en la suite de textos, que hoy no la ejercita.

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

  // X pertenece a TestBuildResponse de uno de los dos archivos objetivo,
  // invoca _build_response de forma directa sin atravesar execute(),
  // NO fija self.creative_type antes de la invocacion, Y asevera al menos
  // un valor que depende de la rama de extraccion seleccionada
  RETURN X.file IN TARGET_TEST_FILES
         AND X.class = 'TestBuildResponse'
         AND invokesBuildResponseDirectly(X)
         AND NOT setsCreativeTypeExplicitly(X)
         AND (
              assertsStandardMaxAmountDefaults(X)   // Grupo A - 6 casos
           OR assertsStandardMappingTable(X)        // Grupo B - 1 caso
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

Las dos sub-condiciones de los Grupos A y B se corresponden con las cláusulas 1.1/1.2/1.3 y 1.4 respectivamente.

### Current Behavior (Defect)

Los 7 casos comparten una única causa raíz —la rama DYNAMIC se ejecuta porque `creative_type` sigue valiendo `''`— y se agrupan por el tipo de aserción que resulta contradicha.

**Grupo A — aserciones de valores por defecto STANDARD sobre una invocación que toma la rama DYNAMIC (6 casos).** Los seis casos construyen un `creative` cuyo `asset_feed_spec` es vacío o inalcanzable y aseveran los defaults de la rama STANDARD (`*_max_amount == 1`), heredados de cuando la heurística `object_story_spec or not asset_feed_spec` enrutaba esa forma hacia la extracción STANDARD. Los docstrings de estos casos siguen describiendo, en cambio, los defaults de la rama DYNAMIC: el de imágenes enuncia literalmente «``0`` for each of the five ``*_max_amount`` values» mientras su aserción exige `1`, y el de textos incorpora una nota que justifica el `1` invocando exactamente la heurística ya eliminada.

1.1 WHEN se ejecutan `test_facebook_save_pre_check_images.py::TestBuildResponse::test_response_uses_exact_defaults_for_every_omitted_field` y `test_facebook_save_pre_check_texts.py::TestBuildResponse::test_defaults_for_all_omitted_fields`, que invocan `_build_response` con `adCreative = {'asset_feed_spec': {}}` THEN la suite falla con `AssertionError: assert 0 == 1` en la primera aserción de `images_max_amount`, en `test_facebook_save_pre_check_images.py:3079` y `test_facebook_save_pre_check_texts.py:4417` respectivamente.

1.2 WHEN se ejecutan `test_facebook_save_pre_check_images.py::TestBuildResponse::test_direct_isolated_call_returns_default_response_when_ad_creative_is_explicit_none` y `test_facebook_save_pre_check_texts.py::TestBuildResponse::test_isolated_call_with_explicit_none_ad_creative_returns_default_response`, que invocan `_build_response` con la clave `adCreative` presente y valor `None` THEN la suite falla con `AssertionError: assert 0 == 1` en `test_facebook_save_pre_check_images.py:3446` y `test_facebook_save_pre_check_texts.py:4606` respectivamente, pese a que la normalización `ad_creative = ads_to_publish.get('adCreative') or {}` sí evita el `AttributeError` que esos casos verifican como intención principal.

1.3 WHEN se ejecutan `test_facebook_save_pre_check_images.py::TestBuildResponse::test_direct_isolated_call_returns_default_response_when_ad_creative_key_absent` y `test_facebook_save_pre_check_texts.py::TestBuildResponse::test_isolated_call_with_ad_creative_key_absent_returns_default_response`, que invocan `_build_response` con la clave `adCreative` enteramente ausente de `ads[0]` THEN la suite falla con `AssertionError: assert 0 == 1` en `test_facebook_save_pre_check_images.py:3514` y `test_facebook_save_pre_check_texts.py:4663` respectivamente.

**Grupo B — aserción de la tabla de mapeo STANDARD completa sobre una invocación que toma la rama DYNAMIC (1 caso).** El caso construye un `creative` con `object_story_spec` y `link_data` completamente poblados, sin `asset_feed_spec`, y asevera las 30 claves del mapeo STANDARD documentado en `design.md`. Al tomarse la rama DYNAMIC, toda clave derivada de `object_story_spec`/`link_data` colapsa a su valor por defecto y sólo sobreviven las cuatro claves que se leen directamente de `creative`/`ads[0]` (`name`, `adset_id`, `ad_id`, `daily_budget`).

1.4 WHEN se ejecuta `test_facebook_save_pre_check_images.py::TestBuildResponse::test_direct_isolated_call_reflects_pre_annotated_standard_link_data_per_mapping_table` THEN la suite falla con `AssertionError: assert 0 == 'channel-7-7'` en `test_facebook_save_pre_check_images.py:3347`, porque `adchannel_id` se resuelve como `ad_creative.get('asset_feed_spec', {}).get('ad_channel_id', 0)` en lugar de `object_story_spec.get('ad_channel_id', 0)`, y las aserciones posteriores sobre `images`, `titles`, `bodies`, `descriptions`, `call_to_action_types`, los cinco `*_valid_amount`, los cinco `*_max_amount`, los tres `unique_*`, `daily_budget_valid`, `min_daily_budget`, `proposal_url`, `proposal_url_valid`, `locations` y `locations_valid` quedan sin evaluar tras el primer fallo.

### Expected Behavior (Correct)

Las cláusulas 2.1 a 2.4 se corresponden una a una con las cláusulas 1.1 a 1.4. Las cláusulas 2.5 a 2.10 son transversales.

2.1 WHEN se ejecutan los 2 casos de valores por defecto con `asset_feed_spec = {}` referidos en 1.1 THEN la suite de pruebas SHALL parametrizarlos sobre `creative_type`, fijando `use_case.creative_type` explícitamente antes de invocar `_build_response`, SHALL aseverar `images_max_amount`, `titles_max_amount`, `bodies_max_amount`, `descriptions_max_amount` y `call_to_action_types_max_amount` iguales a `0` cuando `creative_type` es `CreativeType.DYNAMIC.value` e iguales a `1` cuando es `CreativeType.STANDARD.value`, y SHALL pasar en ambas parametrizaciones preservando intactas las restantes aserciones de cada caso sobre listas vacías, indicadores `False`, `min_daily_budget == 0` y `proposal_url == ''`.

2.2 WHEN se ejecutan los 2 casos con `adCreative` presente y valor `None` referidos en 1.2 THEN la suite de pruebas SHALL parametrizarlos sobre `creative_type` con el mismo criterio de 2.1, SHALL seguir aseverando que la invocación no propaga excepción alguna y que el conjunto de claves de la respuesta es exactamente el documentado, y SHALL pasar en ambas parametrizaciones.

2.3 WHEN se ejecutan los 2 casos con la clave `adCreative` ausente referidos en 1.3 THEN la suite de pruebas SHALL parametrizarlos sobre `creative_type` con el mismo criterio de 2.1, SHALL seguir aseverando la equivalencia observable entre «clave ausente» y «clave presente con valor `None`», y SHALL pasar en ambas parametrizaciones.

2.4 WHEN se ejecuta el caso de la tabla de mapeo STANDARD referido en 1.4 THEN la suite de pruebas SHALL fijar `use_case.creative_type` en `CreativeType.STANDARD.value` antes de invocar `_build_response` y SHALL pasar conservando **sin modificación** las 30 aserciones actuales de la tabla de mapeo, incluida `adchannel_id == 'channel-7-7'`; este caso SHALL NOT parametrizarse sobre la rama DYNAMIC, dado que su `creative` carece de `asset_feed_spec` por diseño.

2.5 WHEN un caso de prueba de `TestBuildResponse` invoca `_build_response` de forma directa, sin atravesar `execute()`, THEN la suite de pruebas SHALL fijar `use_case.creative_type` explícitamente al valor de `CreativeType` correspondiente a la rama que ese caso pretende caracterizar, y SHALL NOT depender del valor `''` que el constructor deja como estado inicial.

2.6 The suite de pruebas SHALL actualizar el docstring de cada caso modificado para describir el despacho vigente por `self.creative_type`, eliminando toda referencia a la heurística `object_story_spec or not asset_feed_spec` y resolviendo la contradicción actual entre docstring y aserción en los casos de valores por defecto.

2.7 IF el identificador de un caso o de una parametrización contradice el comportamiento aseverado tras el realineamiento THEN la suite de pruebas SHALL renombrarlo para reflejar la rama efectivamente ejercitada, de modo que cada parametrización sea distinguible por su `id` de pytest.

2.8 The suite de pruebas SHALL alcanzar `0 failed` al ejecutarse sobre `tests/v2/unit` desde el directorio `sinergia/` con el intérprete de `venv/`, y el total de casos recolectados SHALL crecer de 2574 a 2580 como consecuencia de parametrizar seis casos sobre dos ramas cada uno.

2.9 The archivo `sinergia/app/v2/use_cases/meta_ads.py` y todo archivo bajo `sinergia/app/` SHALL permanecer sin modificaciones, verificable mediante `git diff --stat -- app/`.

2.10 WHILE se adaptan las pruebas, IF una aserción obsoleta resulta imposible de realinear sin cambiar el código productivo THEN la suite de pruebas SHALL NOT eliminar ni marcar como `xfail` o `skip` el caso afectado, y el hallazgo SHALL ser escalado al usuario como una ambigüedad de alcance no resuelta.

### Unchanged Behavior (Regression Prevention)

3.1 WHEN se ejecuta `tests/v2/unit` THEN los 2567 casos que actualmente pasan SHALL CONTINUE TO pasar, sin que ninguno cambie a `failed`, `error`, `skipped` o `xfail`.

3.2 WHEN se ejecutan los dos archivos objetivo THEN los casos que actualmente pasan dentro de esos mismos archivos SHALL CONTINUE TO pasar sin modificación de sus aserciones, incluidos `test_response_contains_exactly_the_keys_from_requirement_14_1`, `test_response_reflects_exact_explicit_asset_feed_spec_values_including_images_projection`, `test_exact_key_set_and_explicit_values_reflected`, `test_images_mapped_to_url_valid_error_subdicts`, `test_proposal_url_is_comma_joined_website_urls_in_the_same_order`, `test_proposal_url_is_comma_join_of_link_urls_website_url_in_order`, ambos `test_proposal_locations_*` y ambos casos de recorrido completo de `execute()` en modo DYNAMIC.

3.3 WHEN se ejecuta cualquier caso que invoca `_build_response` a través de `execute()` THEN ese caso SHALL CONTINUE TO obtener el `creative_type` desde `_set_creative_type(campaign_setup)` a partir de `campaign_setup['attributes']['meta_campaign_mode']`, sin fijación manual del atributo, de modo que la ruta de producción siga ejercitándose tal como está hoy.

3.4 WHEN se ejecutan los casos de `TestUnsupportedMetaCampaignModeRaisesValueError` de ambos archivos THEN SHALL CONTINUE TO aseverar que `execute()` propaga `ValueError` con el mensaje exacto de `CreativeType` y que `use_case.creative_type` conserva el `''` del constructor, sin que la fijación manual introducida en `TestBuildResponse` altere esa expectativa.

3.5 WHEN se ejecutan las suites de los restantes cuatro casos de uso derivados de `FacebookSavePreCheckBaseUseCase` (`test_facebook_save_pre_check_ctas.py`, `test_facebook_save_pre_check_budget.py`, `test_facebook_save_pre_check_proposal_url.py`, `test_facebook_save_pre_check_locations.py`) THEN SHALL CONTINUE TO pasar sin modificación, incluidos los casos que sustituyen `_build_response` por un doble mediante `patch.object`.

3.6 WHEN se ejecutan `test_facebook_launch_campaign.py`, `test_facebook_get_launch_campaign_creatives.py` y `test_funnel_flow_validator.py` THEN SHALL CONTINUE TO pasar sin modificación, dado que sus referencias a `_build_response` corresponden a otras clases o a dobles de prueba.

3.7 WHEN se modifica una función auxiliar o *fixture* compartida (`make_ad_creative`, `make_asset_feed_spec`, `make_object_story_spec`, `make_link_data`, `make_ad`, `make_creative`, `use_case_factory`, el centinela `ABSENT`) THEN todos los casos que ya la consumían y pasaban SHALL CONTINUE TO pasar con la misma semántica de valores por defecto.

3.8 WHEN se ejecuta cualquier caso adaptado THEN `AdChannelRepository` y `CampaignChannelPublishRepository` SHALL CONTINUE TO estar sustituidos por dobles parcheados en `app.v2.use_cases.meta_ads`, y `redis_client` junto con toda llamada HTTP SHALL CONTINUE TO estar parcheados, de modo que la *fixture* `deny_network` de ambos archivos no sea nunca disparada y ninguna prueba realice acceso real a Strapi, a Redis ni a la red.

3.9 WHERE un caso de prueba verifica la identidad por referencia del objeto `creative` que fluye hacia `_save_creative_to_publish` y `_build_response`, o el número de instanciaciones de repositorios, THEN esas aserciones SHALL CONTINUE TO cumplirse sin cambios.

3.10 WHEN se ejecuta `tests/v2` o la suite completa `tests/` THEN los fallos preexistentes y ajenos a este bugfix SHALL CONTINUE TO comportarse igual que hoy, sin ser corregidos ni agravados por este cambio: `test_pin_format_ad_variant_integration.py::TestPinFormatAdVariantEndToEndWorkflow::test_end_to_end_pin_format_workflow_persists_pinned_state` y los fallos y errores de `tests/v1/`.

3.11 WHEN se ejecuta `tests/v2/unit` tras el arreglo THEN el tiempo de ejecución SHALL CONTINUE TO mantenerse en el orden de magnitud actual (aproximadamente 53 segundos), sin introducir esperas reales, reintentos ni entrada/salida de red.
