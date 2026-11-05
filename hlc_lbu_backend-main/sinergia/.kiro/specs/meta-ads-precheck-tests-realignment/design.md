# Realineamiento de las pruebas del pre-check de Meta Ads — Diseño del Bugfix

## Overview

La refactorización manual de la rama STANDARD (HL-2496) cambió el contrato observable de
`FacebookGeneratePreCheckCreativeUseCase` y de `FacebookSavePreCheckBaseUseCase` sin actualizar la
suite. El defecto está en las pruebas: 44 nodos de pytest codifican suposiciones obsoletas y fallan
contra un código productivo que se considera correcto.

El arreglo consiste en realinear esos 44 nodos —y solo esos— con el contrato vigente, en tres
archivos de prueba, sin tocar una sola línea bajo `sinergia/app/`. El trabajo se agrupa en cuatro
causas raíz independientes (A–D), cada una con un cambio mínimo acotado, más una dependencia de
orden entre B y C que se descubrió al inspeccionar el código real y que este diseño resuelve
explícitamente.

La estrategia de validación invierte la habitual: no se escriben pruebas exploratorias nuevas
porque los contraejemplos ya existen y son precisamente los 44 fallos. El baseline se captura
antes de tocar nada, y la preservación se demuestra comparando el resultado nodo por nodo.

## Glossary

- **Bug_Condition (C)**: un nodo de pytest `X` de uno de los tres archivos objetivo que codifica al
  menos una suposición obsoleta sobre el contrato refactorizado de `meta_ads.py`.
- **Property (P)**: el nodo pasa (`outcome == PASSED`) sin que ningún archivo bajo `sinergia/app/`
  haya cambiado.
- **Preservation**: todo nodo de pytest que no cumple C mantiene exactamente el mismo `outcome`
  antes y después del arreglo. Incluye los 283 nodos que pasan en los archivos objetivo y los
  1632 de la suite completa.
- **F**: la suite en su estado actual (44 failed, 1632 passed).
- **F'**: la suite después del realineamiento (0 failed, 1676 passed).
- **`_set_creative_type`**: método nuevo de `FacebookSavePreCheckBaseUseCase`
  (`app/v2/use_cases/meta_ads.py:2492`) que ejecuta
  `CreativeType(campaign_setup.get('attributes', {}).get('meta_campaign_mode')).value`. No admite
  valores fuera de `{"STANDARD", "DYNAMIC"}`.
- **`_validate_standard_cta`**: `app/v2/use_cases/meta_ads.py:1347`. Lee el texto del CTA con
  `cta.get('type', {}).get('value')` (línea 1360) y anota el resultado en `cta['valid']` (línea 1364).
- **`_build_standard_creative_entry`**: `app/v2/use_cases/meta_ads.py:1442`. Firma
  `(self, idx, ad_set_to_publish, ad)`; desciende él mismo con `ad.get('adCreative')` y compone
  `name` como `f"{ad_set_to_publish.get('name')} - {ad.get('name')}"`.
- **Forma canónica del CTA**: `link_data['call_to_action'] = {'type': {'value': <str>, 'valid': <bool>}}`,
  tal como la escribe `FacebookSavePreCheckCTAsUseCase._validate_ctas_standard`
  (`app/v2/use_cases/meta_ads.py:2766`).
- **Forma plana del CTA**: `{'type': <str>}`. Es la forma previa a la refactorización y la que
  construyen hoy las pruebas.
- **Nodo vacuo**: nodo que pasa por una razón distinta de la que su docstring declara, porque su
  entrada degenera antes de alcanzar la lógica que pretende ejercitar.

## Bug Details

### Bug Condition

El sujeto bajo prueba no es el código productivo sino la propia suite. La condición de bug
identifica los nodos de pytest que codifican suposiciones obsoletas.

**Formal Specification:**

```
FUNCTION isBugCondition(X)
  INPUT: X of type PytestNodeId
  OUTPUT: boolean

  RETURN X.file IN TARGET_TEST_FILES
         AND (
              expectsOkZero(X)                    // Grupo A - 23 nodos
           OR buildsFlatCallToActionType(X)       // Grupo B -  8 nodos
           OR passesAdCreativeAsThirdArgument(X)  // Grupo C -  3 nodos
           OR assumesUnknownModeTolerance(X)      // Grupo D - 10 nodos
         )
END FUNCTION
```

donde

```
TARGET_TEST_FILES = {
  tests/v2/unit/use_cases/test_facebook_generate_pre_check_creative.py,
  tests/v2/unit/use_cases/test_facebook_save_pre_check_images.py,
  tests/v2/unit/use_cases/test_facebook_save_pre_check_texts.py
}
```

```
FUNCTION expectedBehavior(result)
  INPUT: result of type PytestOutcome
  OUTPUT: boolean

  RETURN result.outcome = PASSED
         AND result.outcome NOT IN {SKIPPED, XFAIL, XPASS, ERROR}
         AND productionSourceUnchanged() = TRUE   // git diff --stat -- app/ vacío
END FUNCTION
```

### Examples

- `TestExecuteMissingCreative::test_ad_without_creative_as_non_first_ad_yields_ok_zero_without_invoking_validator[ad_creative-absent]`
  espera `result["ok"] == 0`; obtiene `AssertionError: assert 1 == 0`. Esperado tras el arreglo:
  `result["ok"] == 1`.
- `TestStandardCtaValidation::test_cta_valid_scenario` pasa `call_to_action={"type": "LEARN_MORE"}`;
  `_validate_standard_cta` evalúa `"LEARN_MORE".get('value')` y lanza
  `AttributeError: 'str' object has no attribute 'get'`. Esperado tras el arreglo:
  `call_to_action={"type": {"value": "LEARN_MORE"}}` y `link_data["call_to_action"]["valid"] is True`.
- `TestStandardCreativesEntry::test_object_story_spec_completely_absent_uses_every_documented_default`
  pasa `ad_creative` como tercer argumento; `ad.get('adCreative')` devuelve `None`, todo degenera a
  los defaults y `ad_id` resulta `None` en lugar de `"ad-absent-oss"`. Esperado tras el arreglo:
  tercer argumento `ad`, `ad_id == "ad-absent-oss"`, `name == "AdSet-Absent-OSS - Ad"`.
- `TestUnknownMetaCampaignMode::...[meta_campaign_mode-none]` espera un no-op sin mutación; obtiene
  `ValueError: None is not a valid CreativeType`. Esperado tras el arreglo: la prueba asevera la
  excepción con `pytest.raises(ValueError)`.
- Caso borde ya correcto que debe seguir pasando:
  `TestExecuteStandardAdChannelIdReading::test_build_standard_creative_entry_distinguishes_explicit_none_from_absent_key[absent-key]`
  espera `adchannel_id == 0` y pasa hoy por degeneración; tras corregir el tercer argumento debe
  seguir esperando `0`, ahora por la razón correcta (`object_story_spec` sin la clave).

## Expected Behavior

### Preservation Requirements

**Comportamientos que no deben cambiar:**

- Los 1632 nodos que pasan en la suite completa siguen pasando, sin cambiar a `failed`, `error`,
  `skipped` ni `xfail`.
- Los 283 nodos que pasan dentro de los tres archivos objetivo siguen pasando sin modificación de
  sus aserciones.
- Todo nodo de la rama DYNAMIC conserva su contrato basado en `asset_feed_spec`, sin adaptación
  alguna derivada de este bugfix.
- Los builders y fixtures compartidos (`make_link_data`, `make_object_story_spec`, `make_ad`,
  `make_ad_set`, `make_ad_creative`, `make_campaign_setup`, `make_creative`, `make_ad_channel`,
  `use_case_factory`, `patch_redis_client`, el centinela `ABSENT`) conservan su semántica de valores
  por defecto para todo consumidor existente.
- `AdChannelRepository` y `CampaignChannelPublishRepository` siguen sustituidos por dobles
  parcheados en `app.v2.use_cases.meta_ads`; `redis_client` y toda llamada a la Graph API siguen
  parcheados. Ninguna prueba accede a Strapi, Redis ni a la red.
- Las cuatro parametrizaciones de `_STANDARD_SUPPORTED_COMBINATIONS` siguen siendo exactamente
  `awareness-reach`, `leads-conversations`, `leads-lead-generation`, `sales-offsite-conversions`.
- El tiempo de ejecución de los tres archivos se mantiene en el orden de 75–95 s, sin esperas
  reales ni reintentos.

**Alcance:**

Todo nodo que no cumple `isBugCondition` queda completamente inafectado. En particular:

- Los 15 nodos restantes de `TestExecuteAggregationAndStatus`, `TestExecuteCreationBlock` y
  `TestExecuteCombinedScenarios` que ya aseveran `ok == 1`.
- Los nodos de `TestStandardCtaValidation` que ejercitan CTA ausente/falsy (`test_cta_absent_scenario`,
  5 parametrizaciones) y CTA truthy no-`dict` (`test_cta_non_dict_scenario`), que pasan porque
  `_validate_standard_cta` retorna antes de tocar `type`.
- `test_save_creative_to_publish_distinguishes_explicit_none_from_absent_key` (3 parametrizaciones),
  que ejercita el otro sitio de lectura de `ad_channel_id` y no depende de la firma cambiada.
- Los 11 archivos de prueba restantes bajo `tests/`.

