# Implementation Plan

## Overview

Plan para sincronizar las suites unitarias de Meta Ads (`test_facebook_get_launch_campaign_creatives.py` y `test_facebook_launch_campaign.py`) con el contrato introducido por HL-2671: bloque `campaign` de siete claves con `conversion_event`, lectura del atributo `meta_conversion_event` y `tracking_specs` con clave `"fb_pixel"`. Primero se exploran los 16 fallos actuales y se registra la línea base de preservación. Después se corrigen las expectativas de los tests y se verifica que toda la suite pasa sin regresiones.

## Tasks

- [x] 1. Ejecutar la exploración de la condición del bug sobre las suites sin corregir
  - **Property 1: Bug Condition** - Las suites afirman el contrato anterior a HL-2671
  - **CRÍTICO**: Las suites actuales DEBEN FALLAR. El fallo confirma que el bug existe
  - **NO intentar corregir los tests ni el código cuando fallen en este paso**
  - **NOTA**: Es un fix solo de tests. Aquí no se escribe ningún test nuevo: la exploración consiste en ejecutar las suites actuales, sin corregir, contra el código de producción sin modificar
  - **OBJETIVO**: Obtener contraejemplos que demuestren la condición del bug `isBugCondition(test)` del diseño: tests que esperan un bloque `campaign` de 6 claves sin `'conversion_event'`, conjuntos de atributos consultados sin `'meta_conversion_event'`, o `tracking_specs` con clave `"dataset"`
  - **Enfoque PBT acotado**: el bug es determinista. Se acota a los 16 casos concretos que fallan, más la propiedad Hypothesis de Property 14 (`TestLeadsOffsiteAdPayload::test_tracking_specs_only_for_leads_offsite`)
  - Desde `sinergia/`, ejecutar (nunca en modo watch): `venv/bin/python -m pytest tests/v2/unit/use_cases/test_facebook_get_launch_campaign_creatives.py tests/v2/unit/use_cases/test_facebook_launch_campaign.py -q`
  - **RESULTADO ESPERADO**: 16 failed, 969 passed. La lista de fallos coincide con bugfix.md 1.1–1.6
  - Documentar los contraejemplos observados:
    - Diff de dict con la clave extra `'conversion_event': None` (`TestResultComposition` y `TestCampaignBlock`)
    - `tuple(keys) != CAMPAIGN_BLOCK_KEYS` porque el resultado tiene 7 claves (`test_absent_setup_attributes_yield_none_in_the_three_keys`)
    - Diff de conjunto con `'meta_conversion_event'` de más (`test_meta_resources_is_never_read`, `test_meta_resources_is_never_read_end_to_end`)
    - Contraejemplo mínimo de Hypothesis `pixel='0'`: se esperaba `"dataset": ["0"]` y se obtiene `"fb_pixel": ["0"]`
    - `"dataset"` frente a `"fb_pixel"` con `"pixel-123"` en `test_happy_path_publishes_website_adset_and_tracked_ads[DYNAMIC|STANDARD]`
  - Confirmar que ningún contraejemplo apunta a un cambio de producción distinto de los commits `99a93414` y `7ef9a47d`
  - Marcar la tarea como completada cuando la ejecución esté hecha y los fallos documentados
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7_

- [x] 2. Registrar la línea base de preservación (ANTES de aplicar el fix)
  - **Property 2: Preservation** - Los tests no afectados y la producción no cambian
  - **IMPORTANTE**: Seguir la metodología de observar primero. Se observa el comportamiento de la suite sin corregir en los tests donde `isBugCondition` es falso
  - Desde `sinergia/`, guardar la lista de ids de las dos suites afectadas: `venv/bin/python -m pytest tests/v2/unit/use_cases/test_facebook_get_launch_campaign_creatives.py tests/v2/unit/use_cases/test_facebook_launch_campaign.py --co -q`. Guardarla en un archivo temporal fuera del repositorio (por ejemplo `/tmp`)
  - Ejecutar la suite unitaria completa desde `sinergia/` con `venv/bin/python -m pytest` y anotar la línea base: 2875 passed, 16 failed, 2891 en total
  - Observar y anotar que en la suite sin corregir siguen pasando:
    - La rama no Leads_Offsite de Property 14: sin `tracking_specs` y con `name`, `adset_id`, `creative`, `status` y `access_token` conservados (estrategia property-based con Hypothesis, `max_examples=100`, `deadline=None`, `suppress_health_check=[HealthCheck.function_scoped_fixture]`)
    - `TestSuiteSelfAudit`, `TestBuildersIndependence` y el resto de `TestLeadsOffsiteLaunchRollback` (adset WEBSITE, orden de llamadas y rollback)
    - Las aserciones sobre `'meta_resources'`: presente en el fixture y ausente de `consulted_keys`
  - Comprobar que `git status --porcelain sinergia/app/v2/` está vacío (estado de partida de producción)
  - **RESULTADO ESPERADO**: todos los tests fuera de la condición del bug PASAN sobre la suite sin corregir
  - Marcar la tarea como completada cuando la línea base esté registrada
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9_

