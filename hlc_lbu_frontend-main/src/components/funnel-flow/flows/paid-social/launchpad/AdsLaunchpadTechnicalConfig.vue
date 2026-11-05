<script setup lang="ts">
import ChannelConnections, {
  LEADS_CONVERSION_EVENTS,
  type AdAccount,
  type CampaignObjective,
  type LeadsConversionEvent,
} from "@/services/funnel-flow/ChannelConnections";
import { toTypedSchema } from "@vee-validate/yup";
import { boolean, number, object, string } from "yup";
import { SelectOption } from "@/components/forms/base/FieldBaseSelect.vue";
import { useFunnelPaidSocialLaunchpadPreCheckStore } from "@/stores/funnel-flow/paid-social/FunnelPaidSocialLaunchpadPreCheckStore";
import AdChannelDestinationCard from "@/components/channels/AdChannelDestinationCard.vue";

const { goNext, goBack } = useMultiStepFormContext();
const { t, te } = useI18n();

const brandId = useBrandId();
const campaignId = useCampaignId();
const projectId = useProjectId();
const preCheckStore = useFunnelPaidSocialLaunchpadPreCheckStore();

// State
const isAuthenticated = ref(false);
const campaignObjectivesData = ref<CampaignObjective[]>([]);
const isCampaignSetupOpen = ref(false);
const isCampaignModeOpen = ref(false);

// Submit state
const convertModalOpen = ref(false);
const generalErrorMessage = ref<string | undefined>(undefined);

// Fetch campaign objectives
async function fetchCampaignObjectives() {
  const response = await ChannelConnections.getCampaignObjectives();
  campaignObjectivesData.value = response.data;
}

// Icon mappings for campaign objectives and optimization goals
const campaignObjectiveIcons: Record<string, string> = {
  OUTCOME_AWARENESS: "tabler:eye",
  OUTCOME_TRAFFIC: "tabler:click",
  OUTCOME_SALES: "tabler:shopping-cart",
  OUTCOME_LEADS: "tabler:speakerphone",
};

const optimizationGoalIcons: Record<string, string> = {
  REACH: "tabler:target",
  IMPRESSIONS: "tabler:eye",
  AD_RECALL_LIFT: "tabler:clipboard-list",
  THRUPLAY: "tabler:video",
  TWO_SECOND_CONTINUOUS_VIDEO_VIEWS: "tabler:hourglass",
  LEAD_GENERATION: "tabler:speakerphone",
  QUALITY_LEAD: "tabler:award",
  CONVERSATIONS: "tabler:brand-whatsapp",
  OFFSITE_CONVERSIONS: "tabler:shopping-cart",
  VALUE: "tabler:coin",
  LANDING_PAGE_VIEWS: "tabler:world",
  LINK_CLICKS: "tabler:click",
};

// Campaign objectives options
const campaignObjective = computed(() => {
  return campaignObjectivesData.value
    .map((objective) => ({
      value: objective.id,
      label: t(`meta-ads.objectives.${objective.id}.title`, objective.id),
      icon: campaignObjectiveIcons[objective.id] ?? "tabler:question-mark",
      disabled: !objective.active,
    }))
    .sort((a, b) => Number(a.disabled) - Number(b.disabled));
});

// Optimization goals options
const optimizationGoals = computed(() => {
  const selectedObjectiveId = values.campaign_objetive;

  if (!selectedObjectiveId) {
    return [];
  }

  // Find the selected objective
  const selectedObjective = campaignObjectivesData.value.find(
    (obj) => obj.id === selectedObjectiveId,
  );

  let goals = selectedObjective?.goals || [];

  if (selectedObjectiveId === "OUTCOME_LEADS" && goals.length === 0) {
    goals = [
      { id: "LEAD_GENERATION", billing_event: "IMPRESSIONS" },
      { id: "QUALITY_LEAD", billing_event: "IMPRESSIONS" },
      { id: "CONVERSATIONS", billing_event: "IMPRESSIONS" },
    ];
  }

  // Map the selected objective goals to options
  return goals.map((goal) => ({
    value: goal.id,
    label: t(
      `meta-ads.objectives.${selectedObjectiveId}.optimization-goals.${goal.id}.title`,
      goal.id,
    ),
    icon:
      (isLeadsOffsiteCombo(selectedObjectiveId, goal.id)
        ? "tabler:user-plus"
        : optimizationGoalIcons[goal.id]) ?? "tabler:question-mark",
  }));
});

const STANDARD_COMPATIBLE_COMBOS = [
  { objective: "OUTCOME_AWARENESS", goal: "REACH" },
  { objective: "OUTCOME_LEADS", goal: "CONVERSATIONS" },
  { objective: "OUTCOME_SALES", goal: "OFFSITE_CONVERSIONS" },
  { objective: "OUTCOME_LEADS", goal: "LEAD_GENERATION" },
  { objective: "OUTCOME_LEADS", goal: "OFFSITE_CONVERSIONS" },
];

// Leads optimized for conversions on the website, tracked with a pixel event
function isLeadsOffsiteCombo(objective?: string | null, goal?: string | null) {
  return objective === "OUTCOME_LEADS" && goal === "OFFSITE_CONVERSIONS";
}