El comportamiento correcto esperado para los nodos que sí cumplen la condición está definido en
Correctness Properties (Property 1).

## Hypothesized Root Cause

Las cuatro causas están confirmadas contra el código productivo leído en esta fase; no quedan
hipótesis abiertas.

1. **Grupo A — `execute()` devuelve `ok=1` incondicionalmente.** `app/v2/use_cases/meta_ads.py:1980`
   contiene `"ok": 1, # if has_errors else 1`. `has_errors` se sigue calculando en la línea 1917
   pero ya no influye en la respuesta. 23 nodos aseveran `result["ok"] == 0` en 15 sitios de
   aserción distintos.

2. **Grupo B — `call_to_action.type` pasó a ser un objeto anidado.**
   `_validate_standard_cta` (línea 1360) hace `cta.get('type', {}).get('value')` y
   `_build_standard_creative_entry` (línea 1478) hace
   `call_to_action.get('type', {}).get('valid', False) if call_to_action else False`. Con la forma
   plana `{'type': <str>}` ambas expresiones lanzan `AttributeError`. La forma canónica la produce
   `_validate_ctas_standard` (línea 2766). La misma expresión anidada aparece además en
   `_build_response` (línea 2532) y en `_build_standard_creative_published` (línea 3532), lo que
   confirma que la forma anidada es el contrato del sistema, no una peculiaridad de un método.

3. **Grupo C — `_build_standard_creative_entry` cambió de firma y de composición de `name`.** El
   tercer parámetro pasó de `ad_creative` a `ad` (línea 1442) y el método desciende él mismo con
   `ad.get('adCreative') or {}` (línea 1443). `name` pasó a
   `f"{ad_set_to_publish.get('name')} - {ad.get('name')}"` (línea 1464). Al recibir un `ad_creative`,
   `ad.get('adCreative')` devuelve `None`, se sustituye por `{}` y **todo** el resultado degenera
   silenciosamente a los valores por defecto.

4. **Grupo D — `_set_creative_type` convierte el modo de campaña de forma estricta.** El método
   (línea 2492) ejecuta `CreativeType(...).value` antes del bloque `try` de validación, tanto en
   `FacebookSavePreCheckImagesUseCase.execute()` (invocación en 2633, extracción de `asset_feed` en
   2637) como en `FacebookSavePreCheckTextsUseCase.execute()` (invocación en 2674, extracción en
   2678). Cualquier valor fuera de
   `{"STANDARD", "DYNAMIC"}` aborta `execute()` con `ValueError`. Mensajes exactos verificados en
   este entorno (Python 3.8): `"'' is not a valid CreativeType"`,
   `"None is not a valid CreativeType"`, `"'SOME_OTHER_MODE' is not a valid CreativeType"`.
   Ninguna prueba de la suite menciona `_set_creative_type`: el método entró sin cobertura propia.
   `_set_creative_type` se invoca desde seis `execute()` (líneas 2633, 2674, 2782, 2833, 2884, 2958:
   imágenes, textos, CTAs, presupuesto, URL de propuesta y ubicaciones), pero solo las suites de
   imágenes y textos construyen escenarios con modo inválido, por lo que solo ellas fallan. Esto
   confirma el alcance de tres archivos: las otras cuatro suites de pre-check no requieren cambio.

### Hallazgo adicional: acoplamiento B ↔ C y un nodo vacuo

`TestStandardCreativesEntry::test_property_construction_never_raises_and_always_returns_the_fixed_key_set`
(línea 4220, Property 8, 100 ejemplos de Hypothesis) **pasa hoy de forma vacua**. Pasa
`ad_creative` como tercer argumento, así que `ad.get('adCreative')` devuelve `None` y
`object_story_spec`/`link_data`/`call_to_action` colapsan a `{}` antes de que la forma generada por
`standard_object_story_spec_shapes()` (línea 499) pueda influir en nada. El nodo asevera solo el
conjunto de claves y el `idx`, ambos invariantes bajo la degeneración.

Su estrategia de generación `_STANDARD_LINK_DATA_FIELD_STRATEGIES` (línea 428) produce
`call_to_action` en forma **plana**: `st.fixed_dictionaries({"type": st.text(max_size=20)})`. Si se
corrigiera el tercer argumento sin migrar la estrategia, el nodo empezaría a ejercitar las formas
generadas y fallaría con `AttributeError`, rompiendo la preservación 3.2. Verificado
empíricamente invocando el método productivo directamente:

```
flat   {'type': 'LEARN_MORE'}                      -> AttributeError: 'str' object has no attribute 'get'
nested {'type': {'value': 'LEARN_MORE', 'valid': True}}
       -> call_to_action_types=[{'value': 'LEARN_MORE', 'valid': True}]
          call_to_action_types_valid_amount=True, name='AdSet - Ad', ad_id='ad-1'
```

Consecuencia de diseño: la migración de la estrategia de Hypothesis (Grupo B) es **prerrequisito**
de la corrección del tercer argumento (Grupo C) si se decide desvacuar ese nodo, y en cualquier caso
el orden B → C es el único seguro. Ver Orden de Ejecución y Riesgos.

## Correctness Properties

Property 1: Bug Condition - Los 44 nodos desalineados pasan sin tocar el código productivo

_For any_ nodo de pytest `X` donde la condición de bug se cumple (`isBugCondition(X)` devuelve
`true`), la suite realineada `F'` SHALL producir `outcome == PASSED` para `X`, sin que `X` haya sido
eliminado, marcado `skip`/`xfail` ni relajado, y sin que ningún archivo bajo `sinergia/app/` haya
sido modificado (`git diff --stat -- app/` vacío).

**Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9, 2.10, 2.11, 2.12, 2.13**

Property 2: Preservation - Todo nodo alineado conserva su resultado

_For any_ nodo de pytest `X` donde la condición de bug NO se cumple (`isBugCondition(X)` devuelve
`false`), la suite realineada `F'` SHALL producir para `X` exactamente el mismo `outcome` que la
suite original `F`, preservando los 283 nodos que ya pasan en los archivos objetivo, los 1632 de la
suite completa, la semántica de los builders y fixtures compartidos, el aislamiento de red y
repositorios, y el conjunto de parametrizaciones existentes.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8**

## Fix Implementation

### Localización de los 44 nodos

Rutas relativas a `sinergia/`. Todas las líneas verificadas en el estado actual del árbol
(`HEAD = 745a413`).

#### Grupo A — 23 nodos, todos en `tests/v2/unit/use_cases/test_facebook_generate_pre_check_creative.py`

| # | Clase (línea) | Caso (línea `def`) | Aserción `ok == 0` | Parametrización | Nodos |
|---|---|---|---|---|---|
| A1 | `TestExecuteMissingCreative` (1393) | `test_ad_without_creative_as_non_first_ad_yields_ok_zero_without_invoking_validator` (1412) | 1462 | `ad_creative-absent`, `-none`, `-empty-dict` | 3 |
| A2 | `TestExecuteMissingCreative` | `test_iteration_continues_to_next_ad_after_missing_creative` (1485) | 1612 | `ad_creative-absent`, `-none`, `-empty-dict` | 3 |
| A3 | `TestExecuteMissingCreative` | `test_missing_creative_as_ads_zero_empty_dict_does_not_raise_and_yields_ok_zero` (1665) | 1711 | — | 1 |
| A4 | `TestExecuteDynamicBranch` (1714) | `test_is_unique_texts_raising_removes_only_the_corresponding_unique_key_and_yields_ok_zero` (1858) | 1902 | `titles`, `bodies`, `descriptions` | 3 |
| A5 | `TestExecuteDynamicBranch` | `test_is_valid_length_raising_still_leaves_the_unique_key_present_but_yields_ok_zero` (1913) | 1965 | `titles`, `bodies`, `descriptions` | 3 |
| A6 | `TestExecuteDynamicBranch` | `test_validate_cta_raising_for_every_entry_leaves_no_valid_key_and_iteration_continues` (2023) | 2069 | — | 1 |
| A7 | `TestExecuteDynamicBranch` | `test_validate_images_precheck_raising_yields_ok_zero` (2110) | 2133 | — | 1 |
| A8 | `TestExecuteDynamicBranch` | `test_is_valid_amount_raising_yields_ok_zero` (2165) | 2186 | — | 1 |
| A9 | `TestExecuteDynamicBranch` | `test_non_comparable_daily_budget_leaves_min_daily_budget_present_but_daily_budget_valid_absent` (2224) | 2255 | — | 1 |
| A10 | `TestExecuteDynamicBranch` | `test_invalid_link_urls_entry_leaves_link_url_valid_absent_while_daily_budget_valid_stays_present` (2291) | 2400 | — | 1 |
| | | | | **subtotal cláusula 1.1** | **18** |
| A11 | `TestExecuteCreationBlock` (4476) | `test_object_story_spec_as_string_raises_type_error_inside_creation_block_and_yields_ok_zero` (4658) | 4684 | — | 1 |
| A12 | `TestExecuteCreationBlock` | `test_failed_ad_as_ads_zero_still_contributes_to_creatives_alongside_a_created_ad` (4768) | 4842 | — | 1 |
| A13 | `TestExecuteAggregationAndStatus` (4853) | `test_all_failed_results_yield_ok_zero_and_status_200` (4968) | 4992 | — | 1 |
| A14 | `TestExecuteAggregationAndStatus` | `test_mixed_created_and_failed_results_yield_ok_zero_and_status_200` (4994) | 5018 | — | 1 |
| A15 | `TestExecuteCombinedScenarios` (5719) | `test_multiple_ad_sets_with_valid_and_invalid_ads_process_independently_yield_ok_zero` (5832) | 5917 | — | 1 |
| | | | | **subtotal cláusula 1.2** | **5** |

