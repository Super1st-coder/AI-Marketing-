# Implementation Plan: Funnel Flow Validator Tests

## Overview

Implementar en Python una suite pytest de caracterización para `FunnelFlowValidatorUseCase` y sus validadores, exclusivamente en la capa de pruebas. El trabajo avanzará desde el arnés local aislado hacia helpers, orquestación, reglas de validación, agregados y las 15 propiedades del diseño. La suite parcheará `app.v2.use_cases.funnel_flow_validator.StrapiClient` antes de construir el caso de uso, bloqueará cualquier fuga de red y no modificará código productivo.

## Tasks

- [x] 1. Preparar las dependencias y el arnés local de la suite
  - [x] 1.1 Crear la dependencia de test fijada para las propiedades
    - Crear un archivo dedicado `requirements-test.txt` sin modificar `requirements.txt` ni otra configuración productiva.
    - Verificar en los metadatos del paquete la compatibilidad con Python 3.8 y declarar Hypothesis con una única versión exacta mediante `hypothesis==X.Y.Z`, sin rangos ni versiones flotantes.
    - Incluir Hypothesis únicamente porque las tareas 9.1–9.15 implementarán las propiedades definidas en el diseño.
    - _Requirements: 1.1, 8.7, 8.8_

  - [x] 1.2 Crear el módulo de pruebas y sus builders locales frescos
    - Crear `tests/v2/unit/use_cases/test_funnel_flow_validator.py` y la estructura de directorios necesaria, sin crear `tests/conftest.py`.
    - Implementar builders Python mínimos para funnel flows, canales, ad sets, ads, audiencias, experimentos, ad channels y contextos consolidados; distinguir campo omitido de campo presente con `None` mediante un centinela privado.
    - Hacer que cada invocación produzca listas y diccionarios mutables nuevos, sin defaults mutables ni estado de clase o sesión.
    - Mantener nombres `test_` únicos, type hints explícitos y referencias de trazabilidad en docstrings, comentarios o parámetros.
    - _Requirements: 1.7, 1.8, 1.9, 8.1, 8.2, 8.3, 8.7_

  - [x] 1.3 Implementar fixtures locales de aislamiento y pruebas del arnés
    - Implementar fixtures de alcance función con `unittest.mock.patch` y `MagicMock`; parchear exactamente `app.v2.use_cases.funnel_flow_validator.StrapiClient` antes de cada construcción de `FunnelFlowValidatorUseCase`.
    - Entregar desde una factory local instancias nuevas del caso de uso, el constructor parcheado y el doble de Strapi; configurar `find_by_filters` y `get` en memoria y fallar ante endpoints inesperados.
    - Añadir un guard `autouse` local que bloquee `requests.sessions.Session.request` y una prueba que demuestre que los builders no comparten mutables.
    - Verificar que la ruta alcanzable actual no necesita Flask; no crear aplicación, contexto, fixture Flask ni `conftest.py`. Si la ejecución demuestra una dependencia Flask real, detener la implementación y plantear el cambio de requisitos/diseño antes de añadir infraestructura global.
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 1.10, 8.3, 8.7_

- [x] 2. Caracterizar el estado inicial y los helpers del caso de uso
  - [x] 2.1 Probar la inicialización y el orden canónico
    - Verificar las ocho claves de `_state_map`, su orden exacto y los valores completos `completed=False`, `errors=[]`, `message="Pending validation"`.
    - Verificar que `validators` contiene exactamente ocho instancias y que sus claves siguen el mismo orden canónico.
    - _Requirements: 2.1, 2.2, 2.3_

  - [x] 2.2 Probar `_fetch_bulk` y `_run_validator`
    - Verificar la llamada exacta `get(endpoint, params=params)`, la identidad del objeto `data` retornado y el fallback `[]` cuando `data` falta.
    - Sustituir un validador registrado por un doble y comprobar identidad del contexto, indicador, lista de errores y reemplazo completo de la entrada del estado.
    - Probar una clave no registrada y comparar exactamente `completed=False` y el error `SYS_ERR` sin campos adicionales.
    - _Requirements: 2.4, 2.5, 2.6, 2.7, 2.8, 2.9, 8.4, 8.5_

  - [x] 2.3 Probar `_build_response` y los límites de longitud por ejemplos
    - Comprobar orden, unicidad, identidad de `funnel_flow_data` y adición exclusiva de defaults ausentes en los estados.
    - Parametrizar `0`, `1`, `49`, `50` y `51` y afirmar respectivamente `0`, `2`, `59`, `60` y `61` para `_get_max_length_allowed`.
    - _Requirements: 2.10, 2.11, 2.12, 2.13, 2.14, 7.12_

