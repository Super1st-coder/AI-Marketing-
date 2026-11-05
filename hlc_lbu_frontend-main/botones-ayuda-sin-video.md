# Botones de ayuda sin video

Lista de pantallas donde el botón de ayuda (`helpButton` de `PageTitle`) se comentó o deshabilitó porque **no hay URL de video**. En el código hay un comentario `TODO: add help video URL later`.

Para reactivar un botón, restaura `helpButton` y añade `helpVideoUrl` con el enlace del video.

No hay usos independientes de `ButtonVideoHelp` sin URL. El único uso directo (`TargetCustomerFormSummary`) ya tiene video.

---

## Funnel Flow → Paid Social

### Channel

- **Dónde encontrarlo:** Funnel Flow → Paid Social → Channel
- **Componente:** `src/components/funnel-flow/flows/paid-social/FunnelPaidSocialFormChannel.vue`

### Ads (Ads Assembly) → editor de banner

- **Dónde encontrarlo:** Funnel Flow → Paid Social → Ads → [ad set] → Select & Refine → editor de banner → generar imagen (pantalla de estilo y pantalla de prompt)
- **Componentes:**
  - `src/components/funnel-flow/flows/paid-social/ads-assembly/refine/editor/banners/AdsAssemblyEditorOverlayBannerMediaLibraryGenerate.vue`
  - `src/components/images/image-generation/StyleSelectionGrid.vue` (el botón solo aparece si el padre pasa `helpVideoUrl`; aquí no se pasa)

### Ads (Ads Assembly) → flujo de video (UGC / Video)

Tienen `helpButton` pero sin `helpVideoUrl`, así que el botón se muestra y no hace nada.

- **Dónde encontrarlo:** Funnel Flow → Paid Social → Ads → [ad set de video] → Ad / Settings / Scripts / Voiceover / Storyboard
- **Componentes:**
  - `src/components/funnel-flow/flows/paid-social/ads-assembly/video/ad/AdsAssemblyVideoAd.vue`
  - `src/components/funnel-flow/flows/paid-social/ads-assembly/video/settings/AdsAssemblyVideoSettings.vue`
  - `src/components/funnel-flow/flows/paid-social/ads-assembly/video/scripts/AdsAssemblyVideoScripts.vue`
  - `src/components/funnel-flow/flows/paid-social/ads-assembly/video/voiceover/AdsAssemblyVideoVoiceover.vue`
  - `src/components/funnel-flow/flows/paid-social/ads-assembly/video/storyboard/AdsAssemblyVideoStoryboard.vue`

---

## Campaigns

### Formulario de campaña (sidebar)

- **Dónde encontrarlo:** Campaign → Funnel Stage
- **Componente:** `src/components/campaigns/CampaignFormFunnel.vue`

---

## Target Customers

- **Dónde encontrarlo:** Target Customers → Profile Image → overlay “Refine your collection of {name}”
- **Componente:** `src/components/target-customers/image/TargetCustomerFormImageVariations.vue`

---

## Settings

- **Dónde encontrarlo:** Settings → Home
- **Componente:** `src/pages/settings/index.vue`

- **Dónde encontrarlo:** Settings → Security
- **Componente:** `src/pages/settings/security.vue`

- **Dónde encontrarlo:** Settings → Roles
- **Componente:** `src/pages/settings/roles.vue`

- **Dónde encontrarlo:** Settings → Organizations
- **Componente:** `src/pages/settings/organizations.vue`

- **Dónde encontrarlo:** Settings → Users
- **Componente:** `src/pages/settings/users.vue`
