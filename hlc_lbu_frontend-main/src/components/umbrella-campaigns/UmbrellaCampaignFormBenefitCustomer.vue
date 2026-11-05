<script setup lang="ts">
import { UnidentifiedError } from "@/services/common-errors";
import UmbrellaCampaignsApi, {
  UmbrellaCampaignData,
} from "@/services/projects/UmbrellaCampaignsApi";
import { toTypedSchema } from "@vee-validate/yup";
import { array, number, object, string } from "yup";

const { t } = useI18n();

const brandId = useBrandId();
const projectId = useProjectId();

const { goBack, goNext, data, saveData } =
  useMultiStepFormContext<UmbrellaCampaignData>();

const schema = computed(() =>
  toTypedSchema(
    object().shape({
      base_resource: string().required(t("forms.required-field")),
      exchangeable_resource: string().required(t("forms.required-field")),

      product_to_customer: string().required(t("forms.required-field")).trim(),
      customer_to_product: string().required(t("forms.required-field")).trim(),

      benefit_reasoning: string().required(t("forms.required-field")).trim(),

      preferred_benefit: number().required(t("forms.required-field")),
      benefits: array()
        .of(
          object({
            id: number().required(),
            title: string().required(t("forms.required-field")).trim(),
            text: string().required(t("forms.required-field")).trim(),
            preferred: number().required(),
          }),
        )
        .required(),
    }),
  ),
);

const {
  handleSubmit,
  validateField,
  setFieldValue,
  scrollToFirstError,
  values,
  isSubmitting,
  meta,
} = useFormWithErrorScrolling({
  validationSchema: schema,
  initialValues: {
    base_resource: data.value.bperson_resource_base?.name,
    exchangeable_resource: data.value.bperson_resource_exchangeable?.name,
    product_to_customer: data.value.resource_exchange?.product_to_customer,
    customer_to_product: data.value.resource_exchange?.customer_to_product,
    benefit_reasoning: data.value.benefit_reasoning ?? undefined,
    benefits: data.value.benefits ?? undefined,
    preferred_benefit: data.value.preferred_benefit?.id,
  },
});

const onSubmit = handleSubmit(async (values) => {
  const bperson_resource_base = data.value.bperson_resources?.find(
    (resource) => resource.name === values.base_resource,
  );
  const bperson_resource_exchangeable = data.value.bperson_resources?.find(
    (resource) => resource.name === values.exchangeable_resource,
  );

  if (!bperson_resource_base || !bperson_resource_exchangeable) {
    throw new UnidentifiedError();
  }

  const response1 = await UmbrellaCampaignsApi.saveGeneratedBenefits(
    brandId,
    projectId,
    data.value.id,
    {
      bperson_resource_base,
      bperson_resource_exchangeable,
      resource_exchange: {
        customer_to_product: values.customer_to_product,
        product_to_customer: values.product_to_customer,
      },
      benefit_reasoning: values.benefit_reasoning,
      benefits: values.benefits,
    },
  );
  saveData(response1.data);

  const response2 = await UmbrellaCampaignsApi.setPreferredBenefit(
    brandId,
    projectId,
    data.value.id,
    values.preferred_benefit,
  );
  saveData(response2.data);

  goNext();
});

const isInfoAvailable = ref(
  data.value.resource_exchange?.product_to_customer &&
    data.value.resource_exchange?.customer_to_product &&
    data.value.benefit_reasoning
    ? true
    : false,
);

const handleClickGenerate = async () => {
  const { valid: isBaseResourceValid } = await validateField("base_resource");
  const { valid: isExchangeableResourceValid } = await validateField(
    "exchangeable_resource",
  );

  if (!isBaseResourceValid || !isExchangeableResourceValid) {
    await scrollToFirstError();
    return;
  }

  const bperson_resource_base = data.value.bperson_resources?.find(
    (resource) => resource.name === values.base_resource,
  );
  const bperson_resource_exchangeable = data.value.bperson_resources?.find(
    (resource) => resource.name === values.exchangeable_resource,
  );

  if (!bperson_resource_base || !bperson_resource_exchangeable) {
    throw new UnidentifiedError();
  }

  // Generate data
  const response = await UmbrellaCampaignsApi.generateResourceExchange(
    brandId,
    projectId,
    data.value.id,
    {
      bperson_resource_base,
      bperson_resource_exchangeable,
    },
  );

  // Save data
  setFieldValue(
    "product_to_customer",
    response.data.answer.resource_exchange.product_to_customer,
  );
  setFieldValue(
    "customer_to_product",
    response.data.answer.resource_exchange.customer_to_product,
  );
  setFieldValue("benefit_reasoning", response.data.answer.benefit_reasoning);

  isInfoAvailable.value = true;
};

const areBenefitsAvailable = ref(!!data.value.benefits);