- [x] 3. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.
  - Ejecutar `./venv/bin/python -m pytest --collect-only -q tests/v2/unit/use_cases/test_funnel_flow_validator.py` y `./venv/bin/python -m pytest -q -ra tests/v2/unit/use_cases/test_funnel_flow_validator.py` sin modo watch.

- [x] 4. Probar la orquestación, consolidación y fallos de obtención
  - [x] 4.1 Implementar el escenario exitoso mínimo y las aserciones de consultas
    - Configurar respuestas Strapi mínimas para múltiples funnel flows, ad sets y ads y ejecutar los validadores reales.
    - Afirmar `ok=1`, estado HTTP `200`, ocho etapas completas sin errores y las llamadas exactas de `find_by_filters`/`get`, incluidos todos los filtros `$in` indexados, `populate` y `pagination[pageSize]=1000`.
    - Comparar la estructura consolidada completa y la preservación de IDs, nombres, proyecto de medios, URLs, audiencias, experimentos, subcategorías, categorías, canales, atributos y medios bajo el padre correcto.
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9, 3.10, 3.11, 3.12, 3.13, 7.12, 8.4, 8.5_

  - [x] 4.2 Implementar escenarios vacíos, referencias desconocidas y relaciones defectuosas
    - Probar campaña sin funnel flows, ad sets vacíos y ad sets sin ads; afirmar respuesta exacta, estados resultantes y omisión de todas las llamadas posteriores no aplicables.
    - Probar audiencias, experimentos y ad channels con padres conocidos y desconocidos, conservando solo las relaciones válidas.
    - Anteponer relaciones con forma anidada defectuosa y demostrar que se omiten mientras una relación válida posterior sí se procesa.
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 4.9, 8.4, 8.5_

  - [x] 4.3 Implementar la matriz de excepciones de Strapi
    - Parametrizar fallos sentinel en `funnel-flows`, `funnel-flow-channels`, `ad-sets`, `audience-audiences`, `experiment-experiments` y `ad-channels`.
    - Para cada fase, configurar solo las respuestas previas mínimas, comprobar la misma instancia de excepción, ausencia de respuesta exitosa, llamadas previas exactas y ausencia de fases posteriores.
    - _Requirements: 4.10, 4.11, 4.12, 4.13, 4.14, 4.15, 8.4, 8.6_

- [x] 5. Probar los validadores básicos
  - [x] 5.1 Implementar las matrices de `ChannelValidator` y `AdsStructureValidator`
    - Cubrir `None`, vacío, tipo inválido, entrada válida y múltiples ad sets inválidos; comparar estado, cantidad, códigos, ausencia/presencia de metadata y orden exactos.
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 8.2, 8.5_

  - [x] 5.2 Implementar la matriz de `AudiencesValidator`
    - Cubrir ausencia, colección vacía, audiencia preferida/no preferida, múltiples errores e iterables no-lista válidos.
    - Caracterizar con `pytest.raises` los `TypeError` y `AttributeError` actuales para valores verdaderos no iterables o elementos sin `get`.
    - _Requirements: 5.8, 5.9, 5.10, 5.11, 5.12, 5.13, 5.14, 5.15, 8.5, 8.6_

  - [x] 5.3 Implementar la matriz de `ExperimentsValidator`
    - Cubrir ausencia, colección vacía, valores exclusivamente falsos, al menos un valor verdadero, múltiples errores e iterables no-lista.
    - Caracterizar con `pytest.raises` los `TypeError` y `AttributeError` actuales sin envolverlos ni convertirlos en resultados.
    - _Requirements: 5.16, 5.17, 5.18, 5.19, 5.20, 5.21, 5.22, 5.23, 8.5, 8.6_