Los 15 sitios de aserción son exactamente las líneas 1462, 1612, 1711, 1902, 1965, 2069, 2133,
2186, 2255, 2400, 4684, 4842, 4992, 5018, 5917. Ninguna otra línea del archivo contiene
`assert result["ok"] == 0`.

#### Grupo B — 8 nodos, todos en `test_facebook_generate_pre_check_creative.py`

| # | Clase (línea) | Caso (línea `def`) | Sitio del CTA plano | Nodos |
|---|---|---|---|---|
| B1 | `TestStandardCtaValidation` (3617) | `test_property_annotation_mirrors_validate_cta_for_goal_result` (3701) | 3720 | 1 |
| B2 | `TestStandardCtaValidation` | `test_cta_valid_scenario` (3737) | 3750 | 1 |
| B3 | `TestStandardCtaValidation` | `test_cta_invalid_scenario` (3763) | 3777 | 1 |
| B4 | `TestStandardAnnotationContract` (3877) | `test_property_combined_annotation_contract_holds_independently_per_field` (4052) vía helper `_run_full_standard_validation` | 4015 | 1 |
| | | | **subtotal cláusula 1.3** | **4** |
| B5–B8 | `TestStandardCombinationSuccessScenarios` (4316) | `test_full_success_scenario_yields_ok_1_and_all_seven_success_annotations_true` (4447) vía helper `_run_success_scenario` (4341) | 4381 (`WHATSAPP_MESSAGE`) y 292 (`make_standard_link_data_full`, `LEARN_MORE`) | 4 |
| | | | **subtotal cláusula 1.4** | **4** |

Sitio adicional relevante, **no** entre los 44 pero acoplado (ver hallazgo B↔C):
`_STANDARD_LINK_DATA_FIELD_STRATEGIES["call_to_action"]` en la línea 437.

#### Grupo C — 3 nodos, todos en `test_facebook_generate_pre_check_creative.py`

| # | Clase (línea) | Caso (línea `def`) | Sitio de la invocación | Nodos |
|---|---|---|---|---|
| C1 | `TestStandardCreativesEntry` (4113) | `test_object_story_spec_completely_absent_uses_every_documented_default` (4245) | 4276 (extracción de `ad_creative`), 4278 (llamada) | 1 |
| C2–C3 | `TestExecuteStandardAdChannelIdReading` (5975) | `test_build_standard_creative_entry_distinguishes_explicit_none_from_absent_key` (6077) | 6098 (extracción), 6100–6102 (llamada) | 2 (`explicit-none`, `positive-integer`) |

El nodo `[absent-key]` del mismo caso pasa hoy y debe seguir pasando con el valor esperado `0`.

Sitios adicionales del mismo patrón, **no** entre los 44:
`test_property_construction_never_raises_and_always_returns_the_fixed_key_set` (4220, llamada en
4237) — nodo vacuo, ver Riesgo R1.

#### Grupo D — 10 nodos, en los dos archivos de `save_pre_check`

| # | Archivo | Clase (línea) | Caso (línea `def`) | Sitio a cambiar | Nodos |
|---|---|---|---|---|---|
| D1 | `test_facebook_save_pre_check_images.py` | `TestExecuteOrchestration` (1178) | `test_execute_calls_operations_in_exact_order` (1190) | 1220 (`make_campaign_setup(meta_campaign_mode=None)`) y docstring 1211 | 1 |
| D2 | `test_facebook_save_pre_check_texts.py` | `TestExecuteOrchestrationAndShortCircuit` (1222) | `test_execute_calls_operations_in_exact_order` (1234) | 1265 y docstring 1256 | 1 |
| | | | | **subtotal cláusula 1.8** | **2** |
| D3–D6 | `test_facebook_save_pre_check_images.py` | `TestUnknownMetaCampaignMode` (2123) | `test_execute_invokes_neither_branch_and_continues_without_mutation` (2158), `parametrize` 2145–2156 | cuerpo completo 2158–2237 | 4 |
| D7–D10 | `test_facebook_save_pre_check_texts.py` | `TestUnknownMetaCampaignMode` (3455) | `test_no_validator_calls_and_no_mutation_regardless_of_truthy_asset_feed_and_story_spec` (3498), `parametrize` 3481–3497 | cuerpo completo 3498–3604 | 4 |
| | | | | **subtotal cláusula 1.7** | **8** |

IDs de nodo actuales del grupo D:
`[meta_campaign_mode_empty_string-campaign_setup_kwargs0]`, `[meta_campaign_mode_none-campaign_setup_kwargs1]`,
`[meta_campaign_mode_unrelated_value-campaign_setup_kwargs2]`, `[meta_campaign_mode_key_absent-campaign_setup_kwargs3]`
(imágenes, sin `ids=` explícitos) y `[meta_campaign_mode-empty-string]`, `[meta_campaign_mode-none]`,
`[meta_campaign_mode-arbitrary-value]`, `[meta_campaign_mode-key-absent]` (textos, con `pytest.param(..., id=...)`).

### Grupo A — Cambio mínimo y renombrados

**Cambio de aserción.** En cada uno de los 15 sitios, `assert result["ok"] == 0` pasa a
`assert result["ok"] == 1`. Nada más cambia: las aserciones sobre anotaciones presentes, ausentes o
removidas del creativo, sobre `status_code == 200`, sobre `data["creatives"]` y sobre el reindexado
de `idx` quedan intactas (cláusulas 2.1 y 2.2).

**Criterio de renombrado (cláusula 2.9).** Se renombra todo identificador de caso cuyo nombre
contenga `ok_zero`, sustituyendo el fragmento por `ok_1` para alinearse con la convención ya
presente en el archivo (`test_full_success_scenario_yields_ok_1_and_...`, línea 4447). Cuando el
nombre además expresaba un contraste que deja de existir (`..._but_yields_ok_zero`), la conjunción
adversativa `but` pasa a `and`. Ninguna clase del grupo A necesita renombrarse: ninguna afirma nada
sobre el valor de `ok` en su nombre; `TestExecuteAggregationAndStatus` sigue describiendo con
exactitud qué agrega (`results`) y qué status devuelve.

Los 10 casos a renombrar (los 5 restantes de los 15 sitios ya tienen nombres neutrales y no se
tocan):

| Línea | Nombre actual | Nombre propuesto |
|---|---|---|
| 1412 | `test_ad_without_creative_as_non_first_ad_yields_ok_zero_without_invoking_validator` | `test_ad_without_creative_as_non_first_ad_yields_ok_1_without_invoking_validator` |
| 1665 | `test_missing_creative_as_ads_zero_empty_dict_does_not_raise_and_yields_ok_zero` | `test_missing_creative_as_ads_zero_empty_dict_does_not_raise_and_yields_ok_1` |
| 1858 | `test_is_unique_texts_raising_removes_only_the_corresponding_unique_key_and_yields_ok_zero` | `test_is_unique_texts_raising_removes_only_the_corresponding_unique_key_and_yields_ok_1` |
| 1913 | `test_is_valid_length_raising_still_leaves_the_unique_key_present_but_yields_ok_zero` | `test_is_valid_length_raising_still_leaves_the_unique_key_present_and_yields_ok_1` |
| 2110 | `test_validate_images_precheck_raising_yields_ok_zero` | `test_validate_images_precheck_raising_yields_ok_1` |
| 2165 | `test_is_valid_amount_raising_yields_ok_zero` | `test_is_valid_amount_raising_yields_ok_1` |
| 4658 | `test_object_story_spec_as_string_raises_type_error_inside_creation_block_and_yields_ok_zero` | `test_object_story_spec_as_string_raises_type_error_inside_creation_block_and_yields_ok_1` |
| 4968 | `test_all_failed_results_yield_ok_zero_and_status_200` | `test_all_failed_results_yield_ok_1_and_status_200` |
| 4994 | `test_mixed_created_and_failed_results_yield_ok_zero_and_status_200` | `test_mixed_created_and_failed_results_yield_ok_1_and_status_200` |
| 5832 | `test_multiple_ad_sets_with_valid_and_invalid_ads_process_independently_yield_ok_zero` | `test_multiple_ad_sets_with_valid_and_invalid_ads_process_independently_yield_ok_1` |

Casos del grupo A que conservan su nombre: 1485, 2023, 2224, 2291, 4768.

**Docstrings del grupo A (cláusula 2.10).** Tres focos concretos:

1. **Línea 4859**, docstring de clase de `TestExecuteAggregationAndStatus`: contiene la copia
   literal `"ok": 0 if has_errors else 1,`. Debe reemplazarse por el código vigente
   (`"ok": 1, # if has_errors else 1`) y el párrafo introductorio debe dejar de describir la
   agregación como algo que determina `ok`. La clase sigue siendo válida: `results` sí se agrega y
   el `status_code` sí se asevera; lo que cambia es que `ok` ya no refleja `has_errors`.
