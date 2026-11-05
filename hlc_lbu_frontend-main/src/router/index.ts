import {
  createRouter,
  createWebHistory,
  RouteLocationNormalized,
  RouteLocationRaw,
  RouteRecordRaw,
} from "vue-router";
import { usePostHog } from "@/composables/usePostHog";
import i18n, {
  defaultAppLocale,
  loadLocaleMessages,
  setI18nLanguage,
  SUPPORT_LOCALES,
} from "@/plugins/i18n";
import type { Locale } from "vue-i18n";
import { registerGuestRouteNames, isGuestRouteName } from "./guest-routes";

const Login = () => import("@/pages/login.vue");
const ForgotPassword = () => import("@/pages/forgot-password.vue");
const SignupFinish = () => import("@/pages/signup-finish.vue");
const VerifyYouEmail = () =>
  import("../components/auth/VerifyYourEmailForm.vue");
const Register = () => import("@/pages/register.vue");
const ForgotFinish = () => import("@/pages/forgot-finish.vue");
const Unsubscribe = () => import("@/pages/unsubscribe.vue");

const Home = () => import("../components/Home.vue");
const GettingStarted = () =>
  import("../pages/(legacy)/projects/getting-started.vue");
const Process = () => import("../pages/(legacy)/projects/process.vue");
const FunnelStage = () =>
  import("@/pages/(legacy)/projects/funnel-stage/funnel-stage.vue");
const FunnelStageAcquisition = () =>
  import("@/pages/(legacy)/projects/funnel-stage/acquisition/acquisition.vue");
const PaidSocial = () =>
  import("@/pages/(legacy)/projects/funnel-stage/acquisition/paid-social/paid-social.vue");
const AddGenerationLayout = () =>
  import("@/components/layouts/AddGenerationLayout.vue");
const EmailMarketingFlow = () =>
  import("@/pages/(legacy)/projects/funnel-stage/acquisition/paid-social/email-marketing-flow/email-marketing-flow.vue");
const ReminderAndValue = () =>
  import("@/pages/(legacy)/projects/funnel-stage/acquisition/paid-social/email-marketing-flow/reminder-and-value.vue");
const LandingPage = () =>
  import("@/pages/(legacy)/projects/funnel-stage/acquisition/paid-social/landing-page/landing-page.vue");
const LandingPageRemarketing = () =>
  import("@/pages/(legacy)/projects/funnel-stage/acquisition/paid-social/landing-page-remarketing/landing-page-remarketing.vue");
const PainPoints = () =>
  import("@/pages/(legacy)/projects/funnel-stage/acquisition/paid-social/email-marketing-flow/pain-points.vue");
const CaseStudies = () =>
  import("@/pages/(legacy)/projects/funnel-stage/acquisition/paid-social/email-marketing-flow/case-studies.vue");
const Urgency = () =>
  import("@/pages/(legacy)/projects/funnel-stage/acquisition/paid-social/email-marketing-flow/urgency.vue");
const SpecialOffer = () =>
  import("@/pages/(legacy)/projects/funnel-stage/acquisition/paid-social/email-marketing-flow/special-offer.vue");
const Create = () => import("@/pages/(legacy)/projects/create.vue");
const Projects = () => import("@/pages/(legacy)/projects/projects.vue");
const RemarketingMetaAds = () =>
  import("@/pages/(legacy)/projects/funnel-stage/acquisition/paid-social/remarketing-meta-ads.vue");

const MetaAds = () =>
  import("@/pages/(legacy)/projects/funnel-stage/acquisition/paid-social/meta-ads.vue");
const WhatsappBotFunnel = () =>
  import("@/pages/(legacy)/projects/funnel-stage/acquisition/paid-social/whatsapp-bot-funnel/whatsapp-bot-funnel.vue");
const Settings = () =>
  import("@/pages/(legacy)/projects/funnel-stage/acquisition/paid-social/whatsapp-bot-funnel/settings.vue");