function requiresPixel(objective?: string | null, goal?: string | null) {
  return objective === "OUTCOME_SALES" || isLeadsOffsiteCombo(objective, goal);
}

const conversionEventOptions = computed<SelectOption[]>(() =>
  LEADS_CONVERSION_EVENTS.map((event) => ({
    value: event,
    label: t(`meta-ads.conversion-events.${event}.title`, event),
  })),
);

// Preselected when choosing Leads optimized for conversions
const DEFAULT_LEADS_CONVERSION_EVENT: LeadsConversionEvent =
  "COMPLETE_REGISTRATION";

// Budget strategy (behind ENABLE_BUDGET_STRATEGY until the back-end supports it)
const BUDGET_STRATEGIES = ["CBO", "ABO"] as const;
const ABO_BUDGET_SETUPS = ["EVENLY", "PRE_CHECK"] as const;
// Values follow Meta's `bid_strategy` enum
const BID_STRATEGIES = [
  "LOWEST_COST_WITHOUT_CAP",
  "COST_CAP",
  "LOWEST_COST_WITH_BID_CAP",
] as const;
const BUDGET_TYPES = ["DAILY", "LIFETIME"] as const;

// The bid strategy, budget and schedule are set here for CBO, or for ABO
// when the budget is split evenly. Otherwise they are set in the Pre-check
function isBudgetFormShown(
  budgetStrategy?: string | null,
  aboBudgetSetup?: string | null,
) {
  return (
    budgetStrategy === "CBO" ||
    (budgetStrategy === "ABO" && aboBudgetSetup === "EVENLY")
  );
}

// Meta requires a schedule for lifetime budgets
function isScheduleRequired(
  budgetStrategy?: string | null,
  aboBudgetSetup?: string | null,
  budgetType?: string | null,
) {
  return (
    isBudgetFormShown(budgetStrategy, aboBudgetSetup) &&
    budgetType === "LIFETIME"
  );
}

const budgetStrategyOptions = computed(() =>
  BUDGET_STRATEGIES.map((strategy) => ({
    value: strategy,
    label: t(
      `funnel-flow.paid-social.launchpad.technical-config.budget-strategy.options.${strategy}.title`,
    ),
    description: t(
      `funnel-flow.paid-social.launchpad.technical-config.budget-strategy.options.${strategy}.description`,
    ),
  })),
);

const aboBudgetSetupOptions = computed(() =>
  ABO_BUDGET_SETUPS.map((setup) => ({
    value: setup,
    label: t(
      `funnel-flow.paid-social.launchpad.technical-config.budget-strategy.abo-setup.options.${setup}.title`,
    ),
    description: t(
      `funnel-flow.paid-social.launchpad.technical-config.budget-strategy.abo-setup.options.${setup}.description`,
    ),
  })),
);

const bidStrategyOptions = computed<SelectOption[]>(() =>
  BID_STRATEGIES.map((strategy) => ({
    value: strategy,
    label: t(
      `funnel-flow.paid-social.launchpad.technical-config.budget-strategy.bid-strategy.options.${strategy}`,
    ),
  })),
);

const budgetTypeOptions = computed<SelectOption[]>(() =>
  BUDGET_TYPES.map((type) => ({
    value: type,
    label: t(
      `funnel-flow.paid-social.launchpad.technical-config.budget-strategy.budget-type.options.${type}`,
    ),
  })),
);