- [x] 6. Caracterizar todas las ramas de `AdsContentValidator`
  - [x] 6.1 Probar precondiciones, proyecto, ads, URL y selección de variante
    - Cubrir ad sets ausentes, única dependencia de audiencias inválida, proyecto ausente, ads ausentes, URL ausente, canales ausentes y ninguna variante seleccionada.
    - Usar escenarios separados para demostrar los `continue` de `ADS_09`, `ADS_03`, `ADS_04` y `ADS_04_01`, y que `ADS_06` permite continuar dentro del mismo ad.
    - Comparar códigos, cantidades, metadata y orden exactos.
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.8, 6.9, 6.10, 6.11, 6.12, 8.5_

  - [x] 6.2 Probar atributos de canal y payloads
    - Cubrir `channel_attributes=[]`, `None` y no iterable, payload vacío, corte del recorrido tras payload vacío, exceso de `max_char` y exclusión case-insensitive para CTA.
    - Afirmar que `None`/no iterable registra la condición previa y después propaga `TypeError` sin devolver tupla.
    - _Requirements: 6.13, 6.14, 6.15, 6.16, 6.17, 6.18, 8.5, 8.6_

  - [x] 6.3 Probar presencia de medios y datos visuales de formatos
    - Parametrizar `elements`, `images_banner` y `formats` ausentes, `None`, no-lista o vacíos, individualmente y en combinaciones, preservando el orden canónico de errores.
    - Cubrir `visual_id` vacío, `visual_url` vacío y ambos vacíos, verificando uno o dos errores y la continuación con formatos posteriores.
    - _Requirements: 6.19, 6.20, 6.21, 6.22, 6.23, 8.5_

  - [x] 6.4 Probar límites, intención y excepciones de elementos
    - Verificar el límite derivado de `original_payload`, `ADS_08_02` con metadata exacta, `ADS_08_01` y el corte de elementos tras intención ausente.
    - Construir el caso donde un payload verdadero precede a cualquier cálculo de `max` y afirmar `UnboundLocalError`.
    - _Requirements: 6.24, 6.25, 6.26, 6.27, 6.28, 8.5, 8.6_

  - [x] 6.5 Probar contexto válido y acumulación estable de errores
    - Verificar que un contexto mínimo completamente válido retorna `completed=True` y cero errores.
    - Construir infracciones independientes que no disparen `continue`, `break` ni excepción y comprobar acumulación exacta entre varios ads y ad sets en orden de evaluación.
    - _Requirements: 6.29, 6.30, 6.31, 8.2, 8.5_

- [x] 7. Probar los validadores agregados y el contrato final
  - [x] 7.1 Implementar la matriz aislada de dependencias agregadas
    - Parchear las cinco clases dependientes con dobles para `SummaryContentValidator`, `ReviewContentValidator` y `LaunchPadContentValidator`.
    - Cubrir todas completas, cada fallo aislado y múltiples fallos; comparar prefijos `SUM`, `REV`, `LAUNCH`, sufijos `01`–`05`, `metadata={}` y orden canónico sin errores espurios.
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.8, 7.9, 7.10, 7.11, 8.5_

  - [x] 7.2 Probar la respuesta final de `execute` con datos
    - Reafirmar sobre una ejecución orquestada que existen exactamente ocho etapas, sin duplicados ni extras, en orden canónico y con la estructura consolidada correspondiente.
    - _Requirements: 2.10, 7.12, 8.4, 8.5_

- [x] 8. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.
  - Ejecutar `./venv/bin/python -m pytest -q -ra tests/v2/unit/use_cases/test_funnel_flow_validator.py` sin servidor, watcher ni modo interactivo.