const BrandList = () => import("@/pages/brands/index.vue");
const NoBrandAccess = () => import("@/pages/brands/no-access.vue");
const CreateBrand = () => import("@/pages/brands/create.vue");
const BrandSettings = () => import("@/pages/brands/[brandId]/settings.vue");
const BrandHome = () => import("@/pages/brands/[brandId]/index.vue");
const BrandInsights = () =>
  import("@/pages/brands/[brandId]/insights/index.vue");
const LucaGuideOnboarding = () =>
  import("@/pages/brands/[brandId]/luca-guide/onboarding/index.vue");
const LucaGuideSettings = () =>
  import("@/pages/brands/[brandId]/luca-guide/settings/index.vue");
const LucaGuideCampaigns = () =>
  import("@/pages/brands/[brandId]/luca-guide/campaigns/index.vue");
const LucaGuideCampaign = () =>
  import("@/pages/brands/[brandId]/luca-guide/campaigns/[campaignId]/index.vue");
const LucaGuideCampaignOnboarding = () =>
  import("@/pages/brands/[brandId]/luca-guide/campaigns/[campaignId]/onboarding/index.vue");
const LucaGuideCampaignBrief = () =>
  import("@/pages/brands/[brandId]/luca-guide/campaigns/[campaignId]/brief/index.vue");
const LucaGuideCampaignHistory = () =>
  import("@/pages/brands/[brandId]/luca-guide/campaigns/[campaignId]/history/index.vue");
const LucaGuideCampaignAd = () =>
  import("@/pages/brands/[brandId]/luca-guide/campaigns/[campaignId]/ads/[adId]/index.vue");
const LucaGuide = () => import("@/pages/brands/[brandId]/luca-guide/index.vue");

const BuyerPersonList = () =>
  import("@/pages/brands/[brandId]/target-customers/index.vue");
const ProductList = () => import("@/pages/brands/[brandId]/products/index.vue");

const CreateProduct = () =>
  import("@/pages/brands/[brandId]/products/create.vue");
const ProductSettings = () =>
  import("@/pages/brands/[brandId]/products/[productId]/settings.vue");

const CreateBuyerPerson = () =>
  import("@/pages/brands/[brandId]/target-customers/create.vue");
const BuyerPersonSettings = () =>
  import("@/pages/brands/[brandId]/target-customers/[buyerPersonId]/settings.vue");

const ProjectList = () => import("@/pages/brands/[brandId]/projects/index.vue");
const CreateProject = () =>
  import("@/pages/brands/[brandId]/projects/create.vue");
const ProjectSettings = () =>
  import("@/pages/brands/[brandId]/projects/[projectId]/settings.vue");

const UmbrellaCampaignList = () =>
  import("@/pages/brands/[brandId]/projects/[projectId]/umbrella-campaigns/index.vue");
const CreateUmbrellaCampaign = () =>
  import("@/pages/brands/[brandId]/projects/[projectId]/umbrella-campaigns/create.vue");
const UmbrellaCampaignSettings = () =>
  import("@/pages/brands/[brandId]/projects/[projectId]/umbrella-campaigns/[umbrellaCampaignId]/settings.vue");

const CampaignList = () =>
  import("@/pages/brands/[brandId]/projects/[projectId]/campaigns/index.vue");
const CreateCampaign = () =>
  import("@/pages/brands/[brandId]/projects/[projectId]/campaigns/create.vue");
const CampaignSettings = () =>
  import("@/pages/brands/[brandId]/projects/[projectId]/campaigns/[campaignId]/settings.vue");

const FunnelFlowHome = () =>
  import("@/pages/brands/[brandId]/projects/[projectId]/campaigns/[campaignId]/funnel-flow/index.vue");

const FunnelPaidSocial = () =>
  import("@/pages/brands/[brandId]/projects/[projectId]/campaigns/[campaignId]/funnel-flow/paid-social/index.vue");

