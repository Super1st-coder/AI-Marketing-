# HiLuca - HL-79

## Features
- [HL-79](https://hiluca.atlassian.net/browse/HL-79)

### Flujos actualizados:
- **Project Definition (Generate Meta Ads)**
  - Se agrega atributo *type: string ("N", "R")* al body del request. "N" = normal. "R" = remarketing.
  - Se agrega flujo alterno para consultar *OpenAI* y para actualizar en *Strapi* dependiendo de *type* utilizando el node *Switch*.
  - Se agrega atributo *type* al response.
  - **Strapi:** Modificar la collection *project-V2* para agregar el campo *meta_ads_remarketing* de tipo *JSON*.
- **Project Definition (Get Meta Ads)**
  - Se modifica el endpoint en *sinergia*, queda de la siguiente forma */api/v1/application/hiluca/project/< project_id >/type/< type >/meta_ads*
  - Se agrega atributo *type: string ("N", "R")* al body del request. "N" = normal. "R" = remarketing.
  - En el node *Code2* se asigna el valor de *meta_ads* dependiendo del valor de *type*.
  - Se agrega atributo *type* al response.
- **Project Definition (Get One Meta Ad)**
  - Se modifica el endpoint en *sinergia*, queda de la siguiente forma */api/v1/application/hiluca/project/< project_id >/type/< type >/meta_ad/< meta_ad_id >*
  - Se agrega atributo *type: string ("N", "R")* al body del request. "N" = normal. "R" = remarketing.
  - En el node *Code2* se asigna el valor de *meta_ads* dependiendo del valor de *type*.
  - Se agrega atributo *type* al response.
- **Project Definition (Save One Meta Ad)**
  - Se agrega atributo *type: string ("N", "R")* al body del request. "N" = normal. "R" = remarketing.
  - Se agrega flujo alterno para actualizar en *Strapi* dependiendo de *type* utilizando el node *Switch*.
  - Se agrega atributo *type* al response.
- **Project Definition (Generate Image Prompts for Meta Ad)**
  - Se agrega atributo *type: string ("N", "R")* al body del request. "N" = normal. "R" = remarketing.
  - Se agrega flujo alterno para consultar *OpenAI* y para actualizar en *Strapi* dependiendo de *type* utilizando el node *Switch*.
  - Se agrega atributo *type* al response.
- **Project Definition (Upload Meta Ad  Image - Binary)**
  - Se modifica el endpoint en *sinergia*, queda de la siguiente forma */api/v1/application/hiluca/project/< project_id >/type/< type >/meta_ad/< meta_ad_id >/image*
  - Se agrega atributo *type: string ("N", "R")* al body del request. "N" = normal. "R" = remarketing.
  - En el node *Code1* se asigna el valor de *meta_ads* dependiendo del valor de *type*.
  - Se agrega atributo *type* al response.
- **Project Definition (Get Meta Ad Image)**
  - Se modifica el endpoint en *sinergia*, queda de la siguiente forma */api/v1/application/hiluca/project/<project_id>/type/<type>/meta_ad/<meta_ad_id>/image*
  - Se agrega atributo *type: string ("N", "R")* al body del request. "N" = normal. "R" = remarketing.
  - En el node *Code* se asigna el valor de *meta_ad* dependiendo del valor de *type*.


## Resumen

### Flujos actualizados
- Project Definition (Generate Meta Ads)
- Project Definition (Get Meta Ads)
- Project Definition (Get One Meta Ad)
- Project Definition (Save One Meta Ad)
- Project Definition (Generate Image Prompts for Meta Ad)
- Project Definition (Upload Meta Ad  Image - Binary)
- Project Definition (Get Meta Ad Image)


### Strapi
#### Se agregan los siguientes campos a la collection *project-V2*, todos de tipo *JSON*:
- meta_ads_remarketing