2. **Línea 1680**, docstring de `test_missing_creative_as_ads_zero_empty_dict_...`: afirma que
   «la lista `results` es lo que gobierna `has_errors`». Se conserva la parte factual (la entrada
   `Failed` sí se registra en `results`) y se elimina la inferencia de que eso produzca `ok=0`.
3. **Líneas 1497–1502 y 1605–1607**, docstring y comentarios de
   `test_iteration_continues_to_next_ad_after_missing_creative`. Este caso contiene una
   *verificación de aislamiento* en la línea 1555 (`assert isolated_result["ok"] == 1`) cuyo
   propósito declarado era demostrar «que la presencia del ad sin creativo es lo que voltea el `ok`
   agregado a 0». Tras el arreglo ambos `ok` valen 1 y la comparación pierde poder discriminante.
   La aserción de la línea 1555 **se conserva sin cambios** (cláusula 2.1: las demás aserciones
   quedan intactas) y el texto se reescribe para describir lo que sigue siendo cierto: el ad
   posterior al creativeless se alcanza y valida (`asset_feed_after["unique_titles"] is True`,
   `mock_is_unique_texts.call_count == 6`), que es la evidencia real de que `continue` no
   interrumpe el bucle. El diseño registra explícitamente que la comprobación de aislamiento queda
   como redundancia no discriminante, en lugar de eliminarla.

### Grupo B — Migración del `call_to_action` a la forma anidada

**Forma destino.** `{'type': {'value': <cta_text>, 'valid': <bool>}}`, idéntica a la que escribe
`_validate_ctas_standard`. Dos consumidores productivos la leen:
`_validate_standard_cta` lee `['type']['value']` y escribe la anotación en `cta['valid']` (nivel
raíz del CTA, no dentro de `type`); `_build_standard_creative_entry` lee `['type']['valid']` para
`call_to_action_types_valid_amount` y emite `call_to_action_types = [call_to_action['type']]`, es
decir `[{'value': ..., 'valid': ...}]` — exactamente la forma que el resto de la suite ya usa para
la rama DYNAMIC (`call_to_action_types=[{"value": "LEARN_MORE"}]`, líneas 2421, 4708, 5343).

**Decisión: helper nuevo + cambio localizado, sin modificar `make_link_data`.**

Se evaluaron tres opciones:

| Opción | Efecto sobre 3.4 | Veredicto |
|---|---|---|
| Cambiar el default de `make_link_data` (línea 117) para que `call_to_action` sea anidado | `make_link_data` tiene `call_to_action=None` por defecto y es consumido por decenas de nodos, incluidos los que caracterizan CTA ausente/falsy y no-`dict` (3804, 3850). Cambiar su default alteraría esos escenarios | **Rechazada** |
| Añadir un parámetro opcional a `make_link_data` (p. ej. `cta_text=`) | Amplía la superficie de un builder compartido para un solo escenario; los casos que necesitan CTA no-`dict` seguirían pasando el valor crudo, dejando dos vías de construcción coexistiendo | **Rechazada** |
| Introducir un helper nuevo de módulo, `make_standard_cta(value, valid=ABSENT)`, y usarlo en los 6 sitios de construcción de CTA anidado | Cero impacto sobre los consumidores existentes de `make_link_data`; centraliza la forma canónica en un punto único; los escenarios de CTA falsy/no-`dict` siguen pasando valores crudos, que es precisamente lo que caracterizan | **Adoptada** |

Definición propuesta, junto a `make_standard_link_data_full` (tras la línea 296):

```
def make_standard_cta(value, valid=ABSENT):
    """Construye un ``call_to_action`` en la forma canónica anidada
    ``{'type': {'value': <value>, 'valid': <valid>}}`` que produce
    ``FacebookSavePreCheckCTAsUseCase._validate_ctas_standard`` y que leen
    ``_validate_standard_cta`` (``['type']['value']``) y
    ``_build_standard_creative_entry`` (``['type']['valid']``).

    ``valid`` por defecto es el centinela ``ABSENT``: la clave se omite, de modo
    que el helper sirve tanto para entradas previas a la validación (sin anotar)
    como para entradas ya anotadas.
    """
```

**Cambios sitio por sitio:**

- **B1** (3720): `call_to_action={"type": cta_text}` → `call_to_action=make_standard_cta(cta_text)`.
  La aserción `mock_validate_cta_for_goal.assert_called_once_with(cta_text=cta_text, ...)` se
  conserva sin cambios: `_validate_standard_cta` extrae `['type']['value']`, que sigue siendo
  `cta_text`. La aserción `link_data["call_to_action"]["valid"] == valid` también se conserva: la
  anotación se escribe en la raíz del CTA, no dentro de `type`. La estrategia
  `cta_text=st.text(min_size=1)` no cambia.
- **B2** (3750) y **B3** (3777): `{"type": "LEARN_MORE"}` → `make_standard_cta("LEARN_MORE")`.
  Aserciones intactas.
- **B4** (4015), dentro de `_run_full_standard_validation`: ídem. La aserción
  `link_data["call_to_action"]["valid"] == cta_valid` (4099) queda intacta.
- **B5–B8**: dos sitios.
  - `make_standard_link_data_full` (292): `call_to_action={"type": "LEARN_MORE"}` →
    `call_to_action=make_standard_cta("LEARN_MORE")`. El helper es de uso exclusivo de
    `TestStandardCombinationSuccessScenarios` (única invocación real en 4390), por lo que el cambio
    no tiene radio de acción fuera del grupo B. Su docstring (líneas 266–296) debe actualizarse para
    describir la forma anidada.
  - `_run_success_scenario` (4381): `{"type": "WHATSAPP_MESSAGE"}` →
    `make_standard_cta("WHATSAPP_MESSAGE")`.
  - Las siete aserciones de éxito existentes (4468–4474) pasan con la forma anidada sin más
    cambios, porque la séptima asevera `link_data["call_to_action"]["valid"] is True`, que
    `_validate_standard_cta` escribe en la **raíz** del CTA, no dentro de `type`.
  - Cláusula 2.4 pide además que la anotación `call_to_action_types_valid_amount` se lea desde
    `call_to_action['type']['valid']` conforme a `_build_standard_creative_entry`. Ese valor no lo
    escribe `_validate_standard_cta` (anota en la raíz), sino que se hereda de la entrada, tal como
    la dejó el pre-check de CTAs en el flujo real. Para que la anotación se propague a `True`, la
    entrada debe llevar `valid=True` precargado dentro de `type`:
    `make_standard_cta("LEARN_MORE", valid=True)` y `make_standard_cta("WHATSAPP_MESSAGE", valid=True)`.
    La aserción correspondiente sobre
    `result["data"]["creatives"][0]["call_to_action_types_valid_amount"] is True` debe añadirse como
    aserción **nueva**, nunca como reemplazo de ninguna de las siete.
- **Sitio acoplado** (437), `_STANDARD_LINK_DATA_FIELD_STRATEGIES["call_to_action"]`:
  `st.one_of(st.none(), st.fixed_dictionaries({"type": st.text(max_size=20)}))` →
  `st.one_of(st.none(), st.fixed_dictionaries({"type": st.fixed_dictionaries({"value": st.text(max_size=20), "valid": st.booleans()})}))`.
  Este cambio no es exigido por ninguna cláusula 2.x, pero es **obligatorio** si se corrige el
  tercer argumento del nodo vacuo 4220 (ver R1) y en todo caso deja la estrategia coherente con la
  forma canónica. El nodo 4220 solo asevera el conjunto de claves y el `idx`, invariantes bajo
  ambas formas, así que el cambio es seguro por sí solo.

Los escenarios que construyen CTA falsy (3804: `None`, `{}`, `False`, `""`, `ABSENT`) y CTA truthy
no-`dict` (3850) **no se tocan**: caracterizan las dos excepciones documentadas de
`_validate_standard_cta` (retornos anticipados tras `if not cta:` en la línea 1350 y tras
`if not isinstance(cta, dict):` en la 1353), siguen pasando y su semántica es independiente de la
forma de `type`.

### Grupo C — Corrección del tercer argumento

`_build_standard_creative_entry` recibe `ad`, no `ad_creative`. Los tres nodos deben dejar de
extraer `ad_set_to_publish["ads"][0].get("adCreative")` y pasar directamente
`ad_set_to_publish["ads"][0]`.

**C1 — `test_object_story_spec_completely_absent_uses_every_documented_default` (4245).**

- Líneas 4276–4278: sustituir la extracción de `ad_creative` y la llamada por

  ```
  ad = ad_set_to_publish["ads"][0]
  assert "object_story_spec" not in ad["adCreative"]

  result = use_case._build_standard_creative_entry(0, ad_set_to_publish, ad)
  ```

  La aserción de precondición sobre la ausencia de `object_story_spec` se conserva, reexpresada
  sobre `ad["adCreative"]`.
- Expectativa de `name`: `"AdSet-Absent-OSS"` → `"AdSet-Absent-OSS - Ad"`. El sufijo es
  `ad.get('name')`, y `make_ad` (línea 151) usa `name="Ad"` por defecto;
  `_make_ad_set_to_publish` (4192) no lo sobreescribe. Alternativa igualmente válida y más
  explícita: pasar un `name` propio al `ad` y aseverar el string compuesto correspondiente. Se
  recomienda la primera opción (menor superficie de cambio) y dejar la expectativa escrita como
  literal `"AdSet-Absent-OSS - Ad"`, no como f-string, para que la prueba siga siendo una
  caracterización y no una tautología.