const UserSettings = () => import("@/pages/settings/index.vue");
const UserSettingsSecurity = () => import("@/pages/settings/security.vue");
const SettingsFormRoles = () => import("@/pages/settings/roles.vue");
const SettingsFormOrganizations = () =>
  import("@/pages/settings/organizations.vue");
const SettingsFormUsers = () => import("@/pages/settings/users.vue");

const BrandLayout = () => import("@/components/layouts/BrandLayout.vue");
const ProjectLayout = () => import("@/components/layouts/ProjectLayout.vue");
const CampaignLayout = () => import("@/components/layouts/CampaignLayout.vue");
const LucaGuideLayout = () =>
  import("@/components/layouts/LucaGuideLayout.vue");

const SimpleLayout = () => import("@/components/layouts/SimpleLayout.vue");
const SettingsLayout = () => import("@/components/layouts/SettingsLayout.vue");
const FacebookAuthCallback = () => import("@/pages/facebook-auth-callback.vue");

declare module "vue-router" {
  interface RouteMeta {
    requiresAuth?: boolean;
    hasSidebar?: boolean;
    requiredPermissions?: RoutePermissionMeta[];
    permissionRedirectTo?: RouteLocationRaw;
    /** Remount key for App ErrorBoundary/Suspense; defaults to all params except locale. */
    key?: string | ((route: RouteLocationNormalized) => string);
  }
}

