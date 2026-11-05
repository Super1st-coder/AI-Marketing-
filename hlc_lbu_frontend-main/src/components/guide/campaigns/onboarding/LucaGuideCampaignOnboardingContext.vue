<script setup lang="ts">
import { AutocompleteOption } from "@/components/forms/base/FieldBaseAutocomplete.vue";
import LucaGuideCampaignsApi from "@/services/guide/LucaGuideCampaignsApi";
import LucaGuideLibraryApi from "@/services/guide/LucaGuideLibraryApi";
import { toTypedSchema } from "@vee-validate/yup";
import { object, string } from "yup";

const route = useRoute();
const router = useRouter();
const { goNext } = useMultiStepFormContext();

const campaignId = String(route.params.campaignId);
const brandId = String(route.params.brandId);

const [products, personas, projects, umbrellas, context] = await Promise.all([
  LucaGuideLibraryApi.listProducts(),
  LucaGuideLibraryApi.listPersonas(),
  LucaGuideLibraryApi.listProjects(),
  LucaGuideLibraryApi.listUmbrellaCampaigns(),
  LucaGuideCampaignsApi.getContext(campaignId),
]);

// Project is always the full list (it's what you pick to scope the rest).
const projectOptions: AutocompleteOption[] = projects.map((item) => ({
  value: item.id,
  label: item.name,
}));
// Product / Persona / Umbrella options are project-scoped — see the computed block below `values`.

// Marco #14-C: the 5th element lists EVERY campaign in the brand (not scoped to a project), each
// carrying its resolved LOCAL ancestry so selecting one auto-fills Umbrella→Project→Persona→Product.
const campaignOptions = ref<AutocompleteOption[]>([]);
const campaignsLoading = ref(false);
const campaignAncestry = new Map<
  string,
  {
    umbrella_id?: string;
    project_id?: string;
    product_id?: string;
    persona_id?: string;
  }
>();

async function loadBrandCampaigns() {
  campaignsLoading.value = true;
  try {
    const campaigns = await LucaGuideLibraryApi.listCampaigns(); // brand-wide (no project scope)
    campaignAncestry.clear();
    // PRD: only campaigns whose Builder Summary is saved are eligible to link.
    campaignOptions.value = campaigns
      .filter((c) => c.eligible)
      .map((c) => {
        campaignAncestry.set(c.id, {
          umbrella_id: c.umbrella_id ?? undefined,
          project_id: c.project_id ?? undefined,
          product_id: c.product_id ?? undefined,
          persona_id: c.persona_id ?? undefined,
        });
        return { value: c.id, label: c.name };
      });
  } finally {
    campaignsLoading.value = false;
  }
}

const schema = toTypedSchema(
  object({
    productId: string(),
    personaId: string(),
    projectId: string(),
    umbrellaCampaignId: string(),
    campaignId: string(),
  }),
);

const { handleSubmit, isSubmitting, values, setFieldValue } =
  useFormWithErrorScrolling({
    validationSchema: schema,
    initialValues: {
      productId: context?.product_id ?? undefined,
      personaId: context?.persona_id ?? undefined,
      projectId: context?.project_id ?? undefined,
      umbrellaCampaignId: context?.umbrella_campaign_id ?? undefined,
      campaignId: context?.linked_campaign_id ?? undefined,
    },
  });

// Marco #14 (ticket 14): when a Project is selected, scope the pickers to it — show only the
// Umbrellas under that Project, and only the Products / Target Customers those Umbrellas use
// ("This is Correct" — Marco). No Project selected → show everything brand-wide (unchanged).
// Umbrellas already carry project_id / product_id / buyer_persona_id, so this needs no extra fetch.
const umbrellasForProject = computed(() =>
  values.projectId
    ? umbrellas.filter((item) => item.project_id === values.projectId)
    : umbrellas,
);
const relatedProductIds = computed(
  () => new Set(umbrellasForProject.value.map((item) => item.product_id)),
);
const relatedPersonaIds = computed(
  () => new Set(umbrellasForProject.value.map((item) => item.buyer_persona_id)),
);

// The project filter scopes what you can NEWLY pick, but must never drop an already-selected value
// (e.g. one the campaign cascade set that sits outside the project's umbrellas) — otherwise the
// Autocomplete has no matching option and renders the raw id (UUID) instead of the name.
function toOptions<T extends { id: string; name: string }>(
  filtered: T[],
  all: T[],
  selectedId?: string,
): AutocompleteOption[] {
  const list =
    selectedId && !filtered.some((item) => item.id === selectedId)
      ? [...filtered, ...all.filter((item) => item.id === selectedId)]
      : filtered;
  return list.map((item) => ({ value: item.id, label: item.name }));
}