// Validation schema
const schema = computed(() =>
  toTypedSchema(
    object({
      add_account: string().required(t("forms.required-field")),
      business_page: string().required(t("forms.required-field")),
      campaign_objetive: string().required(t("forms.required-field")),
      optimization_goal: string().required(t("forms.required-field")),
      campaign_mode: string().required(t("forms.required-field")),
      lead_gen_form: string()
        .nullable()
        .when("campaign_objetive", {
          is: "OUTCOME_LEADS",
          then: (schema) =>
            schema.when("optimization_goal", {
              is: (val: string) =>
                ["LEAD_GENERATION", "QUALITY_LEAD"].includes(val),
              then: (s) => s.required(t("forms.required-field")),
            }),
        }),
      whatsapp_number: string()
        .nullable()
        .when("campaign_objetive", {
          is: "OUTCOME_LEADS",
          then: (schema) =>
            schema.when("optimization_goal", {
              is: "CONVERSATIONS",
              then: (s) => s.required(t("forms.required-field")),
            }),
        }),
      pixel: string()
        .nullable()
        .when(["campaign_objetive", "optimization_goal"], {
          is: requiresPixel,
          then: (schema) => schema.required(t("forms.required-field")),
        }),
      conversion_event: string()
        .nullable()
        .when(["campaign_objetive", "optimization_goal"], {
          is: isLeadsOffsiteCombo,
          then: (schema) => schema.required(t("forms.required-field")),
        }),

      // Budget strategy
      budget_strategy: ENABLE_BUDGET_STRATEGY
        ? string().oneOf(BUDGET_STRATEGIES).required(t("forms.required-field"))
        : string().oneOf(BUDGET_STRATEGIES).nullable(),
      abo_budget_setup: string().oneOf(ABO_BUDGET_SETUPS).nullable(),
      bid_strategy: string()
        .oneOf(BID_STRATEGIES)
        .nullable()
        .when(["budget_strategy", "abo_budget_setup"], {
          is: isBudgetFormShown,
          then: (schema) => schema.required(t("forms.required-field")),
        }),
      budget_type: string()
        .oneOf(BUDGET_TYPES)
        .nullable()
        .when(["budget_strategy", "abo_budget_setup"], {
          is: isBudgetFormShown,
          then: (schema) => schema.required(t("forms.required-field")),
        }),
      budget_amount: number()
        .nullable()
        .when(["budget_strategy", "abo_budget_setup"], {
          is: isBudgetFormShown,
          then: (schema) =>
            schema
              .required(t("forms.required-field"))
              .moreThan(0, t("forms.greater-than", { min: 0 })),
        }),
      start_time: string()
        .nullable()
        .when(["budget_strategy", "abo_budget_setup", "budget_type"], {
          is: isScheduleRequired,
          then: (schema) => schema.required(t("forms.required-field")),
        }),
      end_time: string()
        .nullable()
        .when(["budget_strategy", "abo_budget_setup", "budget_type"], {
          is: isScheduleRequired,
          then: (schema) => schema.required(t("forms.required-field")),
        })
        .test(
          "after-start",
          t(
            "funnel-flow.paid-social.launchpad.technical-config.budget-strategy.errors.end-before-start",
          ),
          function (endTime) {
            const startTime = this.parent.start_time as string | undefined;

            if (!endTime || !startTime) {
              return true;
            }

            return new Date(endTime) > new Date(startTime);
          },
        ),
      has_spending_limit: boolean(),
      spending_limit: number()
        .nullable()
        .when("has_spending_limit", {
          is: true,
          then: (schema) =>
            schema
              .required(t("forms.required-field"))
              .moreThan(0, t("forms.greater-than", { min: 0 })),
        }),
    }),
  ),
);

// Configuration of the current launch, so coming back to this step shows what
// was submitted, or what the published campaign was launched with, instead of
// an empty form
const launchConfiguration = preCheckStore.launchConfiguration;
const initialValues = {
  add_account: launchConfiguration?.ad_account_id,
  business_page: launchConfiguration?.page_id,
  campaign_objetive: launchConfiguration?.objective,
  optimization_goal: launchConfiguration?.optimization_goal,
  campaign_mode: launchConfiguration?.creative_type,
  lead_gen_form: launchConfiguration?.lead_gen_form_id ?? undefined,
  whatsapp_number: launchConfiguration?.whatsapp_number_id ?? undefined,
  pixel: launchConfiguration?.pixel_id ?? undefined,
  conversion_event: launchConfiguration?.conversion_event ?? undefined,
  // TODO: restore the budget strategy from `launchConfiguration` once the
  // back-end returns it
  budget_strategy: undefined,
  abo_budget_setup: undefined,
  bid_strategy: undefined,
  budget_type: undefined,
  budget_amount: undefined,
  start_time: undefined,
  end_time: undefined,
  has_spending_limit: false,
  spending_limit: undefined,
};

// Form handling
const { handleSubmit, isSubmitting, meta, values, resetForm, setFieldValue } =
  useFormWithErrorScrolling({
    validationSchema: schema,
    initialValues,
  });

// Budget strategy state
const isBudgetStrategyShown = computed(
  () => ENABLE_BUDGET_STRATEGY && !!values.optimization_goal,
);

const isBudgetFormVisible = computed(() =>
  isBudgetFormShown(values.budget_strategy, values.abo_budget_setup),
);

const isScheduleFieldRequired = computed(() =>
  isScheduleRequired(
    values.budget_strategy,
    values.abo_budget_setup,
    values.budget_type,
  ),
);

const destinationCardRef = ref<InstanceType<typeof AdChannelDestinationCard>>();

const selectedAdAccountCurrency = computed(() => {
  const account = getSelectedAdAccount(
    destinationCardRef.value?.accounts ?? [],
  );

  return account?.currency ?? account?.account_currency;
});

// Clear the fields of the budget form when it's hidden, so they don't keep
// stale values for the request
watch(isBudgetFormVisible, (isVisible) => {
  if (isVisible) {
    return;
  }

  setFieldValue("bid_strategy", undefined, false);
  setFieldValue("budget_type", undefined, false);
  setFieldValue("budget_amount", undefined, false);
  setFieldValue("start_time", undefined, false);
  setFieldValue("end_time", undefined, false);
});

watch(
  () => values.budget_strategy,
  (strategy) => {
    if (strategy !== "ABO") {
      setFieldValue("abo_budget_setup", undefined, false);
    }
  },
);

watch(
  () => values.has_spending_limit,
  (hasSpendingLimit) => {
    if (!hasSpendingLimit) {
      setFieldValue("spending_limit", undefined, false);
    }
  },
);

const isStandardModeCompatible = computed(() =>
  STANDARD_COMPATIBLE_COMBOS.some(
    (combo) =>
      combo.objective === values.campaign_objetive &&
      combo.goal === values.optimization_goal,
  ),
);