const routes: RouteRecordRaw[] = [
  {
    path: "/:locale(en|es)?",
    children: [
      {
        path: "", // Default route
        name: "Login",
        component: Login,
      },
      {
        path: "register",
        name: "Register",
        component: Register,
      },
      {
        path: "signup-finish",
        name: "SignupFinish",
        component: SignupFinish,
      },
      {
        path: "forgot-password",
        name: "ForgotPassword",
        component: ForgotPassword,
      },
      {
        path: "forgot-finish",
        name: "ForgotFinish",
        component: ForgotFinish,
      },
      {
        path: "verify-email",
        name: "VerifyYouEmail",
        component: VerifyYouEmail,
      },
      {
        path: "unsubscribe",
        name: "Unsubscribe",
        component: Unsubscribe,
      },
      {
        path: "home",
        name: "Home",
        component: Home,
        meta: { requiresAuth: true },
      },
      {
        path: "dev/facebook/test",
        name: "FacebookTestPage",
        component: () => import("@/pages/tests/FacebookTestPage.vue"),
        meta: {
          requiresAuth: true,
          layout: "default",
        },
      },
      {
        path: "dev/storage/test",
        name: "StorageTestPage",
        component: () => import("@/pages/tests/StorageTestPage.vue"),
        meta: {
          requiresAuth: true,
          layout: "default",
        },
      },
      {
        path: "facebook-auth-callback",
        name: "FacebookAuthCallback",
        component: FacebookAuthCallback,
        meta: { requiresAuth: true },
      },
      {
        path: "brands",
        meta: {
          requiresAuth: true,
        },
        children: [
          {
            path: "",
            component: SimpleLayout,
            children: [
              {
                path: "",
                name: "BrandList",
                component: BrandList,
                meta: {
                  requiredPermissions: [{ name: "BRAND", actions: ["R"] }],
                  permissionRedirectTo: { name: "NoBrandAccess" },
                },
              },
              {
                path: "no-access",
                component: NoBrandAccess,
                name: "NoBrandAccess",
              },
              {
                path: "create",
                name: "CreateBrand",
                component: CreateBrand,
                meta: {
                  hasSidebar: true,
                  requiredPermissions: [{ name: "BRAND", actions: ["C", "U"] }],
                },
              },
              {
                path: ":brandId/settings",
                name: "BrandSettings",
                component: BrandSettings,
                meta: {
                  hasSidebar: true,
                  requiredPermissions: [{ name: "BRAND", actions: ["R"] }],
                },
              },
            ],
          },

          {
            path: ":brandId",
            children: [
              {
                path: "",
                component: BrandLayout,
                meta: {
                  hasSidebar: true,
                },
                children: [
                  {
                    path: "",
                    name: "Brand",
                    component: BrandHome,
                  },
                  {
                    path: "insights",
                    children: [
                      {
                        path: "",
                        name: "BrandInsights",
                        component: BrandInsights,
                      },
                    ],
                  },
                  {
                    path: "projects",
                    children: [
                      {
                        path: "",
                        name: "ProjectList",
                        component: ProjectList,
                      },
                    ],
                  },
                  {
                    path: "target-customers",
                    children: [
                      {
                        path: "",
                        name: "BuyerPersonList",
                        component: BuyerPersonList,
                      },
                    ],
                  },
                  {
                    path: "products",
                    children: [
                      {
                        path: "",
                        name: "ProductList",
                        component: ProductList,
                      },
                    ],
                  },
                ],
              },

              ...(isLucaGuideEnabled
                ? [
                    {
                      path: "luca-guide",
                      component: LucaGuideLayout,
                      meta: {
                        hasSidebar: true,
                        // Keep layout mounted across nested guide pages (e.g. campaign detail ↔ home).
                        key: (route) => String(route.params.brandId),
                      },
                      children: [
                        {
                          path: "",
                          name: "LucaGuide",
                          component: LucaGuide,
                        },
                        {
                          path: "onboarding",
                          name: "LucaGuideOnboarding",
                          component: LucaGuideOnboarding,
                        },
                        {
                          path: "settings",
                          name: "LucaGuideSettings",
                          component: LucaGuideSettings,
                        },
                        {
                          path: "campaigns",
                          children: [
                            {
                              path: "",
                              name: "LucaGuideCampaigns",
                              component: LucaGuideCampaigns,
                            },
                            {
                              path: ":campaignId",
                              children: [
                                {
                                  path: "",
                                  name: "LucaGuideCampaign",
                                  component: LucaGuideCampaign,
                                },
                                {
                                  path: "onboarding",
                                  name: "LucaGuideCampaignOnboarding",
                                  component: LucaGuideCampaignOnboarding,
                                },
                                {
                                  path: "brief",
                                  name: "LucaGuideCampaignBrief",
                                  component: LucaGuideCampaignBrief,
                                },
                                {
                                  path: "history",
                                  name: "LucaGuideCampaignHistory",
                                  component: LucaGuideCampaignHistory,
                                },
                                {
                                  path: "ads/:adId",
                                  name: "LucaGuideCampaignAd",
                                  component: LucaGuideCampaignAd,
                                },
                              ],
                            },
                          ],
                        },
                      ],
                    },
                  ]
                : []),

              {
                path: "products",
                component: SimpleLayout,
                meta: {
                  requiredPermissions: [{ name: "PRODUCT", actions: ["R"] }],
                  hasSidebar: true,
                },
                children: [
                  {
                    path: "create",
                    name: "CreateProduct",
                    component: CreateProduct,
                    meta: {
                      hasSidebar: true,
                      requiredPermissions: [
                        { name: "PRODUCT", actions: ["C", "U"] },
                      ],
                    },
                  },
                  {
                    path: ":productId",
                    children: [
                      {
                        path: "settings",
                        name: "ProductSettings",
                        component: ProductSettings,
                        meta: {
                          requiredPermissions: [
                            { name: "PRODUCT", actions: ["R"] },
                          ],
                        },
                      },
                    ],
                  },
                ],
              },

              {
                path: "target-customers",
                component: SimpleLayout,
                meta: {
                  requiredPermissions: [
                    { name: "TARGET_CUSTOMER", actions: ["R"] },
                  ],
                  hasSidebar: true,
                },
                children: [
                  {
                    path: "create",
                    name: "CreateBuyerPerson",
                    component: CreateBuyerPerson,
                    meta: {
                      requiredPermissions: [
                        { name: "TARGET_CUSTOMER", actions: ["C", "U"] },
                      ],
                      hasSidebar: true,
                    },
                  },
                  {
                    path: ":buyerPersonId",
                    children: [
                      {
                        path: "settings",
                        name: "BuyerPersonSettings",
                        component: BuyerPersonSettings,
                        meta: {
                          requiredPermissions: [
                            {
                              name: "TARGET_CUSTOMER",
                              actions: ["R"],
                            },
                          ],
                        },
                      },
                    ],
                  },
                ],
              },

              {
                path: "projects",
                meta: {
                  requiredPermissions: [{ name: "PROJECT", actions: ["R"] }],
                  hasSidebar: true,
                },
                children: [
                  {
                    path: "",
                    component: SimpleLayout,
                    children: [
                      {
                        path: "create",
                        name: "CreateProject",
                        component: CreateProject,
                        meta: {
                          requiredPermissions: [
                            { name: "PROJECT", actions: ["C", "U"] },
                          ],
                          hasSidebar: true,
                        },
                      },
                      {
                        path: ":projectId",
                        children: [
                          {
                            path: "settings",
                            name: "ProjectSettings",
                            component: ProjectSettings,
                            meta: {
                              requiredPermissions: [
                                { name: "PROJECT", actions: ["U"] },
                              ],
                            },
                          },
                        ],
                      },
                    ],
                  },

                  {
                    path: ":projectId",
                    children: [
                      {
                        path: "",
                        component: ProjectLayout,
                        meta: {
                          hasSidebar: true,
                        },
                        children: [
                          {
                            path: "umbrella-campaigns",
                            children: [
                              {
                                path: "",
                                name: "UmbrellaCampaignList",
                                component: UmbrellaCampaignList,
                                meta: {
                                  requiredPermissions: [
                                    {
                                      name: "UMBRELLA_CAMPAIGN",
                                      actions: ["R"],
                                    },
                                  ],
                                },
                              },
                            ],
                          },
                          {
                            path: "campaigns",
                            children: [
                              {
                                path: "",
                                name: "CampaignList",
                                component: CampaignList,
                              },
                            ],
                          },
                        ],
                      },

                      {
                        path: "umbrella-campaigns",
                        component: SimpleLayout,
                        children: [
                          {
                            path: "create",
                            name: "CreateUmbrellaCampaign",
                            component: CreateUmbrellaCampaign,
                            meta: {
                              requiredPermissions: [
                                {
                                  name: "UMBRELLA_CAMPAIGN",
                                  actions: ["C", "U"],
                                },
                              ],
                            },
                          },
                          {
                            path: ":umbrellaCampaignId",
                            children: [
                              {
                                path: "settings",
                                name: "UmbrellaCampaignSettings",
                                component: UmbrellaCampaignSettings,
                                meta: {
                                  requiredPermissions: [
                                    {
                                      name: "UMBRELLA_CAMPAIGN",
                                      actions: ["R"],
                                    },
                                  ],
                                },
                              },
                            ],
                          },
                        ],
                      },

                      {
                        path: "campaign",
                        children: [
                          {
                            path: "",
                            component: SimpleLayout,
                            children: [
                              {
                                path: "create",
                                name: "CreateCampaign",
                                component: CreateCampaign,
                                meta: {
                                  requiredPermissions: [
                                    {
                                      name: "CAMPAIGN_SETUP",
                                      actions: ["C", "U"],
                                    },
                                  ],
                                },
                              },
                            ],
                          },
                          {
                            path: ":campaignId",
                            children: [
                              {
                                path: "",
                                component: SimpleLayout,
                                children: [
                                  {
                                    path: "settings",
                                    name: "CampaignSettings",
                                    component: CampaignSettings,
                                    meta: {
                                      requiredPermissions: [
                                        {
                                          name: "CAMPAIGN_SETUP",
                                          actions: ["R"],
                                        },
                                      ],
                                    },
                                  },
                                ],
                              },

                              // The campaign "Summary" is a step inside the
                              // settings wizard, not a standalone route. Older
                              // links (and the Campaign Hub cards) could point at
                              // `/campaign/:campaignId/summary`, which matched no
                              // route and rendered a blank page (HL-2685).
                              // Redirect it to the settings wizard, which opens on
                              // the Summary step for completed campaigns.
                              {
                                path: "summary",
                                redirect: (to) => ({
                                  name: "CampaignSettings",
                                  params: to.params,
                                }),
                              },

                              {
                                path: "funnel-flow",
                                children: [
                                  {
                                    path: "",
                                    component: CampaignLayout,
                                    children: [
                                      {
                                        path: "",
                                        name: "FunnelFlowHome",
                                        component: FunnelFlowHome,
                                        meta: {
                                          requiredPermissions: [
                                            {
                                              name: "FUNNEL_FLOW",
                                              actions: ["R"],
                                            },
                                          ],
                                        },
                                      },
                                    ],
                                  },
                                  {
                                    path: "paid-social",
                                    component: SimpleLayout,
                                    children: [
                                      {
                                        path: "",
                                        name: "FunnelPaidSocial",
                                        component: FunnelPaidSocial,
                                      },
                                    ],
                                  },
                                ],
                              },
                            ],
                          },
                        ],
                      },
                    ],
                  },
                ],
              },
            ],
          },
        ],
      },

      {
        path: "settings",
        meta: { requiresAuth: true },
        component: SettingsLayout,
        children: [
          {
            path: "",
            name: "UserSettings",
            component: UserSettings,
            meta: { requiresAuth: true },
          },
          {
            path: "security",
            name: "UserSettingsSecurity",
            component: UserSettingsSecurity,
          },
          {
            path: "roles",
            name: "UserSettingsRoles",
            component: SettingsFormRoles,
            meta: {
              requiredPermissions: [{ name: "ADMIN_ROLES", actions: ["R"] }],
            },
          },
          {
            path: "organizations",
            name: "UserSettingsOrganizations",
            component: SettingsFormOrganizations,
            meta: {
              requiredPermissions: [{ name: "ADMIN_ORG", actions: ["R"] }],
            },
          },
          {
            path: "users",
            name: "UserSettingsUsers",
            component: SettingsFormUsers,
            meta: {
              requiredPermissions: [{ name: "ADMIN_USER", actions: ["R"] }],
            },
          },
        ],
      },
      {
        path: "projects",
        meta: { requiresAuth: true },
        component: AddGenerationLayout,
        children: [
          {
            path: "",
            name: "Projects",
            component: Projects,
          },
          {
            path: "getting-started",
            name: "AdGenerationGettingStarted",
            component: GettingStarted,
          },
          {
            path: "create",
            name: "AdGenerationCreate",
            component: Create,
            meta: {
              requiredPermissions: [
                { name: "PROJECT", actions: ["R", "C", "U"] },
              ],
            },
          },
          {
            path: ":id",
            children: [
              {
                path: "hypothesis-builder",
                name: "AdGenerationProcess",
                component: Process,
              },
              {
                path: "funnel-stage",
                children: [
                  {
                    path: "",
                    name: "FunnelStage",
                    component: FunnelStage,
                  },
                  {
                    path: "acquisition",
                    children: [
                      {
                        path: "",
                        name: "FunnelStageAcquisition",
                        component: FunnelStageAcquisition,
                      },
                      {
                        path: "paid-social",
                        children: [
                          {
                            path: "",
                            name: "PaidSocial",
                            component: PaidSocial,
                          },
                          {
                            path: "meta-ads",
                            name: "MetaAds",
                            component: MetaAds,
                          },
                          {
                            path: "landing-page",
                            name: "LandingPage",
                            component: LandingPage,
                          },
                          {
                            path: "landing-page-remarketing",
                            name: "LandingPageRemarketing",
                            component: LandingPageRemarketing,
                          },
                          {
                            path: "remarketing-meta-ads",
                            name: "RemarketingMetaAds",
                            component: RemarketingMetaAds,
                          },
                          {
                            path: "email-marketing-flow",
                            children: [
                              {
                                path: "",
                                name: "EmailMarketingFlow",
                                component: EmailMarketingFlow,
                              },
                              {
                                path: "reminder-and-value",
                                name: "ReminderAndValue",
                                component: ReminderAndValue,
                              },
                            ],
                          },
                          {
                            path: "pain-points",
                            name: "PainPoints",
                            component: PainPoints,
                          },
                          {
                            path: "case-studies",
                            name: "CaseStudies",
                            component: CaseStudies,
                          },
                          {
                            path: "urgency",
                            name: "Urgency",
                            component: Urgency,
                          },
                          {
                            path: "special-offer",
                            name: "SpecialOffer",
                            component: SpecialOffer,
                          },
                          {
                            path: "whatsapp-bot-funnel",
                            children: [
                              {
                                path: "",
                                name: "WhatsappBotFunnel",
                                component: WhatsappBotFunnel,
                              },
                              {
                                path: "settings",
                                name: "WhatsappBotFunnelSettings",
                                component: Settings,
                              },
                            ],
                          },
                        ],
                      },
                    ],
                  },
                ],
              },
            ],
          },
        ],
      },
    ],
  },
];

