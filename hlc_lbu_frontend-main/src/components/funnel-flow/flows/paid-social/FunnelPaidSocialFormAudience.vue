<script setup lang="ts">
import { FunnelPaidSocialFormData } from "./FunnelPaidSocialForm.vue";
import FunnelPaidSocialFormSideBar from "./FunnelPaidSocialFormSideBar.vue";
import {
  DeleteAudienceBody,
  Income,
  UpdatePreferredAudienceBody,
} from "@/services/projects/AudienceApi";
const { t, locale } = useI18n();

const { data, goNext, goBack } =
  useMultiStepFormContext<FunnelPaidSocialFormData>();

const brandId = useBrandId();
const campaignId = useCampaignId();

const wizard = useFunnelPaidSocialAudienceStore();
wizard.setContext({ brand: brandId, campaign: campaignId });

const showEndMsgModal = computed({
  get: () => wizard.showEndMsg,
  set: (value) => {
    if (!value) wizard.closeAllModals();
  },
});

const paidSocialFormStore = useFunnelPaidSocialFormStore();

const canProceedToCreativeAngle = computed(() =>
  paidSocialFormStore.areAllPreviousStepsCompleted("ads_experiment"),
);

const createAudience = createAudienceStore();

const { hasFileFormProgress, hasManualFormProgress } =
  storeToRefs(createAudience);

const hasAnyProgress = computed(() => {
  return hasFileFormProgress.value || hasManualFormProgress.value;
});

await wizard.loadAdSets(data.value.channelGroupId);

const adsIncomeLevels: { label: string; value: Income }[] = [
  {
    label: t("funnel-flow.paid-social.audience.income-levels.struggling"),
    value: "Struggling to cover basic needs.",
  },
  {
    label: t("funnel-flow.paid-social.audience.income-levels.budget-conscious"),
    value: "Budget-conscious, limited discretionary income.",
  },
  {
    label: t("funnel-flow.paid-social.audience.income-levels.balanced"),
    value: "Balanced finances, occasional treats.",
  },
  {
    label: t("funnel-flow.paid-social.audience.income-levels.comfortable"),
    value: "Comfortable, prioritizes experiences and quality.",
  },
  {
    label: t("funnel-flow.paid-social.audience.income-levels.high-income"),
    value: "High-income, enjoying premium lifestyles.",
  },
  {
    label: t("funnel-flow.paid-social.audience.income-levels.luxury"),
    value: "Extremely wealthy with luxury preferences.",
  },
];

const audienceFormData = ref<UpdatePreferredAudienceBody>();
const updatePreferredAudienceBody = ref<UpdatePreferredAudienceBody>();
const audienceComments = ref<string>();

async function cancelAudience() {
  const bodyCancelProposalAudiences = {
    brand_id: brandId,
    campaign_id: campaignId,
    ad_set_id: wizard.selectedAdSet.id,
  };

  await wizard.cancelProposalAudiences(bodyCancelProposalAudiences);

  wizard.closeAllModals();
}

async function deleteAudience() {
  const deleteAudienceBody: DeleteAudienceBody = {
    brand_id: brandId,
    campaign_id: campaignId,
    ad_set_id: wizard.selectedAdSet.id,
    channel_id: data.value.channelGroupId,
  };

  await wizard.deleteAudience(deleteAudienceBody);

  wizard.closeAllModals();
}

function handleDeleteAudienceRequest() {
  if (!paidSocialFormStore.adSetHasFilledAds(wizard.selectedAdSet.id)) {
    deleteAudience();
  } else {
    wizard.setStep("DELETE_AUDIENCE");
  }
}

const deleteAudienceName = computed(() => {
  // Get the preferred audience name from the current audiences (for selected ad set)
  const audienceWithPreferred = wizard.audiences.find(
    (a) => a.preferred_audience != null,
  );
  return audienceWithPreferred?.preferred_audience?.name ?? "";
});

const sidebar = ref<InstanceType<typeof FunnelPaidSocialFormSideBar>>();

