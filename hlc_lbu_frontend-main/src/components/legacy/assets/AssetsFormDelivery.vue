<script setup lang="ts">
import { toTypedSchema } from "@vee-validate/yup";
import { array, object, string } from "yup";
import { AssetsFormData } from "./AssetsForm.vue";
import AssetsApi from "@/services/legacy/AssetsApi";
import CampaignsApi from "@/services/projects/CampaignsApi";
import { InferOutput } from "vee-validate";

const { t } = useI18n();

const brandId = useBrandId();
const projectId = useProjectId();
const campaignId = useCampaignId();
const { data: campaign } = await CampaignsApi.getOne(
  brandId,
  projectId,
  campaignId,
);

const { data: initialData } = await AssetsApi.getAssetDelivery(
  brandId,
  projectId,
  campaignId,
);

const { goBack } = useMultiStepFormContext<AssetsFormData>();

const schema = computed(() =>
  toTypedSchema(
    object({
      campaign_name: string().required(t("forms.required-field")),
      type: string().required(t("forms.required-field")),
      bperson: object({
        title: string().nullable(),
        image_url: string().nullable(),
        persona_journey: string().required(t("forms.required-field")),
        persona_profile: string().required(t("forms.required-field")),
        persona_challenges: string().required(t("forms.required-field")),
        persona_motivation: string().required(t("forms.required-field")),
      }).required(),
      product: object({
        title: string().nullable(),
        image_url: string().nullable(),
        core_incentive_offer: string().required(t("forms.required-field")),
        problem_solution_fit: string().required(t("forms.required-field")),
        emotional_outcome_payoff: string().required(t("forms.required-field")),
        unique_value_proposition: string().required(t("forms.required-field")),
      }).required(),
      campaign: object({
        title: string().nullable(),
        image_url: string().nullable(),
        campaign_kpis: string().required(t("forms.required-field")),
        campaign_goals: string().required(t("forms.required-field")),
        campaign_resources: string().required(t("forms.required-field")),
        campaign_concept_timing: string().required(t("forms.required-field")),
      }).required(),
      masters: array()
        .of(
          object({
            title: string().required(t("forms.required-field")),
            horizontal: string().nullable().url(),
            square: string().nullable().url(),
            vertical: string().nullable().url(),
          }),
        )
        .required(),
    }),
  ),
);

type Masters = InferOutput<typeof schema.value>["masters"][number];

const { handleSubmit, isSubmitting, values, meta } = useFormWithErrorScrolling({
  validationSchema: schema,
  initialValues: {
    campaign_name: initialData.campaign_name ?? campaign.name,
    type: initialData.type,
    bperson: {
      persona_profile: initialData.summary.bperson.persona_profile,
      persona_challenges: initialData.summary.bperson.persona_challenges,
      persona_journey: initialData.summary.bperson.persona_journey,
      persona_motivation: initialData.summary.bperson.persona_motivation,
      image_url: initialData.summary.bperson.image_url || undefined,
    },
    product: {
      core_incentive_offer: initialData.summary.product.core_incentive_offer,
      problem_solution_fit: initialData.summary.product.problem_solution_fit,
      unique_value_proposition:
        initialData.summary.product.unique_value_proposition,
      emotional_outcome_payoff:
        initialData.summary.product.emotional_outcome_payoff,
      image_url: initialData.summary.product.image_url || undefined,
    },
    campaign: {
      campaign_concept_timing:
        initialData.summary.campaign.campaign_concept_timing,
      campaign_goals: initialData.summary.campaign.campaign_goals,
      campaign_resources: initialData.summary.campaign.campaign_resources,
      campaign_kpis: initialData.summary.campaign.campaign_kpis,
      image_url: initialData.summary.campaign.image_url || undefined,
    },
    masters: initialData.masters.map((master) => ({
      title: master.title,
      horizontal: master.images[0].horizontal,
      square: master.images[1].square,
      vertical: master.images[2].vertical,
    })),
  },
});

const onSubmit = handleSubmit(async (values) => {
  await AssetsApi.saveAssetDelivery(brandId, projectId, campaignId, {
    campaign_name: values.campaign_name,
    type: values.type,
    summary: {
      bperson: values.bperson,
      campaign: values.campaign,
      product: values.product,
    },
    masters: values.masters.map((master, index) => ({
      id: index,
      title: master.title,
      images: [
        { horizontal: master.horizontal ?? null },
        { square: master.square ?? null },
        { vertical: master.vertical ?? null },
      ],
    })),
  });
});

const { remove, push, fields } = useFieldArray<Masters>("masters");

const handleAddMaster = () => {
  push({
    title: `Master ${fields.value.length + 1}`,
    horizontal: undefined,
    square: undefined,
    vertical: undefined,
  });
};

const handleRemoveMaster = (index: number) => {
  remove(index);
};

const copyRootElement = ref<HTMLDivElement>();
const { copy, isCopying } = useCopyElementToClipboard(copyRootElement);
</script>