const getCommonParametersForGeneration = async () => {
  const { valid: isBaseResourceValid } = await validateField("base_resource");
  const { valid: isExchangeableResourceValid } = await validateField(
    "exchangeable_resource",
  );
  const { valid: isProductAudienceValid } = await validateField(
    "product_to_customer",
  );
  const { valid: isAudienceProductValid } = await validateField(
    "customer_to_product",
  );
  const { valid: isBenefitReasoningValid } =
    await validateField("benefit_reasoning");

  // Check needed fields
  if (
    !isBaseResourceValid ||
    !isExchangeableResourceValid ||
    !isProductAudienceValid ||
    !isAudienceProductValid ||
    !isBenefitReasoningValid
  ) {
    await scrollToFirstError();
    return;
  }

  const bperson_resource_base = data.value.bperson_resources?.find(
    (resource) => resource.name === values.base_resource,
  );
  const bperson_resource_exchangeable = data.value.bperson_resources?.find(
    (resource) => resource.name === values.exchangeable_resource,
  );

  if (
    !values.benefit_reasoning ||
    !values.customer_to_product ||
    !values.product_to_customer ||
    !bperson_resource_base ||
    !bperson_resource_exchangeable
  ) {
    throw new UnidentifiedError();
  }

  return {
    bperson_resource_base,
    bperson_resource_exchangeable,
    benefit_reasoning: values.benefit_reasoning,
    resource_exchange: {
      customer_to_product: values.customer_to_product,
      product_to_customer: values.product_to_customer,
    },
  };
};

const handleClickGenerateBenefits = async () => {
  const commonParameters = await getCommonParametersForGeneration();
  if (!commonParameters) {
    return;
  }

  // Generate data
  const response = await UmbrellaCampaignsApi.generateBenefits(
    brandId,
    projectId,
    data.value.id,
    {
      ...commonParameters,
    },
  );

  // Save data
  setFieldValue("benefits", response.data.answer);
  setFieldValue("preferred_benefit", undefined);

  areBenefitsAvailable.value = true;
};

const handleSelect = async (index: number) => {
  setFieldValue("preferred_benefit", index);
  setFieldValue(`benefits.${index}.preferred`, 1);
  // await onSubmit();
};

const regenerateBenefitList = async (text: string) => {
  const commonParameters = await getCommonParametersForGeneration();
  if (!commonParameters) {
    return;
  }

  const response = await UmbrellaCampaignsApi.askLucaForBenefits(
    brandId,
    projectId,
    data.value.id,
    {
      text,
      ...commonParameters,
    },
  );

  setFieldValue("benefits", response.data.answer);
  setFieldValue("preferred_benefit", undefined);

  return response.data.answer;
};

const regenerateSingleBenefit = (index: number) => {
  return async (text: string) => {
    const commonParameters = await getCommonParametersForGeneration();
    if (!commonParameters) {
      return;
    }

    const currentBenefit = values.benefits?.[index];
    if (!currentBenefit) return;

    const response = await UmbrellaCampaignsApi.askLucaForOneBenefit(
      brandId,
      projectId,
      data.value.id,
      {
        text,
        benefit_selected: currentBenefit,
        ...commonParameters,
      },
    );

    setFieldValue(`benefits.${index}`, response.data.answer);

    return response.data.answer;
  };
};
</script>

