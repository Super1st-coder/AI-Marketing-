<script lang="ts" setup>
import { object, string } from "yup";
import { toTypedSchema } from "@vee-validate/yup";
import { useRoute, useRouter } from "vue-router";
import {
  createEmailAPI,
  GenericEmailWithPreheader,
} from "@/services/legacy/EmailsAPI";
import { BaseApiResponseData } from "@/utils/type-declarations";

const props = defineProps<{
  api: ReturnType<
    typeof createEmailAPI<BaseApiResponseData<any>, GenericEmailWithPreheader>
  >;
}>();

const router = useRouter();
const route = useRoute();

// Fetch the email or generate it
const projectId = parseInt(route.params.id as string);
const response = await props.api.getOrGenerate(projectId);

const { handleSubmit, values } = useFormWithErrorScrolling({
  initialValues: {
    subjectLine: response.data[props.api.fieldName]?.["Subject Line"],
    introduction: response.data[props.api.fieldName]?.["Introduction"],
    body: response.data[props.api.fieldName]?.["Body"],
    videoCta: response.data[props.api.fieldName]?.["Video CTA"],
    objectionsAndReassurance:
      response.data[props.api.fieldName]?.["Objections and Reassurance"],
    closingAndFinalCta:
      response.data[props.api.fieldName]?.["Closing and Final CTA"],
    preheader: response.data[props.api.fieldName]?.["Preheader"],
  },
  validationSchema: toTypedSchema(
    object().shape({
      subjectLine: string().required(),
      introduction: string().required(),
      body: string().required(),
      videoCta: string().required(),
      objectionsAndReassurance: string().required(),
      closingAndFinalCta: string().required(),
      preheader: string().required(),
    }),
  ),
  keepValuesOnUnmount: true,
});

const isLoading = ref(false);
const onSubmit = handleSubmit(async (values) => {
  isLoading.value = true;

  // Send data
  await props.api.save(projectId, {
    "Subject Line": values.subjectLine,
    Introduction: values.introduction,
    Body: values.body,
    "Video CTA": values.videoCta,
    "Objections and Reassurance": values.objectionsAndReassurance,
    "Closing and Final CTA": values.closingAndFinalCta,
    Preheader: values.preheader,
  });

  isLoading.value = false;
  router.push({ name: "EmailMarketingFlow" });
});
//#endregion
</script>

<template>
  <WizardCard paddingY="lg">
    <form
      @submit="onSubmit"
      class="tw:flex tw:flex-col tw:gap-[40px] tw:lg:gap-[60px]"
    >
      <div>
        <WizardCardTitle>
          <slot name="title" />
          <template #button>
            <HelpButton> Help info </HelpButton>
          </template>
        </WizardCardTitle>

        <WizardCardParagraph>
          <slot name="description" />
        </WizardCardParagraph>
      </div>

      <div class="tw:grid tw:gap-[60px] tw:lg:grid-cols-2">
        <div class="tw:lg:order-last">
          <EmailTemplate>
            <template #subjectLine>
              {{ values.subjectLine }}
            </template>

            <p class="tw:whitespace-break-spaces">
              {{ values.introduction }}
            </p>
            <br />

            <p class="tw:whitespace-break-spaces">{{ values.body }}</p>
            <br />

            <p class="tw:whitespace-break-spaces">{{ values.videoCta }}</p>
            <br />

            <Button size="md" color="secondary" type="button">
              APPLY NOW
            </Button>
            <br />
            <br />

            <p class="tw:whitespace-break-spaces">
              {{ values.objectionsAndReassurance }}
            </p>

            <br />
            <p class="tw:whitespace-break-spaces">
              {{ values.closingAndFinalCta }}
            </p>
          </EmailTemplate>
        </div>

        <div>
          <div class="tw:mb-[60px] tw:flex tw:flex-col tw:gap-5">
            <h2 class="tw:text-lg tw:font-extrabold">Subject line</h2>

            <EditableCardSection
              name="subjectLine"
              title="Subject Line"
              icon="tabler-box"
              iconVariant="primary"
              editable
            />
          </div>

          <div class="tw:flex tw:flex-col tw:gap-5">
            <h2 class="tw:text-lg tw:font-extrabold">Email body</h2>

            <EditableCardSection
              name="introduction"
              title="Introduction"
              icon="tabler-box"
              iconVariant="primary"
              editable
            />

            <EditableCardSection
              name="body"
              title="Body"
              icon="tabler-file-text"
              iconVariant="success"
              editable
            />

            <EditableCardSection
              name="videoCta"
              title="Video CTA"
              icon="tabler-box"
              iconVariant="primary"
              editable
            />

            <EditableCardSection
              name="objectionsAndReassurance"
              title="Objections and reassurance"
              icon="tabler-file-text"
              iconVariant="success"
              editable
            />

            <EditableCardSection
              name="closingAndFinalCta"
              title="Closing and Final CTA"
              icon="tabler-box"
              iconVariant="primary"
              editable
            />
          </div>
        </div>
      </div>

      <WizardCardActions>
        <WizardButtonGoBack :to="{ name: 'EmailMarketingFlow' }" />

        <WizardButtonNext :isLoading="isLoading"> SAVE EMAIL </WizardButtonNext>
      </WizardCardActions>
    </form>
  </WizardCard>
</template>