const productOptions = computed<AutocompleteOption[]>(() =>
  toOptions(
    values.projectId
      ? products.filter((item) => relatedProductIds.value.has(item.id))
      : products,
    products,
    values.productId,
  ),
);
const personaOptions = computed<AutocompleteOption[]>(() =>
  toOptions(
    values.projectId
      ? personas.filter((item) => relatedPersonaIds.value.has(item.id))
      : personas,
    personas,
    values.personaId,
  ),
);
const umbrellaOptions = computed<AutocompleteOption[]>(() =>
  toOptions(umbrellasForProject.value, umbrellas, values.umbrellaCampaignId),
);

const isUmbrellaModalOpen = ref(false);

// Load every brand campaign up front (no project needed) so the Campaign card is usable first.
await loadBrandCampaigns();

const linkedCount = computed(
  () =>
    [
      values.productId,
      values.personaId,
      values.projectId,
      values.umbrellaCampaignId,
      values.campaignId,
    ].filter(Boolean).length,
);

watch(
  () => values.umbrellaCampaignId,
  (id) => {
    if (!id) {
      // Unlink (X) → revert the derived parents to the initial state (Marco: clicking X on the
      // Umbrella/Campaign should clear everything, not leave stale parents behind).
      setFieldValue("productId", undefined);
      setFieldValue("personaId", undefined);
      setFieldValue("projectId", undefined);
      return;
    }

    const umbrella = umbrellas.find((item) => item.id === id);
    if (!umbrella) return;

    // OVERWRITE (not fill-only-if-empty): selecting/changing an Umbrella must re-derive its
    // Product/Persona/Project so everything matches it (Marco: the old "keep the stale value" was
    // the "not intuitive" bug — changing the umbrella didn't update the parents).
    setFieldValue("productId", umbrella.product_id);
    setFieldValue("personaId", umbrella.buyer_persona_id);
    setFieldValue("projectId", umbrella.project_id);
  },
);

// Marco #14-C: selecting a Campaign auto-fills (OVERWRITES) its whole chain so everything matches
// it; unlinking (X) reverts to the initial cleared state. Campaigns are brand-wide now, so the
// Project no longer scopes them (the old project→reload-campaigns watch is gone).
watch(
  () => values.campaignId,
  (id) => {
    if (!id) {
      setFieldValue("umbrellaCampaignId", undefined);
      setFieldValue("projectId", undefined);
      setFieldValue("productId", undefined);
      setFieldValue("personaId", undefined);
      return;
    }
    const a = campaignAncestry.get(id);
    if (!a) return;
    // Set the umbrella (its own watch cascades too) AND the parents explicitly — the umbrella may
    // be unsynced/null, so we fill from the campaign's own resolved ancestry as the source of truth.
    if (a.umbrella_id) setFieldValue("umbrellaCampaignId", a.umbrella_id);
    if (a.project_id) setFieldValue("projectId", a.project_id);
    if (a.product_id) setFieldValue("productId", a.product_id);
    if (a.persona_id) setFieldValue("personaId", a.persona_id);
  },
);

function handleGoBack() {
  router.push({ name: "LucaGuideCampaigns" });
}

const onSubmit = handleSubmit(async (formValues) => {
  await LucaGuideCampaignsApi.setContext(campaignId, {
    product_id: formValues.productId,
    persona_id: formValues.personaId,
    project_id: formValues.projectId,
    umbrella_campaign_id: formValues.umbrellaCampaignId,
    linked_campaign_id: formValues.campaignId,
  });
  goNext();
});
</script>