const campaignModes = computed(() => [
  {
    value: "DYNAMIC",
    label: t("meta-ads.campaign-modes.DYNAMIC.title", "DYNAMIC"),
    icon: "tabler:cube",
    description: t("meta-ads.campaign-modes.DYNAMIC.description", ""),
  },
  {
    value: "STANDARD",
    label: t("meta-ads.campaign-modes.STANDARD.title", "STANDARD"),
    icon: "tabler:photo",
    description: t("meta-ads.campaign-modes.STANDARD.description", ""),
    disabled: !isStandardModeCompatible.value,
  },
]);

const isStandardMode = computed(() => values.campaign_mode === "STANDARD");

watch(isStandardModeCompatible, (isCompatible) => {
  if (!isCompatible && isStandardMode.value) {
    setFieldValue("campaign_mode", undefined);
  }
});

const isLeadFormRequired = computed(
  () =>
    values.campaign_objetive === "OUTCOME_LEADS" &&
    !!values.optimization_goal &&
    ["LEAD_GENERATION", "QUALITY_LEAD"].includes(values.optimization_goal),
);

const isWhatsAppRequired = computed(
  () =>
    values.campaign_objetive === "OUTCOME_LEADS" &&
    values.optimization_goal === "CONVERSATIONS",
);

const isPixelRequired = computed(() =>
  requiresPixel(values.campaign_objetive, values.optimization_goal),
);

const isConversionEventRequired = computed(() =>
  isLeadsOffsiteCombo(values.campaign_objetive, values.optimization_goal),
);

const isCampaignModeDisabled = computed(
  () =>
    !values.add_account ||
    !values.business_page ||
    !values.campaign_objetive ||
    !values.optimization_goal ||
    (isPixelRequired.value && !values.pixel) ||
    (isConversionEventRequired.value && !values.conversion_event) ||
    (isLeadFormRequired.value && !values.lead_gen_form) ||
    (isWhatsAppRequired.value && !values.whatsapp_number) ||
    (ENABLE_BUDGET_STRATEGY && !values.budget_strategy),
);

function getSelectedAdAccount(accounts: AdAccount[]) {
  if (!values.add_account) {
    return undefined;
  }

  return accounts.find((account) => account.account_id === values.add_account);
}

function handleDisconnect() {
  pixelErrorMessage.value = undefined;
  resetForm({
    values: {
      add_account: undefined,
      business_page: undefined,
      campaign_objetive: undefined,
      optimization_goal: undefined,
      campaign_mode: undefined,
      lead_gen_form: undefined,
      whatsapp_number: undefined,
      pixel: undefined,
      conversion_event: undefined,
      budget_strategy: undefined,
      abo_budget_setup: undefined,
      bid_strategy: undefined,
      budget_type: undefined,
      budget_amount: undefined,
      start_time: undefined,
      end_time: undefined,
      has_spending_limit: false,
      spending_limit: undefined,
    },
  });
}

// Picking a campaign mode card opens its confirmation/info modal.
const previousCampaignMode = ref<string | undefined>(undefined);
let isRevertingCampaignMode = false;

watch(
  () => values.campaign_mode,
  (mode, oldMode) => {
    if (isRevertingCampaignMode) {
      isRevertingCampaignMode = false;
      return;
    }

    if (!mode) {
      return;
    }

    previousCampaignMode.value = oldMode;
    convertModalOpen.value = true;
  },
);

// Undo the pending mode selection when the confirmation modal is dismissed
// without confirming, restoring whatever was selected before it was opened.
function handleConvertModalDismiss() {
  isRevertingCampaignMode = true;
  setFieldValue("campaign_mode", previousCampaignMode.value);
}

const formsOptions = ref<SelectOption[]>([]);
const isFetchingForms = ref(false);

async function fetchForms(pageId: string) {
  if (!pageId) return;
  isFetchingForms.value = true;
  try {
    const res = await ChannelConnections.getLeadgenForms(pageId);
    formsOptions.value = (res.data || []).map((form: any) => ({
      label: form.name,
      value: form.id,
    }));
  } catch (error) {
    console.error("Failed to fetch leadgen forms:", error);
    formsOptions.value = [];
  } finally {
    isFetchingForms.value = false;
  }
}

const whatsappOptions = ref<SelectOption[]>([]);
const isFetchingWhatsApp = ref(false);

async function fetchWhatsAppNumbers(pageId: string) {
  if (!pageId) return;
  isFetchingWhatsApp.value = true;
  try {
    const res = await ChannelConnections.getWhatsAppPhoneNumbers(pageId);
    whatsappOptions.value = res.data.map((num) => ({
      label:
        num.display_phone_number +
        (num.verified_name ? ` (${num.verified_name})` : ""),
      value: num.id,
      chip:
        num.code_verification_status !== "VERIFIED"
          ? {
              label: t(
                "funnel-flow.paid-social.launchpad.technical-config.whatsapp-not-verified",
              ),
              color: "warning",
            }
          : undefined,
    }));
  } catch (error) {
    console.error("Failed to fetch WhatsApp numbers:", error);
    whatsappOptions.value = [];
  } finally {
    isFetchingWhatsApp.value = false;
  }
}