- Expectativa de `ad_id`: `"ad-absent-oss"` — el valor ya escrito en la prueba, que hoy falla
  porque llega `None`. No cambia.
- El resto del diccionario esperado (30 claves) queda intacto: `adchannel_id: 0`,
  `min_daily_budget: 0`, `proposal_url: ""`, los `*_max_amount: 1`, las colecciones vacías y los
  flags `False` son todos los mismos defaults, ahora alcanzados por la vía correcta
  (`ad.get('adCreative')` → `{"name": "Creative"}` → `object_story_spec` ausente → `{}`).
- El docstring (4249–4266) debe actualizarse: la frase «`ad_id` from its single ad» sigue siendo
  correcta, pero la afirmación de que `name` viene de `ad_set_to_publish` «itself» deja de serlo.
- El docstring de clase (4115–4145) contiene una copia literal desfasada de la firma
  (`def _build_standard_creative_entry(self, idx, ad_set_to_publish, ad_creative)` y el cuerpo
  `ad_creative = ad_creative or {}`, `_as_single_item_list(value)` con un solo parámetro). Debe
  reemplazarse por el código vigente de las líneas 1442–1461, incluida la línea
  `ad_creative = ad.get('adCreative') or {}` y la composición de `name`.

**C2–C3 — `test_build_standard_creative_entry_distinguishes_explicit_none_from_absent_key` (6077).**

- Líneas 6098–6102: sustituir por

  ```
  ad = ad_set_to_publish["ads"][0]

  result = use_case._build_standard_creative_entry(0, ad_set_to_publish, ad)
  ```

- La tabla de `parametrize` (6066–6076) no cambia: `explicit-none → None`, `absent-key → 0`,
  `positive-integer → 42`. El nodo `absent-key` pasa hoy por degeneración y tras el cambio pasa por
  la razón correcta (`object_story_spec.get('ad_channel_id', 0)` con la clave genuinamente ausente).
  Los `ids=` se conservan, por lo que los tres IDs de nodo permanecen estables.
- El docstring de clase (5975–6014) contiene la misma copia desfasada de la firma en la línea 5991.
  Debe actualizarse.
- El caso hermano `test_save_creative_to_publish_distinguishes_explicit_none_from_absent_key`
  (6040) **no se toca**: ejercita `_save_creative_to_publish`, cuya firma no cambió.

### Grupo D — Conversión estricta de `meta_campaign_mode`

**D3–D10: las 8 pruebas de `TestUnknownMetaCampaignMode` pasan a aseverar la excepción.**

Punto exacto del fallo: `_set_creative_type(campaign_setup)` se invoca **después** de
`_get_ad_channel` / `_set_channel_id` / `_get_campaign_setup` y **antes** del bloque `try` de
validación (imágenes: líneas 2632–2638; textos: 2673–2679). Por tanto, en el momento del
`ValueError` ya ocurrió la lectura de ambos repositorios y no ocurrió nada más.

Reescritura propuesta (idéntica en ambos archivos, salvo los validadores parcheados):

1. **Construcción de la entrada: sin cambios.** Se conservan el `asset_feed` y el `story_spec`
   truthy simultáneos, el `titles` preexistente distinto de `self.titles` (textos), los snapshots
   `dict(asset_feed)` / `dict(object_story_spec)` y la construcción manual
   `campaign_setup = {"attributes": {}}` para el escenario de clave ausente. Esa entrada sigue
   siendo la que hace las aserciones de no-mutación no vacuas.
2. **Invocación:** `result = use_case.execute()` → 

   ```
   with pytest.raises(ValueError) as exc_info:
       use_case.execute()
   ```

   y se elimina la variable `result` junto con `assert result is build_response_result`, que deja de
   tener sentido. `mock_build_response.return_value` puede conservarse (inocuo) o eliminarse; se
   recomienda eliminarlo para que la prueba no sugiera que `_build_response` se alcanza.
3. **Aserción del mensaje:** `assert str(exc_info.value) == "<mensaje>"`, con el mensaje derivado
   del escenario. Verificados en este entorno:
   `""` → `"'' is not a valid CreativeType"`; `None` → `"None is not a valid CreativeType"`;
   `"SOME_OTHER_MODE"` → `"'SOME_OTHER_MODE' is not a valid CreativeType"`; clave ausente → el
   mismo mensaje que `None`. Se recomienda añadir el mensaje esperado como tercer elemento de cada
   tupla / `pytest.param`, en lugar de recalcularlo en el cuerpo, para que la tabla de
   parametrización siga siendo la única fuente de verdad del escenario.
4. **Aserciones de no-invocación (cláusula 2.7):**
   - Imágenes: `mock_validate_images_dynamic.assert_not_called()` y
     `mock_validate_images_standard.assert_not_called()` se conservan tal cual.
   - Textos: `assert_no_text_validator_calls(mock_is_unique_texts, mock_is_valid_length, mock_is_valid_texts_amount)`
     se conserva tal cual.
   - Se añade `mock_save_creative_to_publish.assert_not_called()` y
     `mock_build_response.assert_not_called()` (reemplazando las dos
     `assert_called_once_with(creative)` y las dos aserciones de identidad).
   - Se añade `mock_ad_channel_repo_instance.update.assert_not_called()`, que es la aserción que la
     cláusula 2.7 nombra explícitamente y que no depende del parcheo de
     `_save_creative_to_publish`. Mantener **ambas** da la garantía más fuerte a costa de una línea.
5. **Aserciones de no-mutación:** `assert asset_feed == asset_feed_before` y
   `assert story_spec == story_spec_before` (imágenes) / los dos `== *_snapshot` (textos) se
   conservan sin cambios.
6. **Aserción adicional recomendada de estado:** `assert use_case.creative_type == ""`.
   `CreativeType(...)` lanza antes de la asignación, así que `creative_type` conserva el valor con
   que lo dejó el constructor (`FacebookSavePreCheckBaseUseCase.__init__` delega con
   `complete_campaign_data={}` y `creative_type` por defecto `''`). Documenta que el fallo no deja
   la instancia en un estado intermedio.

**Renombrado de clase y de casos (cláusula 2.9).** «Unknown» ya no describe tolerancia; el nombre
debe decir que el modo inválido aborta. Propuesta, idéntica en ambos archivos para que la simetría
entre suites hermanas se mantenga:

| Archivo | Identificador actual | Propuesto |
|---|---|---|
| imágenes (2123) | `class TestUnknownMetaCampaignMode` | `class TestUnsupportedMetaCampaignModeRaisesValueError` |
| textos (3455) | `class TestUnknownMetaCampaignMode` | `class TestUnsupportedMetaCampaignModeRaisesValueError` |
| imágenes (2158) | `test_execute_invokes_neither_branch_and_continues_without_mutation` | `test_execute_propagates_value_error_before_invoking_either_branch_or_mutating` |
| textos (3498) | `test_no_validator_calls_and_no_mutation_regardless_of_truthy_asset_feed_and_story_spec` | `test_execute_propagates_value_error_with_no_validator_calls_and_no_mutation_regardless_of_truthy_asset_feed_and_story_spec` |

Los docstrings de clase (imágenes 2123–2145; textos 3455–3479) describen hoy el mecanismo obsoleto
(«ambas comparaciones `elif` fallan, así que ningún cuerpo se ejecuta»). Deben reescribirse en
torno a `_set_creative_type` y su conversión estricta, señalando que el aborto ocurre **antes** de
que las comparaciones `== CreativeType.DYNAMIC.value` / `== CreativeType.STANDARD.value` lleguen a
evaluarse, y que por eso la truthiness simultánea de `asset_feed`/`story_spec` sigue siendo
relevante como control de que nada corrió.

Para el archivo de imágenes se recomienda además añadir `ids=` explícitos al `parametrize`
(2145–2156), que hoy produce IDs ruidosos del tipo `[meta_campaign_mode_empty_string-campaign_setup_kwargs0]`.
Los cuatro nodos afectados están todos dentro de los 44, así que el cambio de IDs no puede romper
ninguna preservación. Es opcional y debe hacerse en el mismo commit que el renombrado, nunca
después.

**D1–D2: los dos casos de orden de operaciones.**

Ambos usan `make_campaign_setup(meta_campaign_mode=None)` únicamente como atajo para neutralizar la
rama de validación sin parchear `MetaAdsValidator`. El atajo dejó de funcionar porque el modo
inválido ahora aborta antes.

**Medio de neutralización elegido: modo válido `"DYNAMIC"` con `asset_feed` genuinamente ausente.**

Verificado contra el código real:

- `make_campaign_setup()` ya tiene `meta_campaign_mode="DYNAMIC"` por defecto (imágenes 136, textos
  121), así que el cambio es literalmente `make_campaign_setup(meta_campaign_mode=None)` →
  `make_campaign_setup()`.
- `make_creative()` —que ambas pruebas ya usan sin argumentos— construye
  `ads=[make_ad()]`, y `make_ad()` deja `adCreative` **ausente** (centinela `ABSENT`). Por tanto
  `creative.get('ads', [])[0].get('adCreative', {})` devuelve `{}` y tanto `asset_feed` como
  `story_spec` son `None`.
- La guarda de la rama DYNAMIC es `if mode == CreativeType.DYNAMIC.value and asset_feed:`. Con
  `asset_feed = None` el operando derecho es falsy, el cuerpo no corre, y el `elif` STANDARD
  tampoco (el modo no es `"STANDARD"`). El bloque `try` completo es un no-op sin excepción.
