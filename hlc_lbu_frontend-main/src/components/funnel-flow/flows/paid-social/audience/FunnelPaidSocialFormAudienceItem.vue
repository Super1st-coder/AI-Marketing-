<script setup lang="ts">
import {
  AudienceItem,
  SaveUnsaveAudienceBody,
  UpdatePreferredAudienceBody,
} from "@/services/projects/AudienceApi";

const props = defineProps<{
  channelId: number;
  audience: AudienceItem;
  audienceType?: "preferred" | "generated" | "ads-experiment" | "saved";
}>();

const emit = defineEmits<{
  (e: "audienceSelected", audienceId: number): void;
  (e: "editAudience", audience: UpdatePreferredAudienceBody): void;
  (
    e: "addAudienceComment",
    updatePreferredAudienceBody: UpdatePreferredAudienceBody,
  ): void;
  (e: "deleteAudienceRequest"): void;
}>();

const brandId = useBrandId();
const campaignId = useCampaignId();

const wizard = useFunnelPaidSocialAudienceStore();
wizard.setContext({ brand: brandId, campaign: campaignId });

const inUseByOtherAdSet = computed(() => {
  if (props.audienceType !== "saved") return null;
  const usage = wizard.getSavedAudienceUsage(props.channelId, props.audience);
  if (!usage) return null;
  if (usage.adSetId === wizard.selectedAdSet?.id) return null;
  return usage.adSetName;
});

async function saveUnsaveAudience(audience: AudienceItem) {
  const audienceBody: SaveUnsaveAudienceBody = {
    brand_id: brandId,
    campaign_id: campaignId,
    ad_set_id: wizard.selectedAdSet.id,
    channel_id: props.channelId,
    audience: audience,
  };

  if (props.audience.saved) {
    if (props.audienceType === "saved") {
      await wizard.deleteAudienceFromSaved(audience.id);
    } else {
      await wizard.unsaveAudience(audienceBody);
    }
  } else {
    await wizard.saveAudience(audienceBody);
  }
}

function editAudience(audience: AudienceItem) {
  const audienceBody: UpdatePreferredAudienceBody = {
    brand_id: brandId,
    campaign_id: campaignId,
    ad_set_id: wizard.selectedAdSet.id,
    channel_id: props.channelId,
    preferred_audience: audience,
  };
  emit("editAudience", audienceBody);
  wizard.setStep("EDIT_AUDIENCE");
}

async function removeComment(audience: AudienceItem) {
  const audienceBody: UpdatePreferredAudienceBody = {
    brand_id: brandId,
    campaign_id: campaignId,
    ad_set_id: wizard.selectedAdSet.id,
    channel_id: props.channelId,
    preferred_audience: {
      ...audience,
      comments: "",
    },
  };
  await wizard.updatePreferredAudience(audienceBody);
}

function addAudienceComment(audience: AudienceItem) {
  const audienceBody: UpdatePreferredAudienceBody = {
    brand_id: brandId,
    campaign_id: campaignId,
    ad_set_id: wizard.selectedAdSet.id,
    channel_id: props.channelId,
    preferred_audience: audience,
  };
  emit("addAudienceComment", audienceBody);
  wizard.setStep("ADD_COMMENT");
}
</script>