<template>
  <FormStepLayout @submit.prevent="onSubmit" :disabled="isSubmitting">
    <template #stepper>
      <MultiStepFormStepper parentStepName="benefit" />
    </template>

    <PageTitle
      helpButton
      helpVideoUrl="https://www.youtube.com/watch?v=HUAj5DwpfsA"
    >
      {{ t("umbrella-campaign.step-benefit.customer-benefit.title") }}
      <template #description>
        {{ t("umbrella-campaign.step-benefit.customer-benefit.description") }}
      </template>
    </PageTitle>

    <div class="tw:flex tw:flex-col tw:gap-7 tw:md:flex-row">
      <FieldSelect
        name="base_resource"
        :placeholder="
          t(
            'umbrella-campaign.step-benefit.customer-benefit.base-resource-placeholder',
          )
        "
        :options="
          data.bperson_resources?.map(({ name, text }) => ({
            label: `${t(`umbrella-campaign.step-benefit.resources.${name}.display_name`)} - ${text}`,
            value: name,
          })) ?? []
        "
        class="tw:grow"
      />

      <Icon icon="tabler-plus" class="tw:shrink-0 tw:text-2xl tw:md:mt-3" />

      <FieldSelect
        name="exchangeable_resource"
        :placeholder="
          t(
            'umbrella-campaign.step-benefit.customer-benefit.exchangeable-resource-placeholder',
          )
        "
        :options="
          data.bperson_resources?.map(({ name, text }) => ({
            label: `${t(`umbrella-campaign.step-benefit.resources.${name}.display_name`)} - ${text}`,
            value: name,
          })) ?? []
        "
        class="tw:grow"
      />
    </div>

    <div class="tw:w-fit">
      <ButtonRegenerate
        :regenerate="isInfoAvailable"
        :fetcher="handleClickGenerate"
      />
    </div>

    <template v-if="isInfoAvailable">
      <Separator />

      <CardBase class="tw:flex tw:flex-col tw:gap-5 tw:p-4">
        <CardTitle
          >🔗
          {{
            t(
              "umbrella-campaign.step-benefit.customer-benefit.resource-exchange-title",
            )
          }}</CardTitle
        >

        <FieldTextarea
          name="product_to_customer"
          :label="
            t(
              'umbrella-campaign.step-benefit.customer-benefit.product-to-customer-label',
            )
          "
          required
        />

        <FieldTextarea
          name="customer_to_product"
          :label="
            t(
              'umbrella-campaign.step-benefit.customer-benefit.customer-to-product-label',
            )
          "
          required
        />
      </CardBase>

      <CardBase class="tw:flex tw:flex-col tw:gap-5 tw:p-4">
        <CardTitle
          >🧠
          {{
            t("umbrella-campaign.step-benefit.customer-benefit.reasoning-title")
          }}</CardTitle
        >

        <FieldTextarea name="benefit_reasoning" required />
      </CardBase>

      <div class="tw:w-fit">
        <ButtonRegenerate
          :regenerate="areBenefitsAvailable"
          :fetcher="handleClickGenerateBenefits"
        >
          <template #generate>
            {{
              $t(
                "umbrella-campaign.step-benefit.customer-benefit.button-generate-benefits",
              )
            }}
          </template>

          <template #regenerate>
            {{
              $t(
                "umbrella-campaign.step-benefit.customer-benefit.button-regenerate-benefits",
              )
            }}
          </template>
        </ButtonRegenerate>
      </div>
    </template>

    <template v-if="areBenefitsAvailable">
      <Separator />

      <CardTitle iconVariant="success" icon="tabler-gift">
        {{
          t(
            "umbrella-campaign.step-benefit.customer-benefit.benefit-proposals-title",
          )
        }}
      </CardTitle>

      <div class="tw:flex tw:justify-end">
        <ButtonGenerateIdea
          :fetcher="regenerateBenefitList"
          useText
          color="primary"
          :textPlaceholder="
            $t(
              'umbrella-campaign.step-benefit.customer-benefit.ask-luca-modal.placeholder',
            )
          "
          :textMaxCharacters="250"
        >
          <template #title>
            {{
              t(
                "umbrella-campaign.step-benefit.customer-benefit.ask-luca-modal.title",
              )
            }}
          </template>

          <template #description>
            {{
              t(
                "umbrella-campaign.step-benefit.customer-benefit.ask-luca-modal.description",
              )
            }}
          </template>

          <template #submit>
            {{
              t(
                "umbrella-campaign.step-benefit.customer-benefit.ask-luca-modal.submit",
              )
            }}
          </template>

          {{ $t("global.ask-luca") }}
        </ButtonGenerateIdea>
      </div>
      <CardGrid>
        <CardBase
          v-for="(benefit, index) in values.benefits"
          class="tw:flex tw:flex-col tw:gap-4 tw:p-6"
          :color="
            values.preferred_benefit === benefit.id ? 'primary' : 'default'
          "
        >
          <FieldEditableText
            :name="`benefits.${index}.title`"
            required
            class="tw:mb-1 tw:text-lg tw:leading-tight tw:font-extrabold"
            variant="text"
          />

          <FieldEditableText :name="`benefits.${index}.text`" required />

          <div class="tw:flex tw:flex-col tw:gap-2">
            <ButtonGenerateIdea
              :fetcher="regenerateSingleBenefit(index)"
              useText
              color="primary"
              size="sm"
              variant="outlined"
              class="tw:bg-white"
              :textPlaceholder="
                $t(
                  'umbrella-campaign.step-benefit.customer-benefit.ask-luca-modal.placeholder',
                )
              "
              :textMaxCharacters="250"
            >
              <template #title>
                {{
                  t(
                    "umbrella-campaign.step-benefit.customer-benefit.ask-luca-modal.title",
                  )
                }}
              </template>

              <template #description>
                {{
                  t(
                    "umbrella-campaign.step-benefit.customer-benefit.ask-luca-modal.description",
                  )
                }}
              </template>

              <template #submit>
                {{
                  t(
                    "umbrella-campaign.step-benefit.customer-benefit.ask-luca-modal.submit",
                  )
                }}
              </template>

              {{ $t("global.ask-luca") }}
            </ButtonGenerateIdea>

            <Button
              class="tw:w-full"
              type="button"
              @click="handleSelect(index)"
              size="sm"
              :isLoading="index === values.preferred_benefit && isSubmitting"
              :disabled="index !== values.preferred_benefit && isSubmitting"
            >
              {{
                t(
                  "umbrella-campaign.step-benefit.customer-benefit.button-select-benefit",
                )
              }}
            </Button>
          </div>
        </CardBase>
      </CardGrid>
    </template>

    <template #actions>
      <WizardCardActions>
        <ButtonGoBack @click="goBack" />
        <ButtonNext :isLoading="isSubmitting" />
      </WizardCardActions>
    </template>

    <ModalFormSaveAlert :isDirty="meta.dirty" />
  </FormStepLayout>
</template>