- `_set_creative_type` tiene éxito y asigna `self.creative_type = "DYNAMIC"`.
- La secuencia observable sobre `manager.mock_calls` se mantiene exactamente
  `_get_decoded_access_token`, `_get_ad_channel`, `_set_channel_id`, `_get_campaign_setup`,
  `_save_creative_to_publish`, `_build_response`. `_set_creative_type` **no** está atado al manager
  y no es un mock, así que no aparece en `mock_calls` y `expected_call_order` no cambia. Las
  aserciones `mock_save_creative_to_publish.assert_called_once_with(creative)`,
  `mock_build_response.assert_called_once_with(creative)` y
  `assert result is build_response_result` quedan intactas.

Alternativas descartadas: parchear `_validate_images_standard`/`_validate_images_dynamic` en la
instancia (añade dos mocks que no aportan nada y no son atables al manager sin alterar
`expected_call_order`), y parchear `MetaAdsValidator` a nivel de clase (es exactamente lo que el
docstring original decía querer evitar).

Los docstrings (imágenes 1211, textos 1256) que dicen
«`_get_campaign_setup` is patched to return `make_campaign_setup(meta_campaign_mode=None)` so the
conditional validation block is a no-op» deben reescribirse: el no-op ahora proviene de un
`asset_feed` ausente bajo un modo válido, no de un modo desconocido. Se recomienda que el nuevo
texto haga explícita la razón (`make_ad()` omite `adCreative`), porque es una dependencia sutil del
default de un builder compartido.

### Trazabilidad de las cláusulas de Expected Behavior

| Cláusula | Parte del diseño que la satisface |
|---|---|
| 2.1 | Grupo A, cambio de aserción en los sitios 1462, 1612, 1711, 1902, 1965, 2069, 2133, 2186, 2255, 2400 (18 nodos). La preservación de «todas las demás aserciones» está explicitada en el foco 3 de docstrings del grupo A, que conserva la línea 1555 |
| 2.2 | Grupo A, cambio de aserción en los sitios 4684, 4842, 4992, 5018, 5917 (5 nodos); `status_code == 200` y las aserciones sobre `data["creatives"]` se dejan intactas por construcción |
| 2.3 | Grupo B, sitios B1–B4 (3720, 3750, 3777, 4015) con `make_standard_cta`; la aserción de que la validez se escribe en `call_to_action['valid']` (raíz) se conserva tal como está |
| 2.4 | Grupo B, sitios B5–B8 (292 y 4381) con `make_standard_cta(..., valid=True)`; la lectura de `call_to_action['type']['valid']` queda justificada en el bullet de la cláusula 2.4 |
| 2.5 | Grupo C, caso C1: tercer argumento `ad`, `name` esperado `"AdSet-Absent-OSS - Ad"`, comparación completa del diccionario preservada |
| 2.6 | Grupo C, casos C2–C3: tercer argumento `ad`; tabla de `parametrize` intacta con `None` / `0` / `42` |
| 2.7 | Grupo D, pasos 2–6 de la reescritura de las 8 pruebas: `pytest.raises(ValueError)`, no-invocación de validadores, `ad_channel_repository.update` y `_build_response`, y no-mutación de `asset_feed_spec`/`object_story_spec` |
| 2.8 | Grupo D, D1–D2: `make_campaign_setup()` con modo `"DYNAMIC"` válido, neutralización por `asset_feed` ausente vía el default de `make_ad()`, `expected_call_order` sin cambios |
| 2.9 | Grupo A, tabla de 10 renombrados con criterio `ok_zero` → `ok_1`; Grupo D, tabla de renombrado de las dos clases `TestUnknownMetaCampaignMode` y sus dos casos |
| 2.10 | Grupo A, focos 1–3 de docstrings (4859, 1680, 1497/1605); Grupo B, docstring de `make_standard_link_data_full` (266–296) y de `TestStandardCtaValidation` (copia desfasada de `cta.get('type')` en 3628); Grupo C, docstrings de clase 4115–4145 (firma antigua en 4117, `_as_single_item_list(value)` en 4125) y 5975–6014 (firma antigua en 5991); Grupo D, docstrings de clase 2123–2145 y 3455–3479 y de caso 1211/1256 |
| 2.11 | Plan de verificación, pasos V3 y V4 |
| 2.12 | Plan de verificación, paso V5 (`git diff --stat -- app/`); ninguna instrucción de este diseño toca `sinergia/app/` |
| 2.13 | Riesgo R1 y su mitigación: el único hallazgo con potencial de requerir cambio productivo se resuelve sin tocarlo; si apareciera otro, la regla es escalar, nunca `xfail`/`skip`/borrar |

### Trazabilidad de las condiciones de preservación

| Condición | Mecanismo de verificación |
|---|---|
| 3.1 | V4: ejecución de la suite completa y comparación del recuento `1676 passed` / `0 failed` contra el baseline `1632 passed` + los 44 realineados |
| 3.2 | V2 + V6: comparación nodo por nodo del reporte por-nodo de baseline contra el posterior, restringida a los tres archivos objetivo; los 283 nodos que no están en la lista de 44 deben mantener `PASSED` |
| 3.3 | V6, filtrado por los nodos de `TestExecuteDynamicBranch`, `TestValidateImagesDynamic`, `TestDynamicBranch*`, `TestStandardSpecDoesNotRegressDynamicBranch`. Refuerzo de diseño: el grupo B introduce un helper nuevo en lugar de tocar `make_link_data`, y ningún cambio altera `make_asset_feed_spec` |
| 3.4 | Decisión explícita del grupo B de no modificar `make_link_data`, `make_object_story_spec`, `make_ad`, `make_ad_set`, `make_ad_creative`, `make_campaign_setup`, `make_creative`, `make_ad_channel`, `use_case_factory`, `patch_redis_client` ni `ABSENT`. Los dos únicos helpers que cambian son `make_standard_link_data_full` (consumidor único, el propio grupo B) y `_STANDARD_LINK_DATA_FIELD_STRATEGIES` (consumidor único, `standard_object_story_spec_shapes`). Verificación: V6 más una revisión de `git diff` que confirme que ninguna definición de builder compartido aparece en el diff |
| 3.5 | La fixture `_deny_real_network_requests` (`autouse`, línea 661) permanece intacta; ningún cambio de este diseño añade patches nuevos de red ni quita los existentes. Verificación: V4 no reporta errores de red y V6 no muestra nodos nuevos en `error` |
| 3.6 | V6 sobre `TestExecutePersistenceSideEffects` (5021) y sobre las aserciones de identidad de D1–D2, que se conservan literalmente |
| 3.7 | `STANDARD_SUPPORTED_COMBINATIONS` (línea 232) y `STANDARD_SUPPORTED_COMBINATIONS_IDS` (línea 249) se derivan mecánicamente de la constante productiva y no se tocan. Verificación: los cuatro IDs de nodo `[awareness-reach]`, `[leads-conversations]`, `[leads-lead-generation]`, `[sales-offsite-conversions]` siguen apareciendo, ni uno más ni uno menos |
| 3.8 | V4 registra la duración; se compara contra el baseline (74,99 s medidos para los tres archivos). Ningún cambio de este diseño introduce `time.sleep`, reintentos ni entrada/salida real; el único cambio de estrategia de Hypothesis (sitio 437) anida un `fixed_dictionaries` sin ampliar `max_examples` |

## Testing Strategy

### Validation Approach

No hay fase exploratoria que construir: los contraejemplos ya existen y son los 44 fallos, con
causa raíz confirmada contra el código productivo leído en esta fase. La validación se reduce a dos
comprobaciones sobre la suite, con un baseline capturado antes de cualquier edición.

### Exploratory Bug Condition Checking

**Estado: completado en esta fase.** Los contraejemplos observados sobre el código sin arreglar son:

- `AssertionError: assert 1 == 0` en los 23 nodos del grupo A.
- `AttributeError: 'str' object has no attribute 'get'` lanzado desde
  `app/v2/use_cases/meta_ads.py:1360` (`_validate_standard_cta`) en los 8 nodos del grupo B (los 4 de
  B5–B8 lo alcanzan a través de `execute()` → `_validate_standard_creative`).
- `AssertionError` sobre la comparación de diccionario y `assert 0 == None` / `assert 0 == 42` en
  los 3 nodos del grupo C.
- `ValueError: <valor> is not a valid CreativeType` lanzado desde
  `app/v2/use_cases/meta_ads.py:2493` (`_set_creative_type`) en los 10 nodos del grupo D.

Confirmación adicional obtenida invocando `_build_standard_creative_entry` directamente con ambas
formas de CTA, que estableció la forma canónica anidada y reveló el nodo vacuo de la línea 4220.
Las cuatro hipótesis quedan confirmadas; no hace falta re-hipotetizar.

### Fix Checking

**Objetivo:** para todo nodo donde la condición de bug se cumple, la suite realineada pasa.

**Pseudocódigo:**

```
FOR ALL X WHERE isBugCondition(X) DO
  result := runTest(F', X)
  ASSERT expectedBehavior(result)
END FOR
```