function navigateBack() {
  const firstAdset = wizard.adSets[0];

  if (firstAdset.id === sidebar.value?.getSelectedAdSetId()) {
    goBack();
  } else {
    sidebar.value?.goPrev();
  }
}

const generalErrorMessage = ref<string | undefined>();
const validate = () => {
  if (
    wizard.audiences.length === 0 ||
    !wizard.audiences.every((audience) => audience.preferred_audience)
  ) {
    generalErrorMessage.value = t(
      "funnel-flow.paid-social.audience.errors.must-define-audience",
    );
    return false;
  }

  generalErrorMessage.value = undefined;
  return true;
};

watch(wizard.audiences, () => {
  if (generalErrorMessage.value) {
    validate();
  }
});

watch(
  () => locale.value,
  () => {
    if (generalErrorMessage.value) {
      validate();
    }
  },
);

async function handleNext() {
  if (validate()) {
    await paidSocialFormStore.revalidate();
    wizard.setStep("END_MESSAGE");
  }
}

function navigateToAdSet(nextAdset) {
  wizard.selectAdSet(nextAdset);
  sidebar.value?.goToAdSetId(nextAdset);
}

function editAudience(newBody: UpdatePreferredAudienceBody) {
  audienceFormData.value = newBody;
}

async function openSavedAudiences() {
  await wizard.loadSavedAudiences();
  wizard.setStep("SAVED_AUDIENCE");
}

function addAudienceComment(newBody: UpdatePreferredAudienceBody) {
  if (audienceComments.value !== newBody.preferred_audience.comments) {
    audienceComments.value = "";
  }
  updatePreferredAudienceBody.value = newBody;
}

async function updateAudienceComment() {
  if (updatePreferredAudienceBody.value === undefined) {
    return;
  }

  updatePreferredAudienceBody.value = {
    ...updatePreferredAudienceBody.value,
    preferred_audience: {
      ...updatePreferredAudienceBody.value.preferred_audience,
      comments: audienceComments.value,
    },
  };
  await wizard.updatePreferredAudience(updatePreferredAudienceBody.value);

  wizard.closeAllModals();
}
</script>