<template>
  <CardBase class="tw:flex tw:flex-col tw:gap-6 tw:overflow-hidden tw:p-5">
    <div
      class="tw:-m-5 tw:flex tw:flex-1 tw:flex-col tw:bg-secondary/30 tw:p-3"
    >
      <label
        :for="
          'channel-' +
          audienceType +
          '-' +
          props.channelId +
          '-audience-' +
          props.audience.id
        "
        class="tw:mb-3 tw:flex tw:items-center tw:text-sm tw:font-semibold"
        :class="[
          audienceType === 'generated' || audienceType === 'saved'
            ? 'tw:justify-start'
            : 'tw:justify-between',
          {
            'tw:cursor-pointer':
              audienceType === 'generated' || audienceType === 'saved',
          },
        ]"
      >
        <input
          v-if="audienceType === 'generated' || audienceType === 'saved'"
          :id="
            'channel-' +
            audienceType +
            '-' +
            props.channelId +
            '-audience-' +
            props.audience.id
          "
          :name="'channel-' + audienceType + '-' + props.channelId"
          :disabled="!!inUseByOtherAdSet"
          @change="() => emit('audienceSelected', props.audience.id)"
          type="radio"
        />
        <span class="tw:ml-2 tw:inline-block tw:font-semibold">
          {{ props.audience.name }}
        </span>

        <ButtonDropdownIcon
          v-if="props.audienceType === 'preferred'"
          placement="bottom-start"
          icon="tabler-dots-vertical"
        >
          <template #options>
            <ButtonDropdownOption
              @click="editAudience(props.audience)"
              class="tw:w-full"
            >
              <div class="tw:flex tw:items-center">
                <Icon
                  icon="tabler-pencil"
                  class="tw:mr-3 tw:text-xl tw:text-primary"
                />
                <span>{{
                  $t(
                    "funnel-flow.paid-social.audience.audience-items-menu.edit-audience",
                  )
                }}</span>
              </div>
            </ButtonDropdownOption>
            <ButtonDropdownOption
              @click="addAudienceComment(audience)"
              class="tw:w-full"
            >
              <div class="tw:flex tw:items-center">
                <Icon
                  icon="tabler-message-dots"
                  class="tw:mr-3 tw:text-xl tw:text-primary"
                />
                <span>{{
                  $t(
                    "funnel-flow.paid-social.audience.audience-items-menu.add-comment",
                  )
                }}</span>
              </div>
            </ButtonDropdownOption>
            <ButtonDropdownOption
              @click="saveUnsaveAudience(props.audience)"
              class="tw:w-full"
            >
              <div>
                <span class="tw:flex tw:text-sm" v-if="props.audience.saved">
                  <Icon
                    icon="tabler-bookmark-filled"
                    class="tw:mr-1 tw:text-lg tw:text-primary"
                  />
                  {{
                    $t(
                      "funnel-flow.paid-social.audience.audience-items-menu.remove-from-saved-audiences",
                    )
                  }}
                </span>
                <span class="tw:flex tw:text-sm" v-if="!props.audience.saved">
                  <Icon
                    icon="tabler-bookmark"
                    class="tw:mr-1 tw:text-lg tw:text-secondary"
                  />
                  {{
                    $t(
                      "funnel-flow.paid-social.audience.audience-items-menu.add-to-saved-audiences",
                    )
                  }}
                </span>
              </div>
            </ButtonDropdownOption>
            <ButtonDropdownOption
              @click="emit('deleteAudienceRequest')"
              class="tw:w-full"
            >
              <div class="tw:flex tw:items-center">
                <Icon
                  icon="tabler-trash"
                  class="tw:mr-3 tw:text-xl tw:text-error"
                />
                <span class="tw:text-error">{{
                  $t(
                    "funnel-flow.paid-social.audience.audience-items-menu.delete-audience",
                  )
                }}</span>
              </div>
            </ButtonDropdownOption>
          </template>
        </ButtonDropdownIcon>
      </label>

      <AudiencePreview
        :audience="audience"
        :audienceType="audienceType"
        @removeComment="removeComment"
        displayActions
      />

      <!-- In-use label moved to bottom, above the footer actions -->
      <div
        v-if="inUseByOtherAdSet"
        class="tw:mt-4 tw:text-xs tw:text-secondary"
      >
        {{
          $t(
            "funnel-flow.paid-social.audience.create-audience-modal.already-in-use",
            { adSet: inUseByOtherAdSet },
          )
        }}
      </div>

      <div
        v-if="props.audienceType !== 'preferred' && !inUseByOtherAdSet"
        class="tw:mt-5 tw:mb-2 tw:flex tw:justify-between"
      >
        <button @click="saveUnsaveAudience(props.audience)">
          <span class="tw:flex tw:text-sm" v-if="props.audience.saved">
            <Icon
              icon="tabler-bookmark-filled"
              class="tw:mr-1 tw:text-lg tw:text-primary"
            />
            {{
              $t(
                "funnel-flow.paid-social.audience.audience-items-menu.remove-from-saved-audiences",
              )
            }}
          </span>
          <span class="tw:flex tw:text-sm" v-if="!props.audience.saved">
            <Icon
              icon="tabler-bookmark"
              class="tw:mr-1 tw:text-lg tw:text-secondary"
            />
            {{
              $t(
                "funnel-flow.paid-social.audience.audience-items-menu.add-to-saved-audiences",
              )
            }}
          </span>
        </button>
      </div>
    </div>
  </CardBase>
</template>

<style></style>