<template>
  <FormStepLayout as="form" :maxWidth="1096" @submit.prevent="onSubmit">
    <template #stepper>
      <MultiStepFormStepper />
    </template>

    <PageTitle>
      {{ $t("luca-guide.campaigns.onboarding.context.title") }}
      <template #description>
        {{ $t("luca-guide.campaigns.onboarding.context.description") }}
      </template>

      <!-- TODO: add View Campaign Team button -->
    </PageTitle>

    <Alert type="warning" expandable>
      <template #title>
        {{ $t("luca-guide.campaigns.onboarding.context.alert.title") }}
      </template>

      <template #custom>
        <p class="tw:mb-1">
          {{ $t("luca-guide.campaigns.onboarding.context.alert.description") }}
        </p>

        <ul class="tw:list-disc tw:space-y-1 tw:pl-5 tw:font-normal">
          <li>
            {{ $t("luca-guide.campaigns.onboarding.context.alert.item-1") }}
          </li>
          <li>
            {{ $t("luca-guide.campaigns.onboarding.context.alert.item-2") }}
          </li>
          <li>
            {{ $t("luca-guide.campaigns.onboarding.context.alert.item-3") }}
          </li>
        </ul>
      </template>
    </Alert>

    <div class="tw:flex tw:flex-col tw:gap-5">
      <div class="tw:flex tw:items-center tw:justify-between tw:gap-4">
        <h2 class="tw:font-bold tw:text-primary-text">
          {{ $t("luca-guide.campaigns.onboarding.context.link-your-context") }}
        </h2>

        <div
          class="tw:flex tw:items-center tw:gap-2 tw:text-sm tw:whitespace-nowrap"
        >
          <ProgressRing
            color="success"
            :diameter="16"
            :thickness="2"
            :progress="linkedCount / 5"
          />

          <i18n-t
            keypath="luca-guide.campaigns.onboarding.context.linked-progress"
          >
            <template #linked>
              <span class="tw:font-semibold">
                {{ $t("luca-guide.campaigns.onboarding.context.linked") }}
              </span>
            </template>

            <template #completed>
              <span class="tw:text-secondary-text">
                {{
                  $t("luca-guide.campaigns.onboarding.context.linked-count", {
                    count: linkedCount,
                  })
                }}
              </span>
            </template>
          </i18n-t>
        </div>
      </div>

      <div class="tw:grid tw:grid-cols-1 tw:gap-2.5 tw:lg:grid-cols-2">
        <LucaGuideCampaignOnboardingContextCard
          name="productId"
          :title="$t('luca-guide.campaigns.onboarding.context.product.title')"
          :description="
            $t('luca-guide.campaigns.onboarding.context.product.description')
          "
          :options="productOptions"
          :searchPlaceholder="
            $t(
              'luca-guide.campaigns.onboarding.context.product.search-placeholder',
            )
          "
          :createTo="{ name: 'CreateProduct', params: { brandId } }"
        />

        <LucaGuideCampaignOnboardingContextCard
          name="personaId"
          :title="
            $t('luca-guide.campaigns.onboarding.context.target-customer.title')
          "
          :description="
            $t(
              'luca-guide.campaigns.onboarding.context.target-customer.description',
            )
          "
          :options="personaOptions"
          :searchPlaceholder="
            $t(
              'luca-guide.campaigns.onboarding.context.target-customer.search-placeholder',
            )
          "
          :createTo="{ name: 'CreateBuyerPerson', params: { brandId } }"
        />

        <LucaGuideCampaignOnboardingContextCard
          name="projectId"
          :title="$t('luca-guide.campaigns.onboarding.context.project.title')"
          :description="
            $t('luca-guide.campaigns.onboarding.context.project.description')
          "
          :options="projectOptions"
          :searchPlaceholder="
            $t(
              'luca-guide.campaigns.onboarding.context.project.search-placeholder',
            )
          "
          :createTo="{ name: 'CreateProject', params: { brandId } }"
        />

        <LucaGuideCampaignOnboardingContextCard
          name="umbrellaCampaignId"
          :title="
            $t(
              'luca-guide.campaigns.onboarding.context.umbrella-campaign.title',
            )
          "
          :description="
            $t(
              'luca-guide.campaigns.onboarding.context.umbrella-campaign.description',
            )
          "
          :options="umbrellaOptions"
          :searchPlaceholder="
            $t(
              'luca-guide.campaigns.onboarding.context.umbrella-campaign.search-placeholder',
            )
          "
          @create="isUmbrellaModalOpen = true"
        />

        <!-- Marco #14-C: the 5th element lists EVERY brand campaign; picking one cascades the rest. -->
        <LucaGuideCampaignOnboardingContextCard
          name="campaignId"
          :title="$t('luca-guide.campaigns.onboarding.context.campaign.title')"
          :description="
            $t('luca-guide.campaigns.onboarding.context.campaign.description')
          "
          :options="campaignOptions"
          :loading="campaignsLoading"
          :searchPlaceholder="
            $t(
              'luca-guide.campaigns.onboarding.context.campaign.search-placeholder',
            )
          "
        />
      </div>
    </div>

    <LucaGuideCampaignOnboardingCreateUmbrellaModal
      v-model="isUmbrellaModalOpen"
    />

    <template #actions>
      <WizardCardActions>
        <ButtonGoBack @click="handleGoBack" />
        <Button
          type="submit"
          icon="tabler-arrow-right"
          :isLoading="isSubmitting"
        >
          {{ $t("luca-guide.campaigns.onboarding.continue-to-metrics") }}
        </Button>
      </WizardCardActions>
    </template>
  </FormStepLayout>
</template>