Implementación concreta: los 44 nodos son un conjunto finito y enumerado (tablas de Localización),
así que la comprobación es exhaustiva por ejecución directa, no muestreada. Se ejecutan los tres
archivos completos y se exige `0 failed`, más la verificación de que el número total de nodos
recolectados no bajó (ningún caso fue eliminado) y que ninguno quedó en `skipped`/`xfail`.

### Preservation Checking

**Objetivo:** para todo nodo donde la condición de bug NO se cumple, el resultado es idéntico antes
y después.

**Pseudocódigo:**

```
FOR ALL X WHERE NOT isBugCondition(X) DO
  ASSERT runTest(F, X).outcome = runTest(F', X).outcome
END FOR
```

**Enfoque de comprobación.** Aquí no se usan pruebas basadas en propiedades sobre el dominio de
entradas: el dominio relevante es el conjunto **finito y enumerable** de nodos de pytest de la
suite, así que la comparación exhaustiva nodo por nodo es estrictamente más fuerte que cualquier
muestreo y no cuesta más. La técnica es diferencial: se captura el reporte por-nodo de `F`, se
aplica el arreglo, se captura el reporte por-nodo de `F'` y se comparan los dos conjuntos
`(nodeid, outcome)`. La única diferencia admisible es que los 44 nodos de la lista pasen de
`failed` a `passed`, con los renombrados aplicados.

**Plan de captura del baseline (antes de tocar nada):**

```
# V1 — baseline por nodo de los tres archivos objetivo
venv/bin/python -m pytest \
  tests/v2/unit/use_cases/test_facebook_generate_pre_check_creative.py \
  tests/v2/unit/use_cases/test_facebook_save_pre_check_images.py \
  tests/v2/unit/use_cases/test_facebook_save_pre_check_texts.py \
  -q --no-header -rA --tb=no > /tmp/baseline-target.txt

# V2 — baseline por nodo de la suite completa
venv/bin/python -m pytest -q --no-header -rA --tb=no > /tmp/baseline-full.txt
```

`-rA` emite una línea `PASSED`/`FAILED`/`SKIPPED`/`XFAIL` por nodo en el *short test summary info*,
que es el insumo de la comparación. Ambos archivos se guardan fuera del repositorio (`/tmp`) para no
introducir artefactos nuevos en el árbol; si se prefiere conservarlos, deben ir a un directorio
ignorado por git, nunca dentro de `sinergia/app/` ni del directorio del spec.

**Casos de preservación de mayor riesgo, a revisar explícitamente en la comparación:**

1. `TestStandardCreativesEntry::test_property_construction_never_raises_and_always_returns_the_fixed_key_set`
   (4220): pasa hoy de forma vacua; es el nodo con más probabilidad de voltear a `failed` si el
   grupo C se aplica sin el grupo B.
2. `TestStandardCtaValidation::test_cta_absent_scenario` (5 nodos) y `test_cta_non_dict_scenario`
   (línea 3850): comparten el `link_data` construido por `make_link_data`, que no se toca.
3. `TestExecuteStandardAdChannelIdReading::test_save_creative_to_publish_distinguishes_explicit_none_from_absent_key`
   (3 nodos): comparte `_make_ad_set_to_publish` indirectamente vía `_make_standard_creative`.
4. Los 15 nodos que ya aseveran `ok == 1` en el mismo archivo (líneas 1555, 2454, 4466, 4633, 4656,
   4758, 4966, 5387, 5461, 5526, 5582, 5658, 5779, 5964): deben seguir pasando sin haber sido
   tocados.
5. `TestExecuteOrchestration` / `TestExecuteOrchestrationAndShortCircuit`: los demás casos de esas
   clases (token faltante, `DataNotFoundException`, identidad del `creative`) comparten
   `make_campaign_setup`, cuyo default no cambia.

### Plan de verificación

| Paso | Acción | Criterio de aceptación |
|---|---|---|
| V1 | Capturar baseline por nodo de los tres archivos (comando arriba) | El archivo registra `44 failed, 283 passed` y contiene una línea por nodo |
| V2 | Capturar baseline por nodo de la suite completa | El archivo registra `44 failed, 1632 passed` |
| V3 | Tras cada grupo, ejecutar solo el archivo tocado, p. ej. `venv/bin/python -m pytest tests/v2/unit/use_cases/test_facebook_generate_pre_check_creative.py -q --no-header` | `0 failed` para los nodos del grupo ya aplicado y ningún fallo nuevo |
| V4 | Ejecución focalizada final de los tres archivos, y luego de la suite completa | `0 failed, 327 passed` en los tres archivos; `0 failed, 1676 passed` en la suite completa; duración de los tres archivos en el orden de 75–95 s |
| V5 | `git diff --stat -- app/` desde `sinergia/` | Salida vacía. Refuerzo: `git status --porcelain -- app/` devuelve exactamente la misma línea que ya devolvía antes de empezar (hoy, el único no rastreado preexistente es `sinergia/app/v2/resources/audience.py`, ajeno a este bugfix), sin entradas nuevas. Conviene capturar esa salida junto al baseline en V1 para poder comparar |
| V6 | Comparación diferencial nodo por nodo del `-rA` posterior contra el baseline | El conjunto de diferencias es exactamente los 44 nodos (con sus nombres nuevos donde se renombraron). Ningún nodo pasa de `PASSED` a otro estado |
| V7 | Detección de `skipped`/`xfail` encubiertos | La línea de resumen no contiene `skipped`, `xfailed`, `xpassed` ni `error`. Verificación cruzada: el recuento de nodos recolectados (`--collect-only -q \| tail -1`) para los tres archivos es igual antes y después (327) |
| V8 | Revisión del diff de builders compartidos | `git diff` no muestra cambios en las definiciones de `make_link_data`, `make_object_story_spec`, `make_ad`, `make_ad_set`, `make_ad_creative`, `make_campaign_setup`, `make_creative`, `make_ad_channel`, `use_case_factory`, `patch_redis_client` ni `_AbsentSentinel`/`ABSENT` |

Comandos exactos, siempre desde el directorio `sinergia/`:

```
# Focalizado por archivo
venv/bin/python -m pytest tests/v2/unit/use_cases/test_facebook_generate_pre_check_creative.py -q --no-header
venv/bin/python -m pytest tests/v2/unit/use_cases/test_facebook_save_pre_check_images.py -q --no-header
venv/bin/python -m pytest tests/v2/unit/use_cases/test_facebook_save_pre_check_texts.py -q --no-header

# Los tres juntos
venv/bin/python -m pytest \
  tests/v2/unit/use_cases/test_facebook_generate_pre_check_creative.py \
  tests/v2/unit/use_cases/test_facebook_save_pre_check_images.py \
  tests/v2/unit/use_cases/test_facebook_save_pre_check_texts.py -q --no-header

# Suite completa
venv/bin/python -m pytest -q --no-header

# Recuento de nodos recolectados (V7)
venv/bin/python -m pytest \
  tests/v2/unit/use_cases/test_facebook_generate_pre_check_creative.py \
  tests/v2/unit/use_cases/test_facebook_save_pre_check_images.py \
  tests/v2/unit/use_cases/test_facebook_save_pre_check_texts.py --collect-only -q | tail -1

# Código productivo intacto (V5)
git diff --stat -- app/
git status --porcelain -- app/
```

No hay `pytest.ini` ni `setup.cfg` en `sinergia/`, y `pytest-randomly` no está instalado, así que el
orden de recolección es determinista y no hacen falta banderas extra. Entorno confirmado:
pytest 8.3.5, hypothesis 6.112.2, Python 3.8.10 en `venv/`.

### Unit Tests

- Los 23 nodos del grupo A, realineados a `ok == 1`, siguen siendo pruebas de caracterización de
  `execute()` a nivel de unidad con todos los colaboradores (`MetaAdsValidator`,
  `FacebookGetAdAccountDetailsUseCase`, `FacebookMinimumBudgetUseCase`, `redis_client`,
  repositorios) parcheados.
- Los 4 nodos B1–B4 y los 3 del grupo C siguen ejercitando métodos privados en aislamiento
  (`_validate_standard_cta`, `_validate_standard_creative`, `_build_standard_creative_entry`), que es
  la convención ya establecida en el archivo.
- Los 8 nodos D3–D10 pasan a ser pruebas de propagación de excepción más no-efecto, la forma
  estándar de caracterizar una guarda que aborta.
- Los 2 nodos D1–D2 siguen siendo pruebas de orden de operaciones con el patrón *manager mock*.

### Property-Based Tests

Tres nodos de Hypothesis están involucrados y ninguno cambia de estrategia salvo en la forma del
CTA:

- B1, `test_property_annotation_mirrors_validate_cta_for_goal_result` (Property 4): conserva
  `cta_text=st.text(min_size=1)` y `valid=st.booleans()`, 100 ejemplos. Solo cambia la envoltura del
  `cta_text` en la forma anidada.
- B4, `test_property_combined_annotation_contract_holds_independently_per_field` (Property 5):
  conserva las 7 estrategias booleanas independientes, 100 ejemplos. Solo cambia el CTA del
  `link_data` de entrada.
- Nodo acoplado, `test_property_construction_never_raises_and_always_returns_the_fixed_key_set`
  (Property 8): su generador `standard_object_story_spec_shapes` pasa a producir CTA anidado. No
  requiere cambio de aserciones.

No se añaden propiedades nuevas: el arreglo no introduce comportamiento nuevo que validar, y las dos
propiedades de este bugfix (Fix Checking y Preservation Checking) se comprueban de forma exhaustiva
sobre un dominio finito, no muestreada.