const pixelOptions = ref<SelectOption[]>([]);
const isFetchingPixels = ref(false);
const pixelErrorMessage = ref<string | undefined>(undefined);

function resolveTechnicalConfigError(error: any, fallbackKey: string) {
  const code = error?.message?.code as string | undefined;
  const text = error?.message?.text as string | undefined;
  const i18nErrorKey = code
    ? `funnel-flow.paid-social.launchpad.technical-config.errors.${code}`
    : undefined;

  if (i18nErrorKey && te(i18nErrorKey)) {
    return t(i18nErrorKey);
  }

  if (text) {
    return text;
  }

  return t(fallbackKey);
}

async function fetchPixels(adAccountId: string) {
  if (!adAccountId) return;
  isFetchingPixels.value = true;
  pixelErrorMessage.value = undefined;
  try {
    const res = await ChannelConnections.getPixelsByAccount(adAccountId);
    pixelOptions.value = res.data.map((pixel) => ({
      label: pixel.name || pixel.id,
      value: pixel.id,
    }));
  } catch (error) {
    console.error("Failed to fetch pixels:", error);
    pixelOptions.value = [];
    pixelErrorMessage.value = resolveTechnicalConfigError(
      error,
      "funnel-flow.paid-social.launchpad.technical-config.errors.pixels-fallback",
    );
  } finally {
    isFetchingPixels.value = false;
  }
}

watch(
  [
    () => values.business_page,
    () => values.campaign_objetive,
    () => values.optimization_goal,
  ],
  async ([pageId, objective, goal], [oldPageId, oldObjective, oldGoal]) => {
    if (objective !== oldObjective) {
      setFieldValue("optimization_goal", undefined, false);
    }

    if (
      pageId !== oldPageId ||
      objective !== oldObjective ||
      goal !== oldGoal
    ) {
      setFieldValue("lead_gen_form", undefined);
      setFieldValue("whatsapp_number", undefined);
    }

    if (objective !== oldObjective || goal !== oldGoal) {
      setFieldValue(
        "conversion_event",
        isLeadsOffsiteCombo(objective, goal)
          ? DEFAULT_LEADS_CONVERSION_EVENT
          : undefined,
      );
    }

    if (!pageId) {
      formsOptions.value = [];
      whatsappOptions.value = [];
      return;
    }

    if (
      objective === "OUTCOME_LEADS" &&
      goal &&
      ["LEAD_GENERATION", "QUALITY_LEAD"].includes(goal)
    ) {
      await fetchForms(pageId);
    }

    if (objective === "OUTCOME_LEADS" && goal === "CONVERSATIONS") {
      await fetchWhatsAppNumbers(pageId);
    }
  },
);

watch(
  [() => values.add_account, () => values.campaign_objetive, isPixelRequired],
  async (
    [accountId, objective, pixelRequired],
    [oldAccountId, oldObjective, oldPixelRequired],
  ) => {
    if (
      accountId !== oldAccountId ||
      objective !== oldObjective ||
      pixelRequired !== oldPixelRequired
    ) {
      setFieldValue("pixel", undefined);
    }

    if (!accountId || !pixelRequired) {
      pixelOptions.value = [];
      pixelErrorMessage.value = undefined;
      return;
    }

    await fetchPixels(accountId);
  },
);

watch(
  () => values.add_account,
  async (account) => {
    if (!account) {
      return;
    }

    // Disconnecting the account while these requests are in flight makes the
    // remaining ones fail, so errors are caught to not reach the error boundary
    try {
      const accountInsights = await ChannelConnections.getInsights(account);
      console.log("Account insights:", accountInsights.data);

      const detailedAccountInsights = await ChannelConnections.getInsights(
        account,
        {
          level: "account",
          fields:
            "account_id,account_name,impressions,spend,reach,frequency,clicks,ctr,cpc,cpm,inline_link_clicks,inline_link_click_ctr,actions",
          date_preset: "last_30d",
          time_increment: "1",
        },
      );
      console.log("Detailed account insights:", detailedAccountInsights.data);

      const campaignInsights = await ChannelConnections.getInsights(account, {
        level: "campaign",
        fields: "campaign_id,campaign_name,impressions,spend,clicks,ctr,cpc",
        date_preset: "last_30d",
      });
      console.log("Campaign insights:", campaignInsights.data);
    } catch (error) {
      console.error("Failed to fetch account insights:", error);
    }
  },
);

// The watchers above only react to changes, so the option lists of the
// restored values are fetched here
async function fetchOptionsForInitialValues() {
  const { add_account, business_page, campaign_objetive, optimization_goal } =
    initialValues;

  if (business_page && campaign_objetive === "OUTCOME_LEADS") {
    if (
      optimization_goal &&
      ["LEAD_GENERATION", "QUALITY_LEAD"].includes(optimization_goal)
    ) {
      await fetchForms(business_page);
    }

    if (optimization_goal === "CONVERSATIONS") {
      await fetchWhatsAppNumbers(business_page);
    }
  }

  if (add_account && requiresPixel(campaign_objetive, optimization_goal)) {
    await fetchPixels(add_account);
  }
}

