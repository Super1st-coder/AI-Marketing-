<script lang="ts" setup>
import { FunnelBuildingBlockStatus } from "@/components/legacy/funnel-builder/cards/FunnelBuildingBlockCard.vue";
import ProjectsAPI from "@/services/legacy/ProjectsAPI";
import { useRoute, useRouter } from "vue-router";

const router = useRouter();
const route = useRoute();

const projectId = parseInt(route.params.id as string);
const project = await ProjectsAPI.getOne(projectId);

const blockStatuses = computed<Record<string, FunnelBuildingBlockStatus>>(
  () => {
    const statuses: Record<string, FunnelBuildingBlockStatus> = {};

    // Meta ads
    statuses["metaAds"] = {
      blockCount: 1,
      blocksCovered: project.data.meta_ads?.find((ad) => ad.preferred) ? 1 : 0,
    };

    statuses["landingPage"] = {
      blockCount: 1,
      blocksCovered: 0,
    };

    statuses["remarketingMetaAds"] = {
      blockCount: 1,
      blocksCovered: project.data.meta_ads_remarketing?.find(
        (ad) => ad.preferred,
      )
        ? 1
        : 0,
    };

    statuses["remarketingLandingPage"] = {
      blockCount: 1,
      blocksCovered: 0,
    };

    // Emails builder
    let emailBlockCovered = 0;
    if (project.data.email_reminder_generated?.Body) emailBlockCovered++;
    if (project.data.email_painpoints_generated?.Body) emailBlockCovered++;
    if (project.data.email_usecase_generated?.Body) emailBlockCovered++;
    if (project.data.email_urgency_generated?.Body) emailBlockCovered++;
    if (project.data.email_offer_generated?.Body) emailBlockCovered++;
    statuses["emailMarketingFlow"] = {
      blockCount: 5,
      blocksCovered: emailBlockCovered,
    };

    statuses["whatsappBotFunnel"] = {
      blockCount: 1,
      blocksCovered: project.data.whatsapp_bot_scheduling_configured ? 1 : 0,
    };

    statuses["salesScript"] = {
      blockCount: 3,
      blocksCovered: 0,
    };

    return statuses;
  },
);

const isStatusReady = (status: FunnelBuildingBlockStatus) =>
  status.blocksCovered >= status.blockCount;

// const isReady = computed(() =>
//   Object.values(blockStatuses.value).every(
//     (status) => status.blocksCovered >= status.blockCount,
//   ),
// );
</script>