### Integration Tests

No aplica. Este bugfix no toca código productivo ni ningún límite de integración; el alcance está
confinado a tres archivos de pruebas unitarias. La ejecución de la suite completa (V4) cumple el rol
de comprobación de extremo a extremo de que el realineamiento no tuvo efectos colaterales en las
otras 11 suites del directorio.

## Riesgos y mitigaciones

**R1 — El nodo vacuo de Property 8 se rompe al corregir el grupo C (severidad: alta).**
`test_property_construction_never_raises_and_always_returns_the_fixed_key_set` (4220) pasa hoy
porque su entrada degenera. Si se corrige el tercer argumento sin migrar
`_STANDARD_LINK_DATA_FIELD_STRATEGIES["call_to_action"]` (437) a la forma anidada, el nodo empieza a
ejercitar las formas generadas y falla con `AttributeError`, violando la preservación 3.2 e
introduciendo un fallo nuevo.
*Mitigación:* aplicar el grupo B antes del grupo C, incluyendo el cambio del sitio 437, y ejecutar
`TestStandardCreativesEntry` completo entre ambos grupos. Decisión: se corrige el tercer argumento
de ese nodo también, con lo que deja de ser vacuo. Si tras la migración de la estrategia el nodo
fallara por una causa distinta de la forma del CTA, aplica la cláusula 2.13: se escala al usuario en
lugar de marcarlo `xfail` o revertir el argumento a `ad_creative`.

**R2 — Tocar un helper compartido rompe parte de los 283 nodos que pasan (severidad: alta).**
`make_link_data` y `make_object_story_spec` tienen decenas de consumidores, incluidos los nodos que
caracterizan CTA ausente, CTA falsy y CTA no-`dict`, cuya semántica depende de que el default siga
siendo `call_to_action=None`.
*Mitigación:* ningún builder compartido se modifica. La forma anidada se centraliza en un helper
**nuevo** (`make_standard_cta`) y se inyecta por sitio de llamada. Los dos helpers que sí cambian
tienen consumidor único y verificable por grep: `make_standard_link_data_full` (solo 4390) y
`_STANDARD_LINK_DATA_FIELD_STRATEGIES` (solo `standard_object_story_spec_shapes`). Verificación V8.

**R3 — Docstrings con copias literales de código productivo desfasado (severidad: media).**
La suite embebe fragmentos de `meta_ads.py` en docstrings de clase. Seis copias están desfasadas y
son activamente engañosas: 4859 (`"ok": 0 if has_errors else 1`), 4117 y 5991 (firma antigua de
`_build_standard_creative_entry` y, en 4125, `_as_single_item_list(value)` con un solo parámetro
cuando el real tiene dos), 3628 (`cta_text = cta.get('type')` sin el `.get('value')`), y los
docstrings de clase de los dos
`TestUnknownMetaCampaignMode`, que describen un mecanismo de tolerancia inexistente. Además, tres
docstrings de caso (1211, 1256, 1497) documentan un atajo que dejó de funcionar.
*Mitigación:* cada grupo lleva su lista explícita de docstrings a actualizar (ver la fila 2.10 de la
tabla de trazabilidad). Regla operativa: al tocar un caso, releer el código productivo citado en su
docstring y en el de su clase, y actualizar la cita en el mismo commit. Los docstrings no se
verifican automáticamente, así que deben revisarse en el diff antes de cerrar cada grupo.

**R4 — Renombrados que rompen referencias o parametrizaciones (severidad: media).**
Los renombrados afectan nombres de método y de clase. `TestStandardCreativesEntry._make_ad_set_to_publish`
se referencia por nombre de clase desde otra clase (línea 6095), y `TestStandardCreativesEntry.EXPECTED_KEYS`
se usa vía `self`. Los `ids=` de `parametrize` son literales y no derivan de los nombres de caso,
salvo `STANDARD_SUPPORTED_COMBINATIONS_IDS`, que se deriva de la constante productiva.
*Mitigación:* ninguna clase del grupo A se renombra, así que la referencia cruzada 6095 no se toca.
Las dos clases que sí se renombran (`TestUnknownMetaCampaignMode` en ambos archivos) no son
referenciadas desde ningún otro punto: verificar con
`grep -rn "TestUnknownMetaCampaignMode" tests/` antes de renombrar y confirmar que las únicas
apariciones son las dos definiciones. Tras cada renombrado, contrastar el recuento de
`--collect-only -q` (V7) para descartar que un nombre duplicado haya hecho que un caso sombree a
otro dentro de la misma clase.

**R5 — Un renombrado deja huérfanas las referencias cruzadas en docstrings (severidad: baja).**
Varios docstrings citan otros casos por nombre (p. ej. la referencia a
`test_min_daily_budget_and_daily_budget_valid_assigned_when_daily_budget_comparable` en la línea
258, o las referencias a `TestStandardBranchNoOp` y `TestDynamicBranchMissingAssetFeed` en los
docstrings del grupo D).
*Mitigación:* tras aplicar los 14 renombrados (10 casos del grupo A + 2 clases y 2 casos del grupo
D), hacer un `grep` de cada nombre antiguo en los tres archivos y confirmar cero apariciones
residuales.

**R6 — La comprobación de aislamiento de A2 pierde poder discriminante (severidad: baja).**
`assert isolated_result["ok"] == 1` en la línea 1555 dejará de distinguir entre el escenario aislado
y el combinado.
*Mitigación:* se conserva la aserción (cláusula 2.1) y se reescribe el texto que la justificaba para
apoyarse en la evidencia que sigue siendo válida (`call_count == 6` y las mutaciones de
`asset_feed_after`). Se documenta como redundancia consciente, no como defecto.

**R7 — Falsa sensación de éxito por conteo agregado (severidad: baja).**
`0 failed, 1676 passed` se puede alcanzar también borrando o silenciando casos.
*Mitigación:* V6 (comparación nodo por nodo) y V7 (recuento de nodos recolectados y ausencia de
`skipped`/`xfailed` en la línea de resumen) hacen que el conteo agregado no sea suficiente por sí
solo.

## Orden de ejecución recomendado

El orden está determinado por el acoplamiento (B antes de C, obligatorio) y por el riesgo creciente
(primero lo mecánico y aislado, después lo semántico).

1. **V1 + V2 — Baseline.** Antes de editar una sola línea. Sin baseline no hay forma de demostrar la
   preservación nodo por nodo, y recapturarlo después ya no sirve.

2. **Grupo D (10 nodos, 2 archivos).** Primero porque está completamente desacoplado de los otros
   tres: vive en archivos distintos, no comparte helpers con el grupo B ni C, y su verificación es
   rápida (los dos archivos de `save_pre_check` corren en una fracción del tiempo total). Cierra 10
   de los 44 con riesgo de interferencia nulo y deja `test_facebook_save_pre_check_images.py` y
   `test_facebook_save_pre_check_texts.py` en verde para el resto del trabajo. Dentro del grupo:
   primero D1–D2 (un cambio de una línea cada uno, más docstring), luego D3–D10 (reescritura del
   cuerpo, renombrado de clase y caso).

3. **Grupo A (23 nodos, 1 archivo).** Es el más voluminoso pero el más mecánico: 15 aserciones
   `0` → `1`, 10 renombrados y 3 focos de docstring. No toca ningún helper ni ninguna firma, así que
   no puede interactuar con B ni con C. Hacerlo antes que B/C reduce el ruido del diff en los pasos
   siguientes: cuando se aplique B, el archivo ya estará mayoritariamente en verde y cualquier fallo
   nuevo será atribuible al cambio en curso.

4. **Grupo B (8 nodos + el sitio acoplado 437).** Introduce `make_standard_cta` y migra los 6 sitios
   de construcción de CTA más la estrategia de Hypothesis. Debe ir **antes** del grupo C (R1).
   Verificación intermedia obligatoria: ejecutar `TestStandardCtaValidation`,
   `TestStandardAnnotationContract`, `TestStandardCombinationSuccessScenarios` y
   `TestStandardCreativesEntry` y confirmar que el nodo 4220 sigue pasando con la estrategia nueva
   (todavía vacuo en este punto, porque el tercer argumento aún no se corrigió).

5. **Grupo C (3 nodos + el nodo vacuo 4220).** Último porque depende de B y porque es el cambio con
   más semántica por línea: corrige la firma en cuatro sitios de llamada, ajusta las expectativas de
   `name` y `ad_id`, y desvacúa el nodo de Property 8. Verificación inmediata sobre
   `TestStandardCreativesEntry` y `TestExecuteStandardAdChannelIdReading` completas, no solo sobre
   los tres nodos objetivo.

6. **V3 tras cada grupo, V4–V8 al final.** Un grupo no se considera cerrado hasta que su archivo
   corre sin fallos nuevos. El cierre global exige los cinco pasos finales, y en particular V6: el
   conteo agregado no basta.

Si en cualquier punto un nodo de los 283 preservados vuelca a `failed`, la regla es detenerse y
atribuir el fallo al grupo en curso antes de continuar, en lugar de acumular cambios. Si una
aserción obsoleta resulta imposible de realinear sin tocar `sinergia/app/`, aplica la cláusula 2.13:
se escala al usuario, sin `xfail`, sin `skip` y sin eliminar el caso.
