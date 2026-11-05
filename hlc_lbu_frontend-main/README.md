# Hi Luca Front-end

Hi Luca Front-end is a Vue 3 web application used to build and manage marketing funnels, campaigns, and related content workflows.

## Technologies Used

- Vue 3
- TypeScript
- Vite
- npm

## Libraries Used

- **Vuetify** — Used sparingly for the app shell (`v-app` / `v-main`), base form inputs (`VTextField`, `VTextarea`, `VSelect`, `VAutocomplete`), admin data tables (`VDataTable`, `VDataTableServer`), and pagination. Most UI is custom Tailwind-based components.
- **Tailwind CSS** — Primary styling layer for layouts, spacing, typography, and most custom UI components.
- **Vue Router** — Client-side routing, navigation guards, and dynamic route segments.
- **Pinia** — Centralized state management for auth, funnel flows, and feature stores.
- **Vue I18n** — Internationalization with English and Spanish locale files.
- **VueUse** — Composition utilities for browser APIs, reactivity helpers, and common patterns.
- **VeeValidate + Yup** — Declarative form validation with schema-based rules.
- **Vue Advanced Cropper** — Image cropping in upload and asset-editing flows.
- **PostHog** — Product analytics and user event tracking.

## Project Structure

The application source lives under `src/`. Page files under `src/pages/` follow Nuxt-like naming conventions, but routes are **manually defined** in `src/router/index.ts` — adding a file does not create a route automatically.

```
v2-hiluca-frontend-vue/
├── .cursor/              # Cursor editor rules and AI assistant configuration
├── .github/              # GitHub Actions workflows
├── .husky/               # Git hooks (pre-commit)
├── .storybook/           # Storybook configuration (not actively maintained)
├── e2e/                  # Playwright specs (not actively maintained)
├── public/               # Static assets served as-is (images, favicons, PDFs)
├── src/
│   ├── assets/           # Bundled static assets (images used in components)
│   ├── components/       # Reusable Vue components, grouped by feature
│   ├── composables/      # Composition API hooks (auth, routing IDs, forms, etc.)
│   ├── constants/        # Shared constants and enums
│   ├── pages/            # Route-level views (Nuxt-like layout; routes wired in router/)
│   ├── plugins/          # App plugins (i18n, Vuetify, Vue Query)
│   ├── router/           # Vue Router configuration
│   ├── services/         # API clients and backend integration
│   ├── stores/           # Pinia state stores
│   ├── stories/          # Storybook stories (outdated; not actively maintained)
│   ├── styles/           # Global styles (Tailwind entry point)
│   ├── types/            # Shared TypeScript type definitions
│   ├── utils/            # Pure utility functions
│   ├── App.vue           # Root application component
│   └── main.ts           # Application entry point
├── Dockerfile            # Container build definition
├── docker-compose.yml    # Local Docker setup
├── index.html            # HTML entry point
├── playwright.config.ts  # Playwright config (not actively maintained)
├── tailwind.config.js    # Tailwind CSS configuration
└── vite.config.ts        # Vite build and dev server configuration
```

### `src/` directories

| Directory      | Purpose                                                                                                                                                                                                                                                 |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `components/`  | UI building blocks organized by domain (e.g. `brands`, `campaigns`, `funnel-flow`, `forms`, `layouts`, `modals`). Legacy funnel and ad-generation flows live under `components/legacy/`.                                                                |
| `composables/` | Reusable logic: route param helpers (`useBrandId`, `useProjectId`), auth flows, form helpers, analytics (`usePostHog`), and multi-step form state.                                                                                                      |
| `pages/`       | Route-level views organized with Nuxt-like conventions (`index.vue`, `[brandId]/` dynamic folders). Each page must be imported and registered in `src/router/index.ts`. The `pages/projects/` tree is legacy; current flows live under `pages/brands/`. |
| `services/`    | HTTP API modules. Current APIs are grouped under `projects/` and `products/`; older endpoints remain in `legacy/`.                                                                                                                                      |
| `stores/`      | Pinia stores for global and feature state (auth, modals, funnel-flow, brand forms, ad platform connections).                                                                                                                                            |
| `plugins/`     | Vue plugin setup: `i18n` (with `locales/en.json` and `locales/es.json`), Vuetify theme/defaults, and Vue Query.                                                                                                                                         |
| `utils/`       | Shared helpers for API calls, dates, URLs, scrolling, and text formatting. Auto-imported via Vite.                                                                                                                                                      |
| `constants/`   | App-wide constants (brands, campaigns, currencies, file sizes). Auto-imported via Vite.                                                                                                                                                                 |

### Routing and pages

Unlike [Nuxt file-based routing](https://nuxt.com/docs/4.x/directory-structure/app/pages), this project uses Vue Router with explicit route definitions. The `pages/` folder is for organization only — path, layout, auth, and permissions are configured in `src/router/index.ts`.

**Naming conventions** (Nuxt-inspired):

- Folders mirror URL segments: `brands/[brandId]/projects/[projectId]/`
- Bracket folders are dynamic params: `[brandId]` → `:brandId` in the router
- `index.vue` is the default view for a segment
- Some paths don't match the filename (e.g. `login.vue` is served at `/`, not `/login`)

**Product hierarchy:**

- **Auth** — `login.vue`, `register.vue`, `forgot-password.vue`, and related flows.
- **Brands** — `brands/` lists and manages brands; `brands/[brandId]/` is the brand workspace.
- **Projects** — `brands/[brandId]/projects/[projectId]/` holds campaigns, assets, and settings.
- **Campaigns & funnel flow** — `campaigns/[campaignId]/` includes funnel-flow steps such as paid-social ads assembly and launchpad.
- **Umbrella campaigns** — `umbrella-campaigns/` for campaign grouping and configuration.
- **Target customers** — `target-customers/` for buyer persona management.
- **Products** — `products/` for product catalog and settings.
- **Settings** — `settings/` for admin users, roles, and organizations.
- **Legacy** — `pages/projects/` (including `funnel-stage/` and its acquisition flows: email marketing, landing pages, WhatsApp bot, Meta ads). Prefer `pages/brands/` for new work.

### Tooling and conventions

- **Auto-imports** — Vue, Vue Router, Pinia, VueUse, VeeValidate, and project `composables/`, `stores/`, `utils/`, and `constants/` are auto-imported (see `vite.config.ts`).
- **Component auto-registration** — VueUse components and the Iconify `Icon` component are resolved automatically.

## E2E tests (not maintained)

Playwright is installed and configured, but end-to-end testing is **not part of the current workflow**.

- The only spec is `e2e/auth.spec.ts`, added as a one-off (~9 months ago). It covers login, forgot password, and register validation.
- There is no `npm` script to run the tests.
- The Playwright job in `.github/workflows/docker-image-dev.yml` is commented out and not run in CI.

## Storybook (not maintained)

Storybook is configured and can be started with `npm run storybook`, but it is **not actively maintained**.

- Stories live in `src/stories/` and document a small set of base UI pieces (buttons, forms, colors, typography, modals).
- Most current components and flows are not covered.
- Stories have not been updated alongside recent UI changes, so they may be outdated or broken.

## Installation

1. Clone the repository:

```bash
git clone git@github.com:aculih/hlc_lbu_frontend.git
```

1. Install dependencies:

```bash
npm install
```

1. Add environment variables:

- Use `.env_base` as reference/template.
- Create or update your local `.env` based on your setup.

## Run

Start the development server:

```bash
npm run dev
```

## Cursor Configuration

This project includes a `.cursor` directory with editor rules and AI assistant configuration for development workflows.