<template>
  <FormStepLayout @submit.prevent="onSubmit">
    <PageTitle helpButton>
      {{ $t("campaigns.assets.delivery.title") }}

      <template #description>
        {{ $t("campaigns.assets.delivery.description") }}
      </template>
    </PageTitle>

    <div class="tw:hidden"></div>

    <CardBase class="tw:flex tw:flex-col tw:gap-8 tw:p-6">
      <FieldEditableText
        name="campaign_name"
        required
        class="tw:text-2xl tw:font-extrabold"
        variant="text"
      />

      <Separator />

      <AssetsFormDeliverySection
        icon="tabler:template"
        iconVariant="primary"
        :imageSrc="initialData.summary.bperson.image_url"
      >
        <template #title
          >{{ $t("campaigns.assets.delivery.sectiononetitle") }}
        </template>

        <FieldTextarea
          name="bperson.persona_profile"
          label="Persona Profile"
          required
        />

        <FieldTextarea
          name="bperson.persona_challenges"
          label="Persona Challenges"
          required
        />

        <FieldTextarea
          name="bperson.persona_journey"
          label="Persona Journey"
          required
        />

        <FieldTextarea
          name="bperson.persona_motivation"
          label="Persona Motivation"
          required
        />
      </AssetsFormDeliverySection>

      <Separator />

      <AssetsFormDeliverySection
        icon="tabler:speakerphone"
        iconVariant="info"
        :imageSrc="initialData.summary.campaign.image_url"
      >
        <template #title
          >{{ $t("campaigns.assets.delivery.sectiotwotitle") }}
        </template>

        <FieldTextarea
          name="campaign.campaign_concept_timing"
          label="Campaign Concept & Timing"
          required
        />

        <FieldTextarea
          name="campaign.campaign_goals"
          label="Campaign Goals"
          required
        />

        <FieldTextarea
          name="campaign.campaign_resources"
          label="Resources"
          required
        />

        <FieldTextarea
          name="campaign.campaign_kpis"
          label="Campaign KPIs"
          required
        />
      </AssetsFormDeliverySection>

      <Separator />

      <AssetsFormDeliverySection
        icon="ion:cube"
        iconVariant="success"
        :imageSrc="initialData.summary.product.image_url"
      >
        <template #title>{{
          $t("campaigns.assets.delivery.sectionthreetitle")
        }}</template>

        <FieldTextarea
          name="product.core_incentive_offer"
          label="Core Incentive / Offer"
          required
        />

        <FieldTextarea
          name="product.problem_solution_fit"
          label="Problem/Solution Fit"
          required
        />

        <FieldTextarea
          name="product.unique_value_proposition"
          label="Unique Value Proposition"
          required
        />

        <FieldTextarea
          name="product.emotional_outcome_payoff"
          label="Emotional Outcome / Payoff"
          required
        />
      </AssetsFormDeliverySection>
    </CardBase>

    <Separator />

    <div class="tw:flex tw:flex-col tw:gap-6">
      <div>
        <h2 class="tw:text-2xl tw:font-extrabold">
          {{ $t("campaigns.assets.delivery.campaigncreativesssetstitle") }}
        </h2>
        <p class="tw:text-sm">
          {{
            $t("campaigns.assets.delivery.campaigncreativesssetsdescription")
          }}
        </p>
      </div>

      <CardBase
        v-for="(_master, index) in fields"
        class="tw:flex tw:flex-col tw:gap-6 tw:p-6"
      >
        <div class="tw:flex">
          <FieldEditableText
            :name="`masters.${index}.title`"
            required
            class="tw:grow tw:text-lg tw:font-extrabold"
            variant="text"
          />

          <Tooltip>
            <Button
              icon="tabler-x"
              size="sm"
              variant="text"
              color="error"
              type="button"
              @click="handleRemoveMaster(index)"
            />

            <template #content
              >{{ $t("campaigns.assets.delivery.removetext") }}
            </template>
          </Tooltip>
        </div>

        <Separator />

        <div class="tw:flex tw:flex-col tw:gap-8 tw:lg:flex-row">
          <AssetsFormDeliveryImageField
            :name="`masters.${index}.horizontal`"
            label="Horizontal Image"
          />

          <AssetsFormDeliveryImageField
            :name="`masters.${index}.square`"
            label="Square Image"
          />

          <AssetsFormDeliveryImageField
            :name="`masters.${index}.vertical`"
            label="Vertical Image"
          />
        </div>
      </CardBase>

      <Button
        leftIcon="tabler-plus"
        variant="label"
        type="button"
        @click="handleAddMaster"
      >
        {{ $t("campaigns.assets.delivery.addmastertext") }}
      </Button>
    </div>

    <Separator />

    <div class="tw:flex tw:justify-end">
      <Button
        leftIcon="tabler-copy"
        variant="outlined"
        type="button"
        @click="copy"
        :isLoading="isCopying"
      >
        {{ $t("campaigns.assets.delivery.buttoncopytoclipboardtext") }}
      </Button>
    </div>

    <!-- Template to copy to clipboard -->
    <div
      class="tw:bg-white tw:select-all"
      :class="{ 'tw:hidden': !isCopying }"
      ref="copyRootElement"
    >
      <AssetsEmailTemplate :values="values" />
    </div>

    <template #actions>
      <WizardCardActions>
        <ButtonGoBack @click="goBack()" />

        <Button :isLoading="isSubmitting" class="tw:basis-[300px]">
          {{ t("global.save") }}
        </Button>
      </WizardCardActions>
    </template>

    <ModalFormSaveAlert :isDirty="meta.dirty" />
  </FormStepLayout>
</template>
