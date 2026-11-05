<script lang="ts" setup>
import { object, string } from "yup";
import { toTypedSchema } from "@vee-validate/yup";
import { useRoute, useRouter } from "vue-router";
import EmailsAPI from "@/services/legacy/EmailsAPI";

const router = useRouter();
const route = useRoute();

// Fetch the email or generate it
const projectId = parseInt(route.params.id as string);
const response = await EmailsAPI.Reminder.getOrGenerate(projectId);

const { handleSubmit, values } = useFormWithErrorScrolling({
  initialValues: {
    subjectLine: response.data.email_reminder_generated["Subject Line"],
    introduction: response.data.email_reminder_generated.Introduction,
    body: response.data.email_reminder_generated.Body,
    videoCta: response.data.email_reminder_generated["Video CTA"],
    objectionsAndReassurance:
      response.data.email_reminder_generated["Objections and Reassurance"],
    closingAndFinalCta:
      response.data.email_reminder_generated["Closing and Final CTA"],
  },
  validationSchema: toTypedSchema(
    object().shape({
      subjectLine: string().required(),
      introduction: string().required(),
      body: string().required(),
      videoCta: string().required(),
      objectionsAndReassurance: string().required(),
      closingAndFinalCta: string().required(),
    }),
  ),
  keepValuesOnUnmount: true,
});

const isLoading = ref(false);
const onSubmit = handleSubmit(async (values) => {
  isLoading.value = true;

  // Send data
  await EmailsAPI.Reminder.save(projectId, {
    "Subject Line": values.subjectLine,
    Introduction: values.introduction,
    Body: values.body,
    "Video CTA": values.videoCta,
    "Objections and Reassurance": values.objectionsAndReassurance,
    "Closing and Final CTA": values.closingAndFinalCta,
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
          Reminder and Value Email
          <template #button>
            <HelpButton> Help info </HelpButton>
          </template>
        </WizardCardTitle>

        <WizardCardParagraph>
          This email is aimed at reminding the user about their sign-up and
          reinforcing the value they’re missing out on.
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

            <!-- <EditableCardSection
              name="previewText"
              title="Preview Text"
              icon="tabler-file-text"
              iconVariant="success"
              editable
            /> -->
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
