<script lang="ts" setup>
import HandReviewApi from "@/services/funnel-flow/paid-social/HandReviewApi";
import { FunnelPaidSocialFormData } from "../FunnelPaidSocialForm.vue";
const { t } = useI18n();

const { goNext } = useMultiStepFormContext<FunnelPaidSocialFormData>();

const brandId = useBrandId();
const campaignId = useCampaignId();
const projectId = useProjectId();

const uploadDocModal = ref<boolean>(false);

const launchCampaignModal = ref<boolean>(false);
const uploadErrorsModal = ref<boolean>(false);

const uploadErrors = ref<string[]>([]);

const selectedFile = ref<File | null>(null);

const fileInputRef = ref<HTMLInputElement | null>(null);

async function handleDownloadExcel() {
  const data = await HandReviewApi.DownloadExcel({
    campaign_id: campaignId,
    brand_id: brandId,
    project_id: projectId,
  });

  downloadBlob(data, "campaign_report.xlsx");
}

function triggerFileInput() {
  fileInputRef.value?.click();
}

async function handleFileChange(event: Event) {
  const target = event.target as HTMLInputElement;
  const file = target.files?.[0];
  if (!file) return;

  selectedFile.value = file;
  uploadDocModal.value = true;

  target.value = "";
}

async function handleConfirmUpload() {
  if (!selectedFile.value) {
    return;
  }

  try {
    await HandReviewApi.UploadExcel(selectedFile.value, {
      brand_id: brandId,
      campaign_id: campaignId,
    });

    selectedFile.value = null;
    launchCampaignModal.value = true;
  } catch (error: any) {
    uploadErrors.value = error?.errors
      ? error.errors
      : error.error
        ? [error.error]
        : [
            t(
              "funnel-flow.paid-social.form-review-attachment.modals.upload-errors.default-error",
            ),
          ];

    uploadErrorsModal.value = true;
  } finally {
    uploadDocModal.value = false;
  }
}
</script>

<template>
  <FormStepLayout>
    <PageTitle>
      {{ t("funnel-flow.paid-social.form-review-attachment.page-title.title") }}

      <template #description>
        {{
          t(
            "funnel-flow.paid-social.form-review-attachment.page-title.description",
          )
        }}
      </template>
    </PageTitle>

    <CardGrid>
      <PermissionGuard
        :requires="[{ name: 'APPROVAL_PROCESS', actions: ['R'] }]"
      >
        <SuggestionCard imageSrc="/images/emojis/inbox-tray.png">
          <template #description>
            {{
              t(
                "funnel-flow.paid-social.form-review-attachment.cards.download-excel.description",
              )
            }}
          </template>

          <template #action>
            <Button
              @click="handleDownloadExcel"
              class="tw:w-full"
              type="button"
            >
              {{
                t(
                  "funnel-flow.paid-social.form-review-attachment.cards.download-excel.action",
                )
              }}
            </Button>
          </template>
        </SuggestionCard>
      </PermissionGuard>

      <PermissionGuard
        :requires="[{ name: 'APPROVAL_PROCESS', actions: ['C', 'U'] }]"
      >
        <SuggestionCard imageSrc="/images/emojis/emoji-floppy-disk.png">
          <template #description>
            {{
              t(
                "funnel-flow.paid-social.form-review-attachment.cards.upload-excel.description",
              )
            }}
          </template>

          <template #action>
            <Button @click="triggerFileInput" class="tw:w-full" type="button">
              {{
                t(
                  "funnel-flow.paid-social.form-review-attachment.cards.upload-excel.action",
                )
              }}
            </Button>

            <input
              ref="fileInputRef"
              type="file"
              accept=".xlsx,.xls"
              class="tw:hidden"
              @change="handleFileChange"
            />
          </template>
        </SuggestionCard>
      </PermissionGuard>
    </CardGrid>

    <Modal v-model="uploadDocModal" class="tw:p-10" :maxWidth="660" closeButton>
      <div class="tw:mb-5 tw:flex tw:justify-center">
        <img class="tw:w-[100px]" src="/images/emoji-rocket.png" alt="" />
      </div>
      <h3 class="tw:mb-5 tw:text-center tw:text-2xl tw:font-bold">
        {{
          t(
            "funnel-flow.paid-social.form-review-attachment.modals.upload-doc.title",
          )
        }}
      </h3>
      <p class="tw:mb-5 tw:text-center">
        {{
          t(
            "funnel-flow.paid-social.form-review-attachment.modals.upload-doc.description",
          )
        }}
      </p>
      <div class="tw:flex tw:justify-center tw:gap-5">
        <Button
          @click="uploadDocModal = false"
          :variant="'outlined'"
          class="tw:mx-auto tw:w-full"
        >
          {{ t("global.cancel") }}
        </Button>
        <Button @click="handleConfirmUpload" class="tw:mx-auto tw:w-full">
          {{
            t(
              "funnel-flow.paid-social.form-review-attachment.modals.upload-doc.actions.publish",
            )
          }}
        </Button>
      </div>
    </Modal>

    <Modal
      v-model="launchCampaignModal"
      class="tw:p-10"
      :maxWidth="660"
      closeButton
    >
      <div class="tw:mb-5 tw:flex tw:justify-center">
        <img class="tw:w-[120px]" src="/images/celebrar-image.png" alt="" />
      </div>
      <h3 class="tw:mb-5 tw:text-center tw:text-2xl tw:font-bold">
        {{
          t(
            "funnel-flow.paid-social.form-review-attachment.modals.launch-campaign.title",
          )
        }}
      </h3>
      <p class="tw:mb-5 tw:text-center">
        {{
          t(
            "funnel-flow.paid-social.form-review-attachment.modals.launch-campaign.description",
          )
        }}
      </p>
      <div class="tw:flex tw:justify-center tw:gap-5">
        <Button
          @click="
            () => {
              launchCampaignModal = false;
              goNext();
            }
          "
          class="tw:mx-auto tw:w-full tw:sm:w-2/5"
        >
          {{
            t(
              "funnel-flow.paid-social.form-review-attachment.modals.launch-campaign.actions.back",
            )
          }}
        </Button>
      </div>
    </Modal>

    <Modal
      v-model="uploadErrorsModal"
      class="tw:p-10"
      :maxWidth="660"
      closeButton
    >
      <h3 class="tw:mb-5 tw:text-center tw:text-2xl tw:font-bold">
        {{
          t(
            "funnel-flow.paid-social.form-review-attachment.modals.upload-errors.title",
          )
        }}
      </h3>
      <p class="tw:mb-5 tw:font-bold">
        {{
          t(
            "funnel-flow.paid-social.form-review-attachment.modals.upload-errors.description",
          )
        }}
      </p>

      <ul class="tw:list-disc tw:pl-5">
        <li v-for="error in uploadErrors" :key="error">
          {{ error }}
        </li>
      </ul>
    </Modal>

    <template #actions>
      <!-- <WizardCardActions>
        <ButtonGoBack @click="goBack" />
        <Button>
          {{
            t(
              "funnel-flow.paid-social.form-review-attachment.actions.launch-campaign",
            )
          }}
        </Button>
      </WizardCardActions> -->
    </template>
  </FormStepLayout>
</template>
