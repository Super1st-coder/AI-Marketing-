<script lang="ts" setup>
import { FunnelBuildingBlockStatus } from "@/components/legacy/funnel-builder/cards/FunnelBuildingBlockCard.vue";
import ProjectsAPI from "@/services/legacy/ProjectsAPI";
import { useRoute } from "vue-router";

const route = useRoute();

const projectId = parseInt(route.params.id as string);
const project = await ProjectsAPI.getOne(projectId);

const blockStatuses = computed<Record<string, FunnelBuildingBlockStatus>>(
  () => {
    const statuses: Record<string, FunnelBuildingBlockStatus> = {};

    statuses["reminderAndValue"] = {
      blockCount: 1,
      blocksCovered: project.data.email_reminder_generated?.Body ? 1 : 0,
    };

    statuses["painPoints"] = {
      blockCount: 1,
      blocksCovered: project.data.email_painpoints_generated?.Body ? 1 : 0,
    };

    statuses["caseStudies"] = {
      blockCount: 1,
      blocksCovered: project.data.email_usecase_generated?.Body ? 1 : 0,
    };

    statuses["urgency"] = {
      blockCount: 1,
      blocksCovered: project.data.email_urgency_generated?.Body ? 1 : 0,
    };

    statuses["specialOffer"] = {
      blockCount: 1,
      blocksCovered: project.data.email_offer_generated?.Body ? 1 : 0,
    };

    return statuses;
  },
);
</script>

<template>
  <WizardCard
    paddingY="lg"
    class="tw:flex tw:flex-col tw:gap-[40px] tw:lg:gap-[60px]"
  >
    <div>
      <WizardCardTitle>
        Email flow builder: automate your engagement
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
        icon="tabler-bell-ringing"
        :to="{ name: 'ReminderAndValue' }"
        :status="blockStatuses['reminderAndValue']"
      >
        <template #title> Reminder and value email </template>

        <template #description>
          This email is aimed at reminding the user about their sign-up and
          reinforcing the value they’re missing out on.
        </template>
      </FunnelBuildingBlockCard>

      <FunnelBuildingBlockCard
        icon="tabler-puzzle"
        :to="{ name: 'PainPoints' }"
        :status="blockStatuses['painPoints']"
      >
        <template #title> Address pain points and offer a solution </template>

        <template #description>
          This email should dive into their pain points and remind them how your
          product solves their problems.
        </template>
      </FunnelBuildingBlockCard>

      <FunnelBuildingBlockCard
        icon="tabler-quote"
        :to="{ name: 'CaseStudies' }"
        :status="blockStatuses['caseStudies']"
      >
        <template #title> Social proof / Case studies </template>

        <template #description>
          This email uses trust signals like testimonials or case studies to
          show real-world results.
        </template>
      </FunnelBuildingBlockCard>

      <FunnelBuildingBlockCard
        icon="tabler-urgent"
        :to="{ name: 'Urgency' }"
        :status="blockStatuses['urgency']"
      >
        <template #title> Urgency / Scarcity Email </template>

        <template #description>
          This email introduces urgency to encourage immediate action.
        </template>
      </FunnelBuildingBlockCard>

      <FunnelBuildingBlockCard
        icon="tabler-rosette-discount"
        :to="{ name: 'SpecialOffer' }"
        :status="blockStatuses['specialOffer']"
      >
        <template #title> Special offer email (last push) </template>

        <template #description>
          This final email provides a special incentive to push them over the
          line.
        </template>
      </FunnelBuildingBlockCard>
    </div>

    <WizardCardActions>
      <WizardButtonGoBack :to="{ name: 'PaidSocial' }" />

      <WizardButtonNext :to="{ name: 'PaidSocial' }">
        SAVE AD COPIES
      </WizardButtonNext>
    </WizardCardActions>
  </WizardCard>
</template>