- [x] 3. Fix para sincronizar las suites unitarias de Meta Ads con el contrato de HL-2671

  - [x] 3.1 Actualizar constantes y helpers de expectativa en `test_facebook_get_launch_campaign_creatives.py`
    - `CAMPAIGN_BLOCK_KEYS` (líneas 5078-5089): añadir `'conversion_event'` al final de la tupla y cambiar el comentario a "The seven keys of the ``campaign`` block..." (diseño, ítem 1)
    - `_expected_campaign_block` (líneas 5114-5133): añadir el parámetro `conversion_event=None` después de `mode` y la entrada `'conversion_event': conversion_event` al final del dict. Actualizar el docstring a siete claves (diseño, ítem 2)
    - `SETUP_ATTRIBUTES_READ_END_TO_END` (líneas 6544-6555): añadir `'meta_conversion_event'`. El comentario pasa a "seven attribute names" y menciona `meta_conversion_event` para la clave `conversion_event` (diseño, ítem 4)
    - Docstring de `make_campaign_setup` (líneas 552-556): enumerar los siete atributos leídos, incluido `meta_conversion_event`. Indicar que el fixture canónico no lo incluye (por eso el valor esperado es `None`) y que se inyecta con `**attribute_overrides`. La firma y el cuerpo no cambian (diseño, ítem 7)
    - _Bug_Condition: isBugCondition(test) donde test.expects(campaign_block_keys) = 6 claves sin 'conversion_event' o test.expects(consulted_setup_attributes) no contiene 'meta_conversion_event'_
    - _Expected_Behavior: Property 1 del diseño (bloque de siete claves en orden; `meta_conversion_event` entre los atributos leídos)_
    - _Preservation: `make_campaign_setup` mantiene firma y comportamiento; `TestBuildersIndependence` no se ve afectado_
    - _Requirements: 2.1, 2.2, 2.4, 2.7, 3.4, 3.8_

  - [x] 3.2 Corregir `TestResultComposition` en `test_facebook_get_launch_campaign_creatives.py`
    - Línea 5221: el comentario de sección pasa a `# -- The ``campaign`` block of seven keys (Requirement 7.3) ---`
    - Línea 5223: renombrar `test_campaign_block_equals_the_six_keys_derived_from_the_fixtures` → `test_campaign_block_equals_the_seven_keys_derived_from_the_fixtures`. El docstring pasa a "seven-key dict" y conserva su línea `Requirements: 7.3`
    - Línea 5240, `test_campaign_block_reflects_the_values_of_a_non_canonical_fixture`: pasar `meta_conversion_event='LEAD'` a `make_campaign_setup` y `conversion_event='LEAD'` a `_expected_campaign_block`. Añadir `assert result['campaign']['conversion_event'] == 'LEAD'`. El docstring menciona las cuatro claves del Campaign_Setup
    - Línea 5334: renombrar `test_absent_setup_attributes_yield_none_in_the_three_keys` → `test_absent_setup_attributes_yield_none_in_the_four_keys`. Añadir `assert result['campaign']['conversion_event'] is None`. El docstring dice "four keys" y "seven keys of the block" y conserva su línea `Requirements:`
    - Línea 5423, `test_meta_resources_is_never_read`: el conjunto esperado pasa a `{'meta_campaign_objective', 'meta_optimization_goal', 'meta_campaign_mode', 'meta_conversion_event', 'meta_account_id', 'meta_campaign_id'}`. El docstring pasa a "six attributes". La aserción sobre `'meta_resources'` no cambia
    - _Bug_Condition: isBugCondition(test) para los tests de `TestResultComposition` enumerados en 1.1, 1.2 y 1.3, y su documentación (1.7)_
    - _Expected_Behavior: Property 1 del diseño (igualdad exacta con siete claves; `conversion_event` = `meta_conversion_event` del Campaign_Setup o `None`)_
    - _Preservation: comparación por igualdad exacta de dict y orden; aserciones de `'meta_resources'`; clase, fixtures e intención de los tests renombrados_
    - _Requirements: 2.1, 2.2, 2.3, 2.7, 2.8, 2.9, 2.10, 3.3, 3.4, 3.10_

  - [x] 3.3 Corregir `TestCampaignBlock` y `TestMetaUrl` en `test_facebook_get_launch_campaign_creatives.py`
    - Línea 6565: el comentario de sección pasa a "Exact equality of the seven keys"
    - Línea 6567: renombrar `test_campaign_block_equals_the_six_keys_derived_from_the_fixtures` → `test_campaign_block_equals_the_seven_keys_derived_from_the_fixtures`. El docstring pasa a "seven-key dict" y se cambia `len(result['campaign']) == 6` por `== 7` (línea 6581). Conserva su línea `Requirements: 7.3, 11.8`
    - Línea 6588: en el docstring de `test_the_block_is_the_same_in_both_modes_except_for_the_mode_key`, "six keys" pasa a "seven keys". El nombre y los ids `DYNAMIC`/`STANDARD` se mantienen
    - Línea 6700: el comentario de sección pasa a "The four keys of the Campaign_Setup"
    - Línea 6702: renombrar `test_the_three_remaining_keys_come_from_the_campaign_setup` → `test_the_four_remaining_keys_come_from_the_campaign_setup`. Añadir `meta_conversion_event='LEAD'` a `make_campaign_setup(...)`, `conversion_event='LEAD'` a `_expected_campaign_block(...)` y `assert result['campaign']['conversion_event'] == 'LEAD'`. El docstring enumera las cuatro claves y conserva su línea `Requirements:`
    - Líneas 6745-6746: en el docstring de `test_absent_setup_attributes_would_not_reach_the_block`, "three ``None`` values" pasa a "four ``None`` values" (solo docstring)
    - Línea 6864, `TestMetaUrl::test_meta_resources_is_never_read_end_to_end`: en el docstring, "six attributes" pasa a "seven attributes". La aserción no cambia porque usa la constante actualizada en 3.1
    - No tocar `test_creatives_no_follows_the_size_of_the_fixture[one-creative|two-creatives|four-creatives]` ni `test_name_is_the_name_attribute_of_the_resolved_campaign`: pasan gracias al valor por defecto `conversion_event=None`
    - _Bug_Condition: isBugCondition(test) para los tests de `TestCampaignBlock` (1.1) y `TestMetaUrl` (1.4), y su documentación (1.7)_
    - _Expected_Behavior: Property 1 del diseño (siete claves de punta a punta; siete atributos leídos en `execute()`)_
    - _Preservation: ids de `parametrize` sin cambios; comprobaciones de `channel_name == 'Meta'`, `creatives_no`, `name` y `meta_url`; aserciones de `'meta_resources'`_
    - _Requirements: 2.1, 2.4, 2.7, 2.8, 2.9, 2.10, 3.3, 3.4, 3.9, 3.10_

  - [x] 3.4 Corregir `tracking_specs` en `test_facebook_launch_campaign.py`
    - Línea 3155: en la etiqueta `# Feature: meta-ads-leads-offsite-conversions, Property 14: ...`, cambiar `"dataset": [pixel]` por `"fb_pixel": [pixel]`. El resto del texto se mantiene (diseño, ítem 8)
    - Línea 3223, `TestLeadsOffsiteAdPayload::test_tracking_specs_only_for_leads_offsite`: el literal esperado pasa a `[{"action.type": ["offsite_conversion"], "fb_pixel": [pixel]}]`. NO cambian `@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])`, `@given`, la rama `else` ni la comprobación de `set(payload)` (diseño, ítem 9)
    - Línea 3562, `TestLeadsOffsiteLaunchRollback::test_happy_path_publishes_website_adset_and_tracked_ads`: el literal esperado pasa a `[{"action.type": ["offsite_conversion"], "fb_pixel": [_LO_PIXEL_ID]}]` (una sola entrada, sin clave `"dataset"`) (diseño, ítem 10)
    - No renombrar ningún test, clase ni id de `parametrize` en esta suite
    - _Bug_Condition: isBugCondition(test) donde test.expects(tracking_specs) = [{"action.type": [...], "dataset": [pixel]}]_
    - _Expected_Behavior: para todo `pixel` en la Combinación_Leads_Offsite, `tracking_specs == [{"action.type": ["offsite_conversion"], "fb_pixel": [pixel]}]`_
    - _Preservation: fuera de la Combinación_Leads_Offsite, sin `tracking_specs`; configuración de Hypothesis intacta; verificación del adset WEBSITE, orden de llamadas y rollback_
    - _Requirements: 2.5, 2.6, 2.7, 3.5, 3.6, 3.7_

  - [x] 3.5 Verificar que la exploración de la condición del bug ahora pasa
    - **Property 1: Expected Behavior** - Las suites afirman el contrato actual de HL-2671
    - **IMPORTANTE**: Volver a ejecutar las MISMAS suites de la tarea 1. NO escribir tests nuevos
    - Desde `sinergia/`: `venv/bin/python -m pytest tests/v2/unit/use_cases/test_facebook_get_launch_campaign_creatives.py tests/v2/unit/use_cases/test_facebook_launch_campaign.py -q`
    - **RESULTADO ESPERADO**: 985 passed, 0 failed
    - Ejecutar por nombre los cuatro tests renombrados con `-k "seven_keys or four_keys or four_remaining_keys"` y comprobar que existen y pasan
    - Comprobar con `--co -q` que ningún id contiene `six_keys`, `three_keys` ni `three_remaining`
    - Buscar con grep el literal `"dataset"` en `test_facebook_launch_campaign.py` y comprobar que ya no aparece en las expectativas de `tracking_specs`
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9, 2.10_

  - [x] 3.6 Verificar que la preservación se mantiene
    - **Property 2: Preservation** - Los tests no afectados y la producción no cambian
    - **IMPORTANTE**: Volver a ejecutar las MISMAS comprobaciones de la tarea 2. NO escribir tests nuevos
    - Comparar la lista de ids de `--co -q` con la línea base guardada: debe ser idéntica salvo los cuatro renombrados de 2.9 (mismo total, mismos ids de `parametrize`)
    - Confirmar que `TestSuiteSelfAudit` y `TestBuildersIndependence` pasan y que la rama no Leads_Offsite de Property 14 sigue en verde
    - Confirmar que `git status --porcelain sinergia/app/v2/` sigue vacío y que `git status` solo muestra cambios en los dos archivos de `sinergia/tests/v2/unit/use_cases/`
    - Borrar el archivo temporal de la línea base
    - **RESULTADO ESPERADO**: sin regresiones y sin cambios en producción
    - _Requirements: 3.1, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9, 3.10_

- [x] 4. Checkpoint - Asegurar que todos los tests pasan
  - Desde `sinergia/`, ejecutar la suite unitaria completa con `venv/bin/python -m pytest` (nunca en modo watch)
  - **RESULTADO ESPERADO**: 2891 tests, 2891 passed, 0 failed, sin skips nuevos y con `deny_network` activo
  - Si surgen dudas o fallos inesperados, preguntar al usuario antes de continuar
  - _Requirements: 3.2, 3.8_

## Notes

- Es un fix solo de tests: únicamente se modifican los dos archivos de `sinergia/tests/v2/unit/use_cases/`.
- El código de producción (`sinergia/app/v2/`) no se toca en ninguna tarea.
- Todos los comandos se ejecutan desde `sinergia/` con `venv/bin/python -m pytest`.
- Nunca ejecutar pytest en modo watch.

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1", "2"] },
    { "id": 1, "tasks": ["3.1", "3.4"] },
    { "id": 2, "tasks": ["3.2", "3.3"] },
    { "id": 3, "tasks": ["3.5"] },
    { "id": 4, "tasks": ["3.6"] },
    { "id": 5, "tasks": ["4"] }
  ]
}
```
