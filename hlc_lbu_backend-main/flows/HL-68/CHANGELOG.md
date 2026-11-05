# HiLuca - HL-68

## Features
- [HL-68](https://hiluca.atlassian.net/browse/HL-68)

### Flujos actualizados:
- **Project Definition (Generate Landing Page Hero)**
  - Se agrega atributo *type: string ("N", "R")* al body del request. "N" = landing page normal. "R" = landing page remarketing.
  - Se agrega flujo alterno para consultar *OpenAI* y para actualizar en *Strapi* dependiendo de *type* utilizando el node *Switch*.
  - Se agrega atributo *type* al response.
  - **Strapi:** Modificar la collection *project-V2* para agregar los campos *landing_page_hero_remarketing_section_generated* y *landing_page_hero_remarketing_section_configured*, ambos de tipo *JSON*.
- **Project Definition (Get Landing Page Hero Elements)**
  - Se modifica el endpoint en *sinergia*, queda de la siguiente forma */api/v1/application/hiluca/project/< project_id >/landing_page/type/< type >/hero/elements*
  - Se agrega atributo *type: string ("N", "R")* al body del request. "N" = landing page normal. "R" = landing page remarketing.
  - En el node *Code2* se asigna el valor de *elements* dependiendo del valor de *type*.
  - Se agrega atributo *type* al response.
- **Project Definition ( Save Elements Landing Page (Hero) )**
  - Se agrega atributo *type: string ("N", "R")* al body del request. "N" = landing page normal. "R" = landing page remarketing.
  - Se agrega flujo alterno para actualizar en *Strapi* dependiendo de *type* utilizando el node *Switch*.
  - Se agrega atributo *type* al response.
- **Project Definition ( Save Configured Landing Page (Hero) )**
  - Se agrega atributo *type: string ("N", "R")* al body del request. "N" = landing page normal. "R" = landing page remarketing.
  - Se agrega flujo alterno para actualizar en *Strapi* dependiendo de *type* utilizando el node *Switch*.
  - Se agrega atributo *type* al response.
- **Project Definition (Get Landing Page Hero Configuration)**
  - Se modifica el endpoint en 'sinergia', queda de la siguiente forma */api/v1/application/hiluca/project/< project_id >/landing_page/type/< type >/hero*
  - Se agrega atributo *type: string ("N", "R")* al body del request. "N" = landing page normal. "R" = landing page remarketing.
  - En el node *Code2* se asigna el valor de *elements* dependiendo del valor de *type*.
  - Se agrega atributo *type* al response.

----------

- **Project Definition (Generate Landing Page Competitive Advantage)**
  - Se agrega atributo *type: string ("N", "R")* al body del request. "N" = landing page normal. "R" = landing page remarketing.
  - Se agrega flujo alterno para consultar *OpenAI* y para actualizar en *Strapi* dependiendo de *type* utilizando el node *Switch*.
  - Se agrega atributo *type* al response.
  - **Strapi:** Modificar la collection *project-V2* para agregar los campos *landing_page_comp_adv_remarketing_section_generated* y *landing_page_comp_adv_remarketing_section_configured*, ambos de tipo *JSON*.
- **Project Definition (Get Landing Page Competitive Advantages  Elements)**
  - Se modifica el endpoint en *sinergia*, queda de la siguiente forma */api/v1/application/hiluca/project/< project_id >/landing_page/type/< type >/competitive_advantages/elements*
  - Se agrega atributo *type: string ("N", "R")* al body del request. "N" = landing page normal. "R" = landing page remarketing.
  - En el node *Code2* se asigna el valor de *elements* dependiendo del valor de *type*.
  - Se agrega atributo *type* al response.
- **Project Definition ( Save Elements Landing Page (Competitive Advantages) )**
  - Se agrega atributo *type: string ("N", "R")* al body del request. "N" = landing page normal. "R" = landing page remarketing.
  - Se agrega flujo alterno para actualizar en *Strapi* dependiendo de *type* utilizando el node *Switch*.
  - Se agrega atributo *type* al response.
- **Project Definition ( Save Configured Landing Page (Competitive Advantages) )**
  - Se agrega atributo *type: string ("N", "R")* al body del request. "N" = landing page normal. "R" = landing page remarketing.
  - Se agrega flujo alterno para actualizar en *Strapi* dependiendo de *type* utilizando el node *Switch*.
  - Se agrega atributo *type* al response.
- **Project Definition (Get Landing Page Competitive Advantages Configuration)**
  - Se modifica el endpoint en 'sinergia', queda de la siguiente forma */api/v1/application/hiluca/project/< project_id >/landing_page/type/< type >/competitive_advantages*
  - Se agrega atributo *type: string ("N", "R")* al body del request. "N" = landing page normal. "R" = landing page remarketing.
  - En el node *Code2* se asigna el valor de *elements* dependiendo del valor de *type*.
  - Se agrega atributo *type* al response.

----------

- **Project Definition (Generate Landing Page HowWeDo)**
  - Se agrega atributo *type: string ("N", "R")* al body del request. "N" = landing page normal. "R" = landing page remarketing.
  - Se agrega flujo alterno para consultar *OpenAI* y para actualizar en *Strapi* dependiendo de *type* utilizando el node *Switch*.
  - Se agrega atributo *type* al response.
  - **Strapi:** Modificar la collection *project-V2* para agregar los campos *landing_page_howwedo_remarketing_section_generated* y *landing_page_howwedo_remarketing_section_configured*, ambos de tipo *JSON*.
- **Project Definition (Get Landing Page HowWeDo  Elements)**
  - Se modifica el endpoint en *sinergia*, queda de la siguiente forma */api/v1/application/hiluca/project/< project_id >/landing_page/type/< type >/howwedo/elements*
  - Se agrega atributo *type: string ("N", "R")* al body del request. "N" = landing page normal. "R" = landing page remarketing.
  - En el node *Code2* se asigna el valor de *elements* dependiendo del valor de *type*.
  - Se agrega atributo *type* al response.
- **Project Definition ( Save Elements Landing Page ( HowWeDo) )**
  - Se agrega atributo *type: string ("N", "R")* al body del request. "N" = landing page normal. "R" = landing page remarketing.
  - Se agrega flujo alterno para actualizar en *Strapi* dependiendo de *type* utilizando el node *Switch*.
  - Se agrega atributo *type* al response.
- **Project Definition ( Save Configured Landing Page (HowWeDo) )**
  - Se agrega atributo *type: string ("N", "R")* al body del request. "N" = landing page normal. "R" = landing page remarketing.
  - Se agrega flujo alterno para actualizar en *Strapi* dependiendo de *type* utilizando el node *Switch*.
  - Se agrega atributo *type* al response.
- **Project Definition (Get Landing Page HowWeDo Configuration)**
  - Se modifica el endpoint en 'sinergia', queda de la siguiente forma */api/v1/application/hiluca/project/< project_id >/landing_page/type/< type >/howwedo*
  - Se agrega atributo *type: string ("N", "R")* al body del request. "N" = landing page normal. "R" = landing page remarketing.
  - En el node *Code2* se asigna el valor de *elements* dependiendo del valor de *type*.
  - Se agrega atributo *type* al response.

----------

- **Project Definition (Generate Landing Page Testimonial)**
  - Se agrega atributo *type: string ("N", "R")* al body del request. "N" = landing page normal. "R" = landing page remarketing.
  - Se agrega flujo alterno para consultar *OpenAI* y para actualizar en *Strapi* dependiendo de *type* utilizando el node *Switch*.
  - Se agrega atributo *type* al response.
  - **Strapi:** Modificar la collection *project-V2* para agregar los campos *landing_page_testimonial_remarketing_section_generated* y *landing_page_testimonial_remarketing_section_configured*, ambos de tipo *JSON*.
- **Project Definition (Get Landing Page Testimonial  Elements)**
  - Se modifica el endpoint en *sinergia*, queda de la siguiente forma */api/v1/application/hiluca/project/< project_id >/landing_page/type/< type >/testimonial/elements*
  - Se agrega atributo *type: string ("N", "R")* al body del request. "N" = landing page normal. "R" = landing page remarketing.
  - En el node *Code2* se asigna el valor de *elements* dependiendo del valor de *type*.
  - Se agrega atributo *type* al response.
- **Project Definition ( Save Elements Landing Page (Testimonial) )**
  - Se agrega atributo *type: string ("N", "R")* al body del request. "N" = landing page normal. "R" = landing page remarketing.
  - Se agrega flujo alterno para actualizar en *Strapi* dependiendo de *type* utilizando el node *Switch*.
  - Se agrega atributo *type* al response.
- **Project Definition ( Save Configured Landing Page (Testimonial) )**
  - Se agrega atributo *type: string ("N", "R")* al body del request. "N" = landing page normal. "R" = landing page remarketing.
  - Se agrega flujo alterno para actualizar en *Strapi* dependiendo de *type* utilizando el node *Switch*.
  - Se agrega atributo *type* al response.
- **Project Definition (Get Landing Page Testimonial Configuration)**
  - Se modifica el endpoint en 'sinergia', queda de la siguiente forma */api/v1/application/hiluca/project/< project_id >/landing_page/type/< type >/testimonial*
  - Se agrega atributo *type: string ("N", "R")* al body del request. "N" = landing page normal. "R" = landing page remarketing.
  - En el node *Code2* se asigna el valor de *elements* dependiendo del valor de *type*.
  - Se agrega atributo *type* al response.

----------

- **Project Definition (Generate Landing Page Benefits)**
  - Se agrega atributo *type: string ("N", "R")* al body del request. "N" = landing page normal. "R" = landing page remarketing.
  - Se agrega flujo alterno para consultar *OpenAI* y para actualizar en *Strapi* dependiendo de *type* utilizando el node *Switch*.
  - Se agrega atributo *type* al response.
  - **Strapi:** Modificar la collection *project-V2* para agregar los campos *landing_page_benefits_remarketing_section_generated* y *landing_page_benefits_remarketing_section_configured*, ambos de tipo *JSON*.
- **Project Definition (Get Landing Page Benefits  Elements)**
  - Se modifica el endpoint en *sinergia*, queda de la siguiente forma */api/v1/application/hiluca/project/< project_id >/landing_page/type/< type >/benefits/elements*
  - Se agrega atributo *type: string ("N", "R")* al body del request. "N" = landing page normal. "R" = landing page remarketing.
  - En el node *Code2* se asigna el valor de *elements* dependiendo del valor de *type*.
  - Se agrega atributo *type* al response.
- **Project Definition ( Save Elements Landing Page (Benefits) )**
  - Se agrega atributo *type: string ("N", "R")* al body del request. "N" = landing page normal. "R" = landing page remarketing.
  - Se agrega flujo alterno para actualizar en *Strapi* dependiendo de *type* utilizando el node *Switch*.
  - Se agrega atributo *type* al response.
- **Project Definition ( Save Configured Landing Page (Benefits) )**
  - Se agrega atributo *type: string ("N", "R")* al body del request. "N" = landing page normal. "R" = landing page remarketing.
  - Se agrega flujo alterno para actualizar en *Strapi* dependiendo de *type* utilizando el node *Switch*.
  - Se agrega atributo *type* al response.
- **Project Definition (Get Landing Page Benefits Configuration)**
  - Se modifica el endpoint en 'sinergia', queda de la siguiente forma */api/v1/application/hiluca/project/< project_id >/landing_page/type/< type >/benefits*
  - Se agrega atributo *type: string ("N", "R")* al body del request. "N" = landing page normal. "R" = landing page remarketing.
  - En el node *Code2* se asigna el valor de *elements* dependiendo del valor de *type*.
  - Se agrega atributo *type* al response.


## Resumen

### Flujos actualizados
- Project Definition (Generate Landing Page Hero)
- Project Definition (Get Landing Page Hero Elements)
- Project Definition ( Save Elements Landing Page (Hero) )
- Project Definition ( Save Configured Landing Page (Hero) )
- Project Definition (Get Landing Page Hero Configuration)
- Project Definition (Generate Landing Page Competitive Advantage)
- Project Definition (Get Landing Page Competitive Advantages  Elements)
- Project Definition ( Save Elements Landing Page (Competitive Advantages) )
- Project Definition ( Save Configured Landing Page (Competitive Advantages) )
- Project Definition (Get Landing Page Competitive Advantages Configuration)
- Project Definition (Generate Landing Page HowWeDo)
- Project Definition (Get Landing Page HowWeDo  Elements)
- Project Definition ( Save Elements Landing Page ( HowWeDo) )
- Project Definition ( Save Configured Landing Page (HowWeDo) )
- Project Definition (Get Landing Page HowWeDo Configuration)
- Project Definition (Generate Landing Page Testimonial)
- Project Definition (Get Landing Page Testimonial  Elements)
- Project Definition ( Save Elements Landing Page (Testimonial) )
- Project Definition ( Save Configured Landing Page (Testimonial) )
- Project Definition (Get Landing Page Testimonial Configuration)
- Project Definition (Generate Landing Page Benefits)
- Project Definition (Get Landing Page Benefits  Elements)
- Project Definition ( Save Elements Landing Page (Benefits) )
- Project Definition ( Save Configured Landing Page (Benefits) )
- Project Definition (Get Landing Page Benefits Configuration)


### Strapi
#### Se agregan los siguientes campos a la collection *project-V2*, todos de tipo *JSON*:
- landing_page_hero_remarketing_section_generated
- landing_page_hero_remarketing_section_configured
- landing_page_comp_adv_remarketing_section_generated
- landing_page_comp_adv_remarketing_section_configured
- landing_page_howwedo_remarketing_section_generated
- landing_page_howwedo_remarketing_section_configured
- landing_page_testimonial_remarketing_section_generated
- landing_page_testimonial_remarketing_section_configured
- landing_page_benefits_remarketing_section_generated
- landing_page_benefits_remarketing_section_configured