- [x] 9. Implementar las propiedades con Hypothesis
  - [x] 9.1 Escribir el test PBT de la Property 1: El despacho conserva contexto y resultado
    - Generar claves registradas, booleanos, contextos y listas de errores; comprobar identidad y reemplazo exacto con al menos 100 ejemplos y `deadline=None`.
    - **Property 1: El despacho conserva contexto y resultado**
    - **Validates: Requirements 2.7, 2.8**

  - [x] 9.2 Escribir el test PBT de la Property 2: La respuesta normaliza estados en orden canónico
    - Generar combinaciones de campos ausentes y datos arbitrarios, preservando defaults existentes, identidad, orden y unicidad.
    - **Property 2: La respuesta normaliza estados en orden canónico**
    - **Validates: Requirements 2.10, 2.11, 2.12, 7.12**

  - [x] 9.3 Escribir el test PBT de la Property 3: El margen de longitud está acotado
    - Generar enteros no negativos y comparar exactamente la fórmula `n + min(ceil(n * 0.2), 10)`.
    - **Property 3: El margen de longitud está acotado por veinte por ciento y diez**
    - **Validates: Requirements 2.13, 2.14, 6.24**

  - [x] 9.4 Escribir el test PBT de la Property 4: Las consultas indexadas cubren cada identificador una sola vez
    - Generar IDs únicos y ejecutar `execute` contra respuestas en memoria, comprobando claves indexadas, constantes por endpoint, ausencia de omisiones y duplicados.
    - **Property 4: Las consultas indexadas cubren cada identificador una sola vez**
    - **Validates: Requirements 3.2, 3.3, 3.4, 3.5, 3.6**

  - [x] 9.5 Escribir el test PBT de la Property 5: La consolidación particiona relaciones y preserva proyecciones
    - Generar grafos pequeños con padres conocidos/desconocidos y afirmar pertenencia única, exclusión y preservación de todos los campos proyectados.
    - **Property 5: La consolidación particiona relaciones y preserva proyecciones**
    - **Validates: Requirements 3.7, 3.8, 3.9, 3.10, 3.11, 3.12, 3.13, 4.6, 4.7, 4.8**

  - [x] 9.6 Escribir el test PBT de la Property 6: Una lista de canales no vacía siempre es válida
    - Generar listas no vacías con contenido arbitrario y comprobar completitud sin errores.
    - **Property 6: Una lista de canales no vacía siempre es válida**
    - **Validates: Requirements 5.3**

  - [x] 9.7 Escribir el test PBT de la Property 7: Los errores de estructura corresponden a ad sets inválidos
    - Generar secuencias de ad sets válidos e inválidos y comparar cardinalidad, orden y metadata de cada `ADS_STRUCT_02`.
    - **Property 7: Los errores de estructura corresponden a los ad sets inválidos**
    - **Validates: Requirements 5.5, 5.6, 5.7**

  - [x] 9.8 Escribir el test PBT de la Property 8: La audiencia preferida determina la validez por ad set
    - Generar iterables no vacíos de audiencias con y sin `preferred=1` y comparar exactamente los `AUD_03` aplicables.
    - **Property 8: La audiencia preferida determina la validez por ad set**
    - **Validates: Requirements 5.10, 5.11, 5.12, 5.13**

  - [x] 9.9 Escribir el test PBT de la Property 9: Un experimento verdadero determina la validez por ad set
    - Generar iterables no vacíos de experimentos verdaderos/falsos y comparar exactamente los `EXP_03` aplicables.
    - **Property 9: Un experimento verdadero determina la validez por ad set**
    - **Validates: Requirements 5.18, 5.19, 5.20, 5.21**

  - [x] 9.10 Escribir el test PBT de la Property 10: Los límites de atributos se aplican salvo para CTA
    - Generar nombres CTA con casing variado y nombres no CTA, máximos y payloads excedidos; comparar inclusión/exclusión de `ADS_05_02` y metadata.
    - **Property 10: Los límites de atributos se aplican salvo para CTA**
    - **Validates: Requirements 6.17, 6.18**

  - [x] 9.11 Escribir el test PBT de la Property 11: Los errores de medios corresponden al subconjunto inválido
    - Generar subconjuntos y formas inválidas de los tres campos de medios; comparar un `ADS_07` por campo y orden canónico.
    - **Property 11: Los errores de medios corresponden al subconjunto inválido**
    - **Validates: Requirements 6.19, 6.20**

  - [x] 9.12 Escribir el test PBT de la Property 12: El exceso de payload usa el límite derivado
    - Generar `original_payload` no vacío y payload excedido, afirmando `ADS_08_02` y toda su metadata exacta.
    - **Property 12: El exceso de payload de elemento usa el límite derivado**
    - **Validates: Requirements 6.25**

  - [x] 9.13 Escribir el test PBT de la Property 13: Todo contexto de anuncio válido completa sin errores
    - Construir estrategias válidas por diseño y comprobar `completed=True` y `errors=[]` sin filtrar ejemplos mediante `assume` excesivo.
    - **Property 13: Todo contexto de anuncio válido completa sin errores**
    - **Validates: Requirements 6.29**

  - [x] 9.14 Escribir el test PBT de la Property 14: Las infracciones independientes se acumulan de forma estable
    - Generar secuencias pequeñas que no activen cortes ni excepciones y comparar un error por infracción en orden de evaluación entre ads y ad sets.
    - **Property 14: Las infracciones independientes se acumulan de forma estable**
    - **Validates: Requirements 6.30, 6.31**

  - [x] 9.15 Escribir el test PBT de la Property 15: Los agregados reflejan exactamente las dependencias fallidas
    - Generar todos los subconjuntos de cinco dependencias para las tres clases agregadas y comparar completitud, códigos, `metadata={}` y orden.
    - **Property 15: Los agregados reflejan exactamente las dependencias fallidas**
    - **Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.8, 7.9, 7.10, 7.11**