await fetchOptionsForInitialValues();

// Submit handler
const onSubmit = handleSubmit(async (values) => {
  generalErrorMessage.value = undefined;

  try {
    // TODO: send the budget strategy fields (budget_strategy, abo_budget_setup,
    // bid_strategy, budget_type, budget_amount, start_time, end_time,
    // spending_limit) once the back-end supports them, and remove the
    // ENABLE_BUDGET_STRATEGY flag (VITE_ENABLE_BUDGET_STRATEGY). The dates are
    // in local time (`YYYY-MM-DDTHH:mm`), so convert them to the format the
    // back-end expects (e.g. ISO 8601 with `new Date(value).toISOString()`)
    await preCheckStore.initialize(projectId, {
      brand_id: brandId,
      campaign_id: campaignId,
      ad_account_id: values.add_account,
      page_id: values.business_page,
      objective: values.campaign_objetive,
      optimization_goal: values.optimization_goal,
      creative_type: values.campaign_mode,
      daily_budget: null,
      lead_gen_form_id: values.lead_gen_form || null,
      whatsapp_number_id: values.whatsapp_number || null,
      pixel_id: values.pixel || null,
      conversion_event:
        (values.conversion_event as LeadsConversionEvent | undefined) || null,
    });
    goNext();
  } catch (error: any) {
    console.error("Failed to initialize pre-check:", error);
    generalErrorMessage.value = resolveTechnicalConfigError(
      error,
      "funnel-flow.paid-social.launchpad.technical-config.errors.fallback",
    );
  }
});
</script>