<template>
  <FunnelPaidSocialFormSideBar
    ref="sidebar"
    @selectAdSet="wizard.selectAdSet"
    :title="data.campaign.name"
    :adSets="wizard.adSets"
    :adsClickeables="false"
  >
    <FormStepLayout as="div">
      <PageTitle
        helpButton
        helpVideoUrl="https://www.youtube.com/watch?v=pMjiVJB0Yls"
      >
        {{ $t("funnel-flow.paid-social.audience.title") }}
      </PageTitle>

      <CardBase
        v-if="wizard.selectedAdSet.id !== 0"
        class="tw:mx-auto tw:w-full tw:max-w-[974px] tw:gap-6 tw:p-5"
      >
        <h3 class="tw:mb-5 tw:text-lg tw:font-extrabold">
          {{ wizard.selectedAdSet.name }}
        </h3>

        <template v-if="wizard.audiences.length === 0">
          <p class="tw:mb-5">
            {{ $t("funnel-flow.paid-social.audience.general-instruction") }}
          </p>

          <div class="tw:flex tw:gap-5">
            <Button
              v-if="hasAnyProgress"
              @click="wizard.setStep('CREATE_MANUAL')"
              size="md"
              type="button"
              class="tw:mb-0 tw:w-auto"
            >
              {{
                $t("funnel-flow.paid-social.audience.actions.resume-audience")
              }}
            </Button>

            <Button
              @click="wizard.setStep('START')"
              variant="outlined"
              size="md"
              type="button"
              class="tw:mb-0 tw:w-auto"
            >
              {{
                $t("funnel-flow.paid-social.audience.actions.define-audience")
              }}
            </Button>
          </div>
        </template>

        <hr
          v-if="wizard.audiences.length > 0"
          class="tw:-mx-5 tw:my-5 tw:border tw:border-secondary/30"
        />

        <div class="tw:grid tw:grid-cols-1 tw:gap-5 tw:xl:grid-cols-2">
          <div
            v-for="channel in wizard.audiences"
            :key="channel.channel_id"
            :title="channel.channel_name"
            :class="{
              'tw:border-r tw:pr-5': wizard.audiences.length > 1,
            }"
          >
            <template
              v-if="
                channel.preferred_audience === null ||
                channel.preferred_audience === undefined
              "
            >
              <p class="tw:mb-5">
                {{ $t("funnel-flow.paid-social.audience.instruction") }}
                {{ channel.channel_name }}.
              </p>

              <Button
                @click="wizard.setStep('START')"
                size="md"
                type="button"
                class="tw:mb-0 tw:w-auto"
              >
                {{
                  $t("funnel-flow.paid-social.audience.actions.define-audience")
                }}
              </Button>
            </template>

            <template v-if="channel.preferred_audience">
              <h2 class="tw:text-md tw:mb-5 tw:font-bold">
                {{ channel.channel_name }}
              </h2>
              <FunnelPaidSocialFormAudienceItem
                :channelId="channel.channel_id"
                :audience="channel.preferred_audience"
                :audienceType="'preferred'"
                @editAudience="editAudience"
                @addAudienceComment="addAudienceComment"
                @delete-audience-request="handleDeleteAudienceRequest"
              />
            </template>
          </div>
        </div>
      </CardBase>

      <Alert v-if="generalErrorMessage" type="error" autoScroll>
        {{ generalErrorMessage }}
      </Alert>

      <!-- Choose method -->
      <Modal
        :modelValue="wizard.showAddSetModal"
        @update:modelValue="
          (v) => {
            if (!v) wizard.closeAllModals();
          }
        "
        class="tw:p-10"
        :maxWidth="600"
        closeButton
      >
        <h2 class="tw:mb-4 tw:text-2xl tw:font-extrabold">
          {{ $t("funnel-flow.paid-social.audience.choose-method-instruction") }}
        </h2>

        <div
          @click="wizard.startManual()"
          class="tw:align-center audience-method-item tw:mb-6 tw:flex tw:cursor-pointer tw:items-center tw:rounded-xl tw:border tw:p-3"
        >
          <div class="tw:m-3 tw:mr-6 tw:flex tw:w-16 tw:justify-center">
            <Icon
              icon="tabler-plus"
              class="tw:h-16 tw:text-9xl tw:text-primary"
            />
          </div>
          <div>
            <h4 class="tw:mb-2 tw:text-lg tw:font-extrabold">
              {{
                $t(
                  "funnel-flow.paid-social.audience.create-audience.modal-label",
                )
              }}
            </h4>
            <p>
              {{
                $t(
                  "funnel-flow.paid-social.audience.create-audience.modal-instruction",
                )
              }}
            </p>
          </div>
        </div>

        <div
          @click="openSavedAudiences()"
          class="tw:align-center audience-method-item tw:mb-6 tw:flex tw:cursor-pointer tw:items-center tw:rounded-xl tw:border tw:p-3"
        >
          <div class="tw:m-3 tw:mr-6 tw:flex tw:w-16 tw:justify-center">
            <Icon
              icon="tabler-bookmark"
              class="tw:h-16 tw:text-9xl tw:text-primary"
            />
          </div>
          <div>
            <h4 class="tw:mb-2 tw:text-lg tw:font-extrabold">
              {{ $t("funnel-flow.paid-social.audience.saved-audience.title") }}
            </h4>
            <p>
              {{
                $t(
                  "funnel-flow.paid-social.audience.saved-audience.description",
                )
              }}
            </p>
          </div>
        </div>

        <div
          class="tw:align-center audience-method-item tw:mb-6 tw:flex tw:items-center tw:rounded-xl tw:border tw:p-3 tw:opacity-50"
        >
          <div class="tw:m-3 tw:mr-6 tw:flex tw:w-16 tw:justify-center">
            <Icon
              icon="custom:hi-luca"
              class="tw:h-16 tw:text-9xl tw:text-primary"
            />
          </div>
          <div>
            <h4 class="tw:mb-2 tw:text-lg tw:font-extrabold">
              {{
                $t("funnel-flow.paid-social.audience.luca-audience.modal-label")
              }}
              <span
                class="tw:ml-2 tw:rounded-md tw:bg-secondary/30 tw:px-2 tw:py-1 tw:text-sm"
                >{{ $t("global.soon") }}</span
              >
            </h4>
            <p>
              {{
                $t(
                  "funnel-flow.paid-social.audience.luca-audience.modal-instruction",
                )
              }}
            </p>
          </div>
        </div>

        <div
          class="tw:align-center audience-method-item tw:mb-6 tw:flex tw:items-center tw:rounded-xl tw:border tw:p-3 tw:opacity-50"
        >
          <div class="tw:m-3 tw:mr-6 tw:flex tw:w-16 tw:justify-center">
            <Icon
              icon="tabler-template"
              class="tw:h-16 tw:text-9xl tw:text-primary"
            />
          </div>
          <div>
            <h4 class="tw:mb-2 tw:text-lg tw:font-extrabold">
              {{
                $t("funnel-flow.paid-social.audience.use-template.modal-label")
              }}
              <span
                class="tw:ml-2 tw:rounded-md tw:bg-secondary/30 tw:px-2 tw:py-1 tw:text-sm"
                >{{ $t("global.soon") }}</span
              >
            </h4>
            <p>
              {{
                $t(
                  "funnel-flow.paid-social.audience.use-template.modal-instruction",
                )
              }}
            </p>
          </div>
        </div>
      </Modal>

      <!-- Generate Audience Loader -->
      <Modal
        :modelValue="wizard.showGenerateAudLoader"
        @update:modelValue="
          (v) => {
            if (!v) wizard.closeAllModals();
          }
        "
        class="tw:p-10 tw:text-center"
        :maxWidth="500"
        closeButton
      >
        <FunnelPaidSocialFormAudienceLoader
          :title="
            $t(
              'funnel-flow.paid-social.audience.ai-research.loader-to-saved-audience.title',
            )
          "
          :description="
            $t(
              'funnel-flow.paid-social.audience.ai-research.loader-to-saved-audience.description',
            )
          "
        />
      </Modal>

      <!-- Saved Audience -->
      <Modal
        :modelValue="wizard.showSavedAudience"
        @update:modelValue="
          (v) => {
            if (!v) wizard.closeAllModals();
          }
        "
        class="tw:p-10"
        :maxWidth="1280"
        closeButton
      >
        <FunnelPaidSocialFormAudienceSavedAudience
          key="saved"
          :currentTab="
            wizard.savedAudiences.length > 0
              ? wizard.savedAudiences[0].channel_id
              : null
          "
          audiencesType="saved"
          :description="
            $t('funnel-flow.paid-social.audience.saved-audience.description')
          "
          :audiences="wizard.savedAudiences"
          @useAudience="wizard.setStep('START')"
          :title="$t('funnel-flow.paid-social.audience.saved-audience.title')"
        />
      </Modal>

      <!-- Generated Audience -->
      <Modal
        :modelValue="wizard.showGeneratedAudience"
        @update:modelValue="
          (v) => {
            if (!v) wizard.closeAllModals();
          }
        "
        class="tw:p-10"
        :maxWidth="1280"
        closeButton
      >
        <FunnelPaidSocialFormAudienceSavedAudience
          key="generated"
          :title="
            $t('funnel-flow.paid-social.audience.generated-audience.title')
          "
          :description="
            $t(
              'funnel-flow.paid-social.audience.generated-audience.description',
            )
          "
          :currentTab="
            wizard.audiences.length > 0 ? wizard.audiences[0].channel_id : null
          "
          audiencesType="generated"
          :audiences="wizard.audiences"
          @useAudience="wizard.setStep('CANCEL_AUDIENCE')"
        />
      </Modal>

      <!-- Create Audience -->
      <Modal
        :modelValue="wizard.showCreateManual"
        @update:modelValue="
          (v) => {
            if (!v) wizard.closeAllModals();
          }
        "
        class="tw:p-10"
        :maxWidth="800"
        closeButton
      >
        <FunnelPaidSocialFormAudienceCreateAudience
          :adsIncomeLevels="adsIncomeLevels"
        />
      </Modal>

      <!-- Edit audience -->
      <Modal
        :modelValue="wizard.showEditAudience"
        @update:modelValue="
          (v) => {
            if (!v) wizard.closeAllModals();
          }
        "
        class="tw:p-10"
        :maxWidth="800"
        closeButton
      >
        <FunnelPaidSocialFormAudienceEditAudience
          v-if="audienceFormData"
          :key="audienceFormData.channel_id"
          :channelId="audienceFormData.channel_id"
          :formData="audienceFormData.preferred_audience"
          :adsIncomeLevels="adsIncomeLevels"
        />
      </Modal>

      <!-- Cancel audiences -->
      <Modal
        :modelValue="wizard.showCancelAudience"
        @update:modelValue="
          (v) => {
            if (!v) wizard.closeAllModals();
          }
        "
        class="tw:p-10"
        :maxWidth="500"
        closeButton
      >
        <h3 class="tw:mb-5 tw:text-center tw:text-2xl tw:font-bold">
          {{ $t("funnel-flow.paid-social.audience.cancel-proposal.title") }}
        </h3>
        <p class="tw:mb-5 tw:text-center">
          {{
            $t("funnel-flow.paid-social.audience.cancel-proposal.description")
          }}
        </p>
        <div class="tw:flex tw:justify-between tw:gap-2 tw:md:gap-10">
          <Button
            @click="wizard.setStep('GENERATED_AUDIENCE')"
            size="md"
            variant="outlined"
            type="button"
            class="tw:w-full"
          >
            {{ $t("funnel-flow.paid-social.audience.actions.dont-cancel") }}
          </Button>
          <Button
            @click="cancelAudience"
            size="md"
            type="button"
            class="tw:w-full"
          >
            {{ $t("global.cancel") }}
          </Button>
        </div>
      </Modal>

      <!-- Delete audience (modal only shown when there are filled ads) -->
      <ModalGeneric
        :modelValue="wizard.showDeleteAudience"
        :maxWidth="560"
        @cancel="wizard.closeAllModals()"
        @close="wizard.closeAllModals()"
      >
        <template #title>
          {{ $t("funnel-flow.paid-social.audience.delete-audience.title") }}
        </template>

        <p class="tw:mb-2 tw:text-secondary-text">
          {{
            $t(
              "funnel-flow.paid-social.audience.delete-audience.dependency-description",
              {
                audienceName: deleteAudienceName,
                adSetName: wizard.selectedAdSet.name,
                adCount: paidSocialFormStore.countFilledAds(
                  wizard.selectedAdSet.id,
                ),
              },
            )
          }}
        </p>
        <p class="tw:text-sm tw:text-secondary tw:italic">
          {{
            $t(
              "funnel-flow.paid-social.audience.delete-audience.dependency-impact",
            )
          }}
        </p>

        <template #actions>
          <Button
            variant="outlined"
            type="button"
            @click="wizard.closeAllModals()"
          >
            {{ $t("global.cancel") }}
          </Button>

          <Button color="error" type="button" @click="deleteAudience()">
            {{ $t("funnel-flow.paid-social.audience.delete-audience.confirm") }}
          </Button>
        </template>
      </ModalGeneric>

      <Modal
        :modelValue="wizard.showAddComment"
        @update:modelValue="
          (v) => {
            if (!v) wizard.closeAllModals();
          }
        "
        class="tw:p-10"
        :maxWidth="500"
        closeButton
      >
        <h5 class="tw:text-xl tw:font-bold">
          {{ $t("funnel-flow.paid-social.audience.add-comment.title") }}
        </h5>
        <hr class="tw:-mx-10 tw:my-5 tw:border tw:border-secondary/30" />
        <textarea
          v-model="audienceComments"
          class="tw:w-full tw:resize-none tw:rounded-xl tw:border tw:border-secondary/30 tw:p-4"
          row="20"
          col="10"
          :placeholder="
            $t('funnel-flow.paid-social.audience.add-comment.placeholder')
          "
          type="text"
        ></textarea>
        <div>
          <hr class="tw:-mx-10 tw:my-5 tw:border tw:border-secondary/30" />
          <div class="tw:grid tw:grid-cols-2 tw:gap-6">
            <Button
              @click="wizard.closeAllModals()"
              size="lg"
              variant="outlined"
              type="button"
            >
              {{ $t("global.cancel") }}
            </Button>
            <Button @click="updateAudienceComment" size="lg" type="button">
              {{ $t("funnel-flow.paid-social.audience.actions.add") }}
            </Button>
          </div>
        </div>
      </Modal>

      <!-- End Msg -->
      <FunnelPaidSocialFormEndMessageModal v-model="showEndMsgModal">
        <template #title>
          {{ $t("funnel-flow.paid-social.audience.end-msg.title") }}
          <br />
          <template v-if="wizard.nextSet">
            {{
              $t(
                "funnel-flow.paid-social.audience.end-msg.subtitle.with-next",
                { name: wizard.selectedAdSet.name },
              )
            }}
          </template>
          <template v-else>
            {{
              $t(
                "funnel-flow.paid-social.audience.end-msg.subtitle.all-complete",
              )
            }}
          </template>
        </template>

        <template #description>
          <template v-if="wizard.nextSet">
            {{
              $t(
                "funnel-flow.paid-social.audience.end-msg.description.with-next",
                { name: wizard.nextSet?.name },
              )
            }}
          </template>
          <template v-else>
            {{
              $t(
                "funnel-flow.paid-social.audience.end-msg.description.all-complete",
              )
            }}
          </template>
        </template>

        <template #actions>
          <template v-if="wizard.nextSet">
            <Button @click="navigateToAdSet(wizard.nextSet.id)">
              {{
                $t(
                  "funnel-flow.paid-social.audience.end-msg.actions.define-audience-for",
                  { name: wizard.nextSet?.name },
                )
              }}
            </Button>
          </template>
          <template v-else>
            <Alert
              v-if="!canProceedToCreativeAngle"
              type="warning"
              autoScroll
              class="tw:w-full"
            >
              {{
                $t(
                  "funnel-flow.paid-social.audience.end-msg.warning.prerequisite-steps-incomplete",
                )
              }}
            </Alert>
            <Button :disabled="!canProceedToCreativeAngle" @click="goNext">
              {{
                $t(
                  "funnel-flow.paid-social.audience.actions.next-ads-experiment",
                )
              }}
            </Button>
          </template>

          <Button type="button" variant="text" @click="wizard.closeAllModals()">
            {{
              $t(
                "funnel-flow.paid-social.audience.end-msg.actions.review-audience",
                { name: wizard.selectedAdSet.name },
              )
            }}
          </Button>
        </template>
      </FunnelPaidSocialFormEndMessageModal>

      <template #actions>
        <WizardCardActions>
          <ButtonGoBack @click="navigateBack()" />
          <ButtonNext @click="handleNext()">
            <template v-if="wizard.nextSet">
              {{
                $t("funnel-flow.paid-social.audience.actions.next-with-name", {
                  name: wizard.nextSet.name,
                })
              }}
            </template>
            <template v-else>
              {{
                $t(
                  "funnel-flow.paid-social.audience.actions.next-ads-experiment",
                )
              }}
            </template>
          </ButtonNext>
        </WizardCardActions>
      </template>
    </FormStepLayout>
  </FunnelPaidSocialFormSideBar>
</template>

<style scoped>
.audience-method-item {
  border: 1px solid #e7e3df;
}
</style>