- [x] 10. Validar colección, aislamiento y repetibilidad de la suite
  - [x] 10.1 Ejecutar la validación pytest completa y corregir únicamente el código de pruebas
    - Ejecutar `./venv/bin/python -m pytest --collect-only -q tests/v2/unit/use_cases/test_funnel_flow_validator.py`.
    - Ejecutar `./venv/bin/python -m pytest -q -ra tests/v2/unit/use_cases/test_funnel_flow_validator.py` y exigir cero `failed`, cero `skipped` y cero errores.
    - Repetir con `PYTHONHASHSEED=1` y `PYTHONHASHSEED=777` usando el mismo comando no interactivo para detectar estado compartido u orden accidental.
    - Confirmar que cada propiedad ejecuta al menos 100 ejemplos, que el guard no detecta red, que no se creó infraestructura Flask y que `app/v2/use_cases/funnel_flow_validator.py` permanece sin cambios.
    - _Requirements: 1.1, 1.5, 1.7, 1.8, 1.9, 1.10, 8.1, 8.3, 8.7, 8.8_

- [x] 11. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Las tareas de pruebas no llevan `*` porque la suite pytest es el entregable principal de esta feature y todos los criterios, incluidas las 15 propiedades, son obligatorios; marcarlas como opcionales permitiría incumplir Requirements 8.8.
- No se debe modificar `app/v2/use_cases/funnel_flow_validator.py`, ningún otro archivo de producción, `requirements.md`, `design.md`, `.config.kiro` ni `requirements.txt`.
- `requirements-test.txt` se crea solo para fijar Hypothesis con una versión exacta compatible con Python 3.8; no se deben añadir `pytest-mock` ni dependencias innecesarias porque la suite usa `unittest.mock.MagicMock` y `patch`.
- No se debe crear `tests/conftest.py`, una aplicación Flask ni una fixture Flask con el código alcanzable actual.
- Cada tarea amplía el mismo módulo de pruebas de manera secuencial; el grafo evita escrituras concurrentes al archivo.
- Todos los comandos pytest son ejecuciones únicas y no interactivas; no se deben iniciar servidores, watchers ni aplicaciones.

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["1.2"] },
    { "id": 2, "tasks": ["1.3"] },
    { "id": 3, "tasks": ["2.1"] },
    { "id": 4, "tasks": ["2.2"] },
    { "id": 5, "tasks": ["2.3"] },
    { "id": 6, "tasks": ["4.1"] },
    { "id": 7, "tasks": ["4.2"] },
    { "id": 8, "tasks": ["4.3"] },
    { "id": 9, "tasks": ["5.1"] },
    { "id": 10, "tasks": ["5.2"] },
    { "id": 11, "tasks": ["5.3"] },
    { "id": 12, "tasks": ["6.1"] },
    { "id": 13, "tasks": ["6.2"] },
    { "id": 14, "tasks": ["6.3"] },
    { "id": 15, "tasks": ["6.4"] },
    { "id": 16, "tasks": ["6.5"] },
    { "id": 17, "tasks": ["7.1"] },
    { "id": 18, "tasks": ["7.2"] },
    { "id": 19, "tasks": ["9.1"] },
    { "id": 20, "tasks": ["9.2"] },
    { "id": 21, "tasks": ["9.3"] },
    { "id": 22, "tasks": ["9.4"] },
    { "id": 23, "tasks": ["9.5"] },
    { "id": 24, "tasks": ["9.6"] },
    { "id": 25, "tasks": ["9.7"] },
    { "id": 26, "tasks": ["9.8"] },
    { "id": 27, "tasks": ["9.9"] },
    { "id": 28, "tasks": ["9.10"] },
    { "id": 29, "tasks": ["9.11"] },
    { "id": 30, "tasks": ["9.12"] },
    { "id": 31, "tasks": ["9.13"] },
    { "id": 32, "tasks": ["9.14"] },
    { "id": 33, "tasks": ["9.15"] },
    { "id": 34, "tasks": ["10.1"] }
  ]
}
```