<template>
  <FormStepLayout as="form" @submit.prevent="onSubmit">
    <!-- Horizontal Stepper -->
    <template #stepper>
      <AdsLaunchpadStepper />
    </template>

    <PageTitle
      helpButton
      helpVideoUrl="https://www.youtube.com/watch?v=PS-LLZhhrJA"
    >
      {{ $t("funnel-flow.paid-social.launchpad.technical-config.page-title") }}

      <template #description>
        {{
          $t(
            "funnel-flow.paid-social.launchpad.technical-config.page-description",
          )
        }}
      </template>
    </PageTitle>

    <AdChannelDestinationCard
      ref="destinationCardRef"
      v-model:authenticated="isAuthenticated"
      @connect="fetchCampaignObjectives"
      @disconnect="handleDisconnect"
    >
      <template #selectors="{ accountOptions, pageOptions, accounts }">
        <FieldNewSelect
          :placeholder="$t('channels.ad-channel-destination.select-ad-account')"
          name="add_account"
          :options="accountOptions"
          required
          chips
        >
          <template v-if="getSelectedAdAccount(accounts)" #chip>
            <span class="tw:line-clamp-1">
              <span class="tw:text-primary-text">
                {{ getSelectedAdAccount(accounts)?.name }}
              </span>
              {{ " " }}
              <span class="tw:text-gray-500"> ({{ values.add_account }}) </span>
            </span>
          </template>
        </FieldNewSelect>

        <FieldAutocomplete
          :placeholder="
            $t('channels.ad-channel-destination.select-business-page')
          "
          name="business_page"
          :options="pageOptions"
          required
        />
      </template>
    </AdChannelDestinationCard>

    <AccordionList variant="card">
      <Accordion
        titleClass="tw:text-xl tw:font-bold"
        :disabled="!values.add_account || !values.business_page"
        openOnUnDisabled
        v-model="isCampaignSetupOpen"
      >
        <template #title>
          {{
            $t(
              "funnel-flow.paid-social.launchpad.technical-config.campaign-setup",
            )
          }}
        </template>

        <div class="tw:mt-5">
          <ButtonSelector
            v-if="campaignObjective.length > 0"
            name="campaign_objetive"
            :options="campaignObjective"
            :cols="4"
            :label="
              $t(
                'funnel-flow.paid-social.launchpad.technical-config.campaign-objective',
              )
            "
          />

          <Separator class="tw:my-5" v-if="optimizationGoals.length > 0" />

          <ButtonSelector
            v-if="optimizationGoals.length > 0"
            name="optimization_goal"
            :options="optimizationGoals"
            :cols="optimizationGoals.length === 2 ? 2 : 4"
            :label="
              $t(
                'funnel-flow.paid-social.launchpad.technical-config.optimization-goals',
              )
            "
          />

          <!-- Leadgen Form Selector -->
          <div v-if="isLeadFormRequired" class="tw:mt-5">
            <FieldAutocomplete
              :label="
                $t(
                  'funnel-flow.paid-social.launchpad.technical-config.leadgen-form-label',
                )
              "
              :placeholder="
                $t(
                  'funnel-flow.paid-social.launchpad.technical-config.select-leadgen-form',
                )
              "
              name="lead_gen_form"
              :options="formsOptions"
              :loading="isFetchingForms"
              leftIcon="tabler:forms"
              required
            />
          </div>

          <!-- WhatsApp Selector -->
          <div v-if="isWhatsAppRequired" class="tw:mt-5">
            <FieldAutocomplete
              :label="
                $t(
                  'funnel-flow.paid-social.launchpad.technical-config.whatsapp-number-label',
                )
              "
              :placeholder="
                $t(
                  'funnel-flow.paid-social.launchpad.technical-config.select-whatsapp-number',
                )
              "
              name="whatsapp_number"
              :options="whatsappOptions"
              :loading="isFetchingWhatsApp"
              leftIcon="tabler:brand-whatsapp"
              required
            />
          </div>

          <!-- Pixel Selector (Sales, and Leads optimized for conversions) -->
          <div v-if="isPixelRequired" class="tw:mt-5">
            <FieldAutocomplete
              :label="
                $t(
                  'funnel-flow.paid-social.launchpad.technical-config.pixel-label',
                )
              "
              :placeholder="
                $t(
                  'funnel-flow.paid-social.launchpad.technical-config.select-pixel',
                )
              "
              name="pixel"
              :options="pixelOptions"
              :loading="isFetchingPixels"
              leftIcon="heroicons:code-bracket-solid"
              required
            />

            <Alert
              v-if="pixelErrorMessage"
              type="error"
              class="tw:mt-4"
              autoScroll
            >
              {{ pixelErrorMessage }}
            </Alert>
          </div>

          <!-- Conversion Event Selector (Leads optimized for conversions) -->
          <div v-if="isConversionEventRequired" class="tw:mt-5">
            <FieldNewSelect
              :label="
                $t(
                  'funnel-flow.paid-social.launchpad.technical-config.conversion-event-label',
                )
              "
              :placeholder="
                $t(
                  'funnel-flow.paid-social.launchpad.technical-config.select-conversion-event',
                )
              "
              name="conversion_event"
              :options="conversionEventOptions"
              leftIcon="tabler:target-arrow"
              required
            />
          </div>

          <!-- Budget strategy -->
          <template v-if="isBudgetStrategyShown">
            <Separator class="tw:my-5" />

            <ButtonSelector
              name="budget_strategy"
              :options="budgetStrategyOptions"
              :cols="2"
              :label="
                $t(
                  'funnel-flow.paid-social.launchpad.technical-config.budget-strategy.label',
                )
              "
            />

            <div
              v-if="values.budget_strategy"
              class="tw:mt-4 tw:flex tw:flex-col tw:gap-4"
            >
              <div
                v-if="values.budget_strategy === 'ABO' || isBudgetFormVisible"
                class="tw:flex tw:flex-col tw:gap-5 tw:rounded-2xl tw:bg-gray-100 tw:p-4"
              >
                <!-- ABO: how the budget is set up for the ad sets -->
                <template v-if="values.budget_strategy === 'ABO'">
                  <ButtonSelector
                    name="abo_budget_setup"
                    :options="aboBudgetSetupOptions"
                    :cols="2"
                    :label="
                      $t(
                        'funnel-flow.paid-social.launchpad.technical-config.budget-strategy.abo-setup.label',
                      )
                    "
                    optional
                  />

                  <Alert
                    v-if="values.abo_budget_setup === 'PRE_CHECK'"
                    type="info"
                  >
                    {{
                      $t(
                        "funnel-flow.paid-social.launchpad.technical-config.budget-strategy.abo-setup.pre-check-info",
                      )
                    }}
                  </Alert>
                </template>

                <!-- Bid strategy, budget and schedule -->
                <template v-if="isBudgetFormVisible">
                  <FieldNewSelect
                    name="bid_strategy"
                    :label="
                      $t(
                        'funnel-flow.paid-social.launchpad.technical-config.budget-strategy.bid-strategy.label',
                      )
                    "
                    :placeholder="
                      $t(
                        'funnel-flow.paid-social.launchpad.technical-config.budget-strategy.bid-strategy.placeholder',
                      )
                    "
                    :options="bidStrategyOptions"
                    :clearable="false"
                    required
                  />

                  <div
                    class="tw:grid tw:grid-cols-1 tw:gap-5 tw:md:grid-cols-2"
                  >
                    <FieldNewSelect
                      name="budget_type"
                      :label="
                        $t(
                          'funnel-flow.paid-social.launchpad.technical-config.budget-strategy.budget-type.label',
                        )
                      "
                      :placeholder="
                        $t(
                          'funnel-flow.paid-social.launchpad.technical-config.budget-strategy.budget-type.placeholder',
                        )
                      "
                      :options="budgetTypeOptions"
                      :clearable="false"
                      required
                    />

                    <FieldMoney
                      name="budget_amount"
                      :label="
                        $t(
                          `funnel-flow.paid-social.launchpad.technical-config.budget-strategy.budget-amount.${values.budget_type ?? 'DAILY'}`,
                        )
                      "
                      :currency="selectedAdAccountCurrency"
                      useCurrencyIcon
                      required
                    />

                    <FieldDateTime
                      name="start_time"
                      :label="
                        $t(
                          'funnel-flow.paid-social.launchpad.technical-config.budget-strategy.start-time',
                        )
                      "
                      :max="values.end_time ?? undefined"
                      :required="isScheduleFieldRequired"
                      :optional="!isScheduleFieldRequired"
                    />

                    <FieldDateTime
                      name="end_time"
                      :label="
                        $t(
                          'funnel-flow.paid-social.launchpad.technical-config.budget-strategy.end-time',
                        )
                      "
                      :min="values.start_time ?? undefined"
                      :required="isScheduleFieldRequired"
                      :optional="!isScheduleFieldRequired"
                    />
                  </div>
                </template>
              </div>

              <!-- Campaign spending limit -->
              <CardBase borderRadius="md" :shadow="false" class="tw:p-4">
                <div class="tw:flex tw:items-start tw:gap-3">
                  <!-- The checkbox uses its `name` as the input id -->
                  <FieldCheckbox
                    name="has_spending_limit"
                    variant="switch"
                    size="lg"
                  />

                  <label for="has_spending_limit" class="tw:cursor-pointer">
                    <span class="tw:mb-1 tw:block tw:font-bold">
                      {{
                        $t(
                          "funnel-flow.paid-social.launchpad.technical-config.budget-strategy.spending-limit.label",
                        )
                      }}
                    </span>

                    <span class="tw:block tw:text-sm tw:text-secondary-text">
                      {{
                        $t(
                          "funnel-flow.paid-social.launchpad.technical-config.budget-strategy.spending-limit.description",
                        )
                      }}
                    </span>
                  </label>
                </div>

                <div
                  v-if="values.has_spending_limit"
                  class="tw:mt-4 tw:rounded-2xl tw:bg-gray-100 tw:p-4"
                >
                  <FieldMoney
                    name="spending_limit"
                    :label="
                      $t(
                        'funnel-flow.paid-social.launchpad.technical-config.budget-strategy.spending-limit.amount',
                      )
                    "
                    :currency="selectedAdAccountCurrency"
                    appendCodeToLabel
                    useCurrencyIcon
                    required
                  />
                </div>
              </CardBase>
            </div>
          </template>
        </div>
      </Accordion>

      <Accordion
        titleClass="tw:text-xl tw:font-bold"
        :disabled="isCampaignModeDisabled"
        openOnUnDisabled
        v-model="isCampaignModeOpen"
      >
        <template #title>
          {{
            $t(
              "funnel-flow.paid-social.launchpad.technical-config.select-campaign-mode",
            )
          }}
        </template>

        <ButtonSelector
          name="campaign_mode"
          :options="campaignModes"
          :cols="2"
        />
      </Accordion>
    </AccordionList>

    <Alert v-if="generalErrorMessage" type="error" autoScroll>
      {{ generalErrorMessage }}
    </Alert>

    <template #actions>
      <WizardCardActions>
        <ButtonGoBack @click="goBack" type="button" />

        <Button type="submit" :isLoading="isSubmitting" :disabled="!meta.valid">
          {{
            $t("funnel-flow.paid-social.launchpad.technical-config.next-steps")
          }}
        </Button>
      </WizardCardActions>
    </template>

    <!-- Dynamic Creative (DCO) conversion -->
    <ModalGeneric
      v-if="!isStandardMode"
      v-model="convertModalOpen"
      :maxWidth="520"
      @cancel="handleConvertModalDismiss"
      @close="handleConvertModalDismiss"
    >
      <template #title>
        {{
          $t(
            "funnel-flow.paid-social.launchpad.technical-config.dco-modal.title",
          )
        }}
      </template>

      <template #description>
        {{
          $t(
            "funnel-flow.paid-social.launchpad.technical-config.dco-modal.description",
          )
        }}
      </template>

      <!-- TODO: temporary Meta help article until Wizerlink provides the official DCO video/link -->
      <Link
        underline
        class="tw:text-sm tw:font-medium"
        external
        href="https://www.facebook.com/business/help/170372403538781"
      >
        {{
          $t(
            "funnel-flow.paid-social.launchpad.technical-config.dco-modal.watch-dco",
          )
        }}
      </Link>

      <template #cancel> {{ $t("global.cancel") }} </template>

      <template #continue>
        {{
          $t(
            "funnel-flow.paid-social.launchpad.technical-config.dco-modal.confirm-convert",
          )
        }}
      </template>
    </ModalGeneric>

    <!-- Standard campaign conversion -->
    <ModalGeneric
      v-else
      v-model="convertModalOpen"
      :maxWidth="520"
      @cancel="handleConvertModalDismiss"
      @close="handleConvertModalDismiss"
    >
      <template #title>
        {{
          $t(
            "funnel-flow.paid-social.launchpad.technical-config.standard-modal.title",
          )
        }}
      </template>

      <template #description>
        {{
          $t(
            "funnel-flow.paid-social.launchpad.technical-config.standard-modal.description",
          )
        }}
      </template>

      <p class="tw:font-medium">
        {{
          $t(
            "funnel-flow.paid-social.launchpad.technical-config.standard-modal.note",
          )
        }}
      </p>

      <template #cancel> {{ $t("global.cancel") }} </template>

      <template #continue>
        {{
          $t(
            "funnel-flow.paid-social.launchpad.technical-config.standard-modal.confirm-convert",
          )
        }}
      </template>
    </ModalGeneric>
  </FormStepLayout>
</template>