<template>
  <WizardCard
    paddingY="lg"
    class="tw:flex tw:flex-col tw:gap-[40px] tw:lg:gap-[60px]"
  >
    <div>
      <WizardCardTitle>
        Paid Social funnel building blocks
        <template #button>
          <HelpButton> Help info </HelpButton>
        </template>
      </WizardCardTitle>

      <WizardCardParagraph>
        Select and customize the key building blocks to construct your Paid
        Social funnel, from initial engagement to final conversion.
      </WizardCardParagraph>
    </div>

    <div class="tw:flex tw:flex-col tw:gap-8">
      <FunnelBuildingBlockCard
        icon="tabler-brand-meta"
        :to="{ name: 'MetaAds' }"
        :status="blockStatuses['metaAds']"
      >
        <template #title> Meta ads </template>

        <template #description>
          Drive targeted traffic and build initial awareness or engagement
          through Facebook and Instagram ads.
        </template>

        <template #options>
          <Button
            leftIcon="tabler-brand-meta"
            icon="tabler-arrow-right"
            size="md"
            variant="outlined"
            customColor="#0081FB"
            :disabled="!isStatusReady(blockStatuses['metaAds'])"
          >
            SEND TO META
          </Button>
        </template>
      </FunnelBuildingBlockCard>

      <FunnelBuildingBlockCard
        icon="tabler-browser"
        :to="{ name: 'LandingPage' }"
        :status="blockStatuses['landingPage']"
      >
        <template #title> Landing page </template>

        <template #description>
          Convert traffic from Meta ads by providing a focused page that matches
          the ad message, with a clear call to action.
        </template>

        <template #options>
          <Button
            leftIcon="tabler-brand-webflow"
            icon="tabler-arrow-right"
            size="md"
            variant="outlined"
            customColor="#146ef5"
            :disabled="!isStatusReady(blockStatuses['landingPage'])"
          >
            SEND TO WEBFLOW
          </Button>
        </template>
      </FunnelBuildingBlockCard>

      <FunnelBuildingBlockCard
        icon="tabler-speakerphone"
        :to="{ name: 'RemarketingMetaAds' }"
        :status="blockStatuses['remarketingMetaAds']"
      >
        <template #title> Remarketing Meta ads </template>

        <template #description>
          Re-engage users who visited the landing page but didn’t convert, using
          tailored Meta ads to drive them back for another attempt.
        </template>

        <template #options>
          <Button
            leftIcon="tabler-brand-meta"
            icon="tabler-arrow-right"
            size="md"
            variant="outlined"
            customColor="#0081FB"
            :disabled="!isStatusReady(blockStatuses['remarketingMetaAds'])"
          >
            SEND TO META
          </Button>
        </template>
      </FunnelBuildingBlockCard>

      <FunnelBuildingBlockCard
        icon="tabler-page-break"
        :to="{ name: 'LandingPageRemarketing' }"
        :status="blockStatuses['remarketingLandingPage']"
      >
        <template #title> Remarketing landing page </template>

        <template #description>
          Provide a customized landing page for users returning from remarketing
          ads, offering them an exclusive deal or more targeted content.
        </template>

        <template #options>
          <Button
            leftIcon="tabler-brand-webflow"
            icon="tabler-arrow-right"
            size="md"
            variant="outlined"
            customColor="#146ef5"
            :disabled="!isStatusReady(blockStatuses['remarketingLandingPage'])"
          >
            SEND TO WEBFLOW
          </Button>
        </template>
      </FunnelBuildingBlockCard>

      <FunnelBuildingBlockCard
        icon="tabler-mail"
        :to="{ name: 'EmailMarketingFlow' }"
        :status="blockStatuses['emailMarketingFlow']"
      >
        <template #title> Email marketing flow </template>

        <template #description>
          Nurture leads captured on the landing page with an automated email
          sequence triggered by user actions.
        </template>

        <template #options>
          <Button
            leftIcon="fa-brands:mailchimp"
            icon="tabler-arrow-right"
            size="md"
            variant="outlined"
            customColor="black"
            :disabled="!isStatusReady(blockStatuses['emailMarketingFlow'])"
          >
            SEND TO MAILCHIMP
          </Button>
        </template>
      </FunnelBuildingBlockCard>

      <FunnelBuildingBlockCard
        icon="tabler-brand-whatsapp"
        :to="{ name: 'WhatsappBotFunnel' }"
        :status="blockStatuses['whatsappBotFunnel']"
      >
        <template #title> WhatsApp bot funnel </template>

        <template #description>
          Automate follow-up communication with leads via WhatsApp, providing
          instant responses, product information, and guidance through the
          funnel.
        </template>

        <template #options>
          <Button
            leftIcon="brand-wati"
            icon="tabler-arrow-right"
            size="md"
            variant="outlined"
            customColor="#00E785"
            :disabled="!isStatusReady(blockStatuses['whatsappBotFunnel'])"
          >
            SEND TO WATI
          </Button>
        </template>
      </FunnelBuildingBlockCard>

      <FunnelBuildingBlockCard
        icon="tabler-messages"
        :status="blockStatuses['salesScript']"
      >
        <template #title> Sales script </template>

        <template #description>
          Provide sales teams with a structured conversation flow to handle
          leads who require direct contact, guiding them toward conversion.
        </template>

        <template #options>
          <Button
            leftIcon="brand-teleperformance"
            icon="tabler-arrow-right"
            size="md"
            variant="outlined"
            customColor="#D52083"
            :disabled="!isStatusReady(blockStatuses['salesScript'])"
          >
            SEND TO TELEPERFORMANCE
          </Button>
        </template>
      </FunnelBuildingBlockCard>
    </div>

    <div
      class="tw:flex tw:flex-col tw:justify-start tw:gap-5 tw:lg:flex-row tw:lg:self-stretch"
    >
      <div class="tw:grow">
        <WizardButtonGoBack
          @click="router.push({ name: 'FunnelStageAcquisition' })"
        />
      </div>

      <Button
        class="tw:lg:basis-[250px]"
        color="success"
        leftIcon="tabler-brand-upwork"
        icon="tabler-arrow-right"
      >
        SEND TO UPWORK
      </Button>

      <Button
        class="tw:lg:basis-[250px]"
        color="info"
        leftIcon="tabler-brand-trello"
        icon="tabler-arrow-right"
      >
        SEND TO TRELLO
      </Button>

      <Button class="tw:lg:basis-[250px]" icon="tabler-arrow-right">
        EXPORT AS A FILE
      </Button>
    </div>
  </WizardCard>
</template>