// Register guest route names
registerGuestRouteNames(routes);

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior(to, _from, savedPosition) {
    if (to.hash) {
      return {
        el: to.hash,
      };
    }

    if (savedPosition) {
      return savedPosition;
    }

    return { top: 0 };
  },
});

usePostHog();

// Load locale messages on demand when the URL locale changes
// https://vue-i18n.intlify.dev/guide/advanced/lazy
router.beforeEach(async (to) => {
  const paramsLocale = (to.params.locale as string) || defaultAppLocale.code;

  if (!SUPPORT_LOCALES.includes(paramsLocale)) {
    return {
      ...to,
      params: {
        ...to.params,
        locale: defaultAppLocale.code,
      },
    };
  }

  if (!i18n.global.availableLocales.includes(paramsLocale)) {
    await loadLocaleMessages(paramsLocale as Locale);
  }

  setI18nLanguage(paramsLocale as Locale);
});

// Check auth token and permissions before each route
router.beforeEach(async (to) => {
  const authStore = useAuthStore();

  if (to.matched.some((record) => record.meta.requiresAuth)) {
    // If the route requires authentication, check if the user is logged in
    if (await authStore.hasActiveSession()) {
      const allowed = await authStore.hasAccessToRoute(to);

      if (allowed) {
        // Allowed, proceed to route
        return;
      }

      if (to.meta.permissionRedirectTo) {
        // Redirect to a specific route given in the route meta
        return to.meta.permissionRedirectTo;
      }

      // Redirect to a safe home page if user lacks required permissions
      console.warn("User lacks required permissions for this route");
      return { name: "BrandList" };
    } else {
      handleSessionExpired("router_guard_no_token", to.fullPath);
      return false;
    }
  } else {
    if (isGuestRouteName(to.name) && (await authStore.hasActiveSession())) {
      const postLoginTarget = resolvePostLoginRedirect(
        router,
        to.query[AUTH_REDIRECT_QUERY_KEY],
      );

      return postLoginTarget ?? { name: "BrandList" };
    }
  }
});

// Force reload when a module cannot be loaded (e.g. after a new deployment)
router.onError((error) => {
  if (
    error.message.includes("Failed to fetch dynamically imported module") ||
    error.message.includes("Importing a module script failed")
  ) {
    window.location.reload();
    return;
  }
});

export default router;

router.afterEach((to) => {
  try {
    const fullPath =
      to.fullPath || window.location.pathname + window.location.search;
    window._hsq = window._hsq || [];
    window._hsq.push(["setPath", fullPath]);
    window._hsq.push(["trackPageView"]);
  } catch (_) {
    // no-op
  }
});
