<script lang="ts" setup>
import { array, object, string } from "yup";
import { toTypedSchema } from "@vee-validate/yup";
import { useRoute, useRouter } from "vue-router";
import WhatsappBotFunnelAPI, {
  WhatsappBotFunnelElements,
} from "@/services/legacy/WhatsappBotFunnelAPI";

const router = useRouter();
const route = useRoute();

//#region Fetch initial data

const projectId = parseInt(route.params.id as string);
const response = await WhatsappBotFunnelAPI.getConfigured(projectId);
let data: WhatsappBotFunnelElements | undefined =
  response.data.whatsapp_bot_scheduling_configured;

if (!data?.WhatsApp_Conversational_Flow) {
  // Let's try to fetch the elements
  const response = await WhatsappBotFunnelAPI.getElements(projectId);
  data.WhatsApp_Conversational_Flow =
    response.data.whatsapp_bot_scheduling_generated.WhatsApp_Conversational_Flow;
}

if (!data?.WhatsApp_Conversational_Flow) {
  throw new Error("WHATSAPP_BOT_FUNNEL_NOT_GENERATED");
}

//#endregion

const isLoading = ref(false);

type SimulationType = undefined | "scheduleACall" | "talkToAnAgentNow";
const viewedSimulation = ref<SimulationType>(undefined);

const chatParent = ref<HTMLDivElement>();
const handleViewSimulation = async (type: SimulationType) => {
  viewedSimulation.value = type;
  chatParent.value?.scrollIntoView({ behavior: "smooth" });
};

const { handleSubmit, values } = useFormWithErrorScrolling({
  initialValues: {
    initialMessage:
      data.WhatsApp_Conversational_Flow.Section_1_Initial_Greeting_Message[0],
    secondMessage:
      data.WhatsApp_Conversational_Flow
        .Section_2_Follow_Up_Greeting_With_Options[0],
    scheduleACall: {
      title:
        data.WhatsApp_Conversational_Flow["follow-up-greeting_options"]?.[0] ??
        "Schedule a Call",
      chooseADay:
        data.WhatsApp_Conversational_Flow
          .Section_3_Flow_A_Days_Of_The_Week_Options[0],
      chooseADayOptions: data.WhatsApp_Conversational_Flow.day_options ?? [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
      ],
      chooseTimeSlot:
        data.WhatsApp_Conversational_Flow
          .Section_4_Flow_A_Choose_Hours_Options[0],
      chooseTimeSlotOptions: data.WhatsApp_Conversational_Flow
        .time_slot_options ?? [
        "9:00 AM - 11:00 AM",
        "1:00 PM - 3:00 PM",
        "5:00 PM - 7:00 PM",
      ],
      endingMessage:
        data.WhatsApp_Conversational_Flow.Section_5_Flow_A_Goodbye_Options[0],
    },
    talkToAgentNow: {
      title:
        data.WhatsApp_Conversational_Flow["follow-up-greeting_options"]?.[1] ??
        "Talk to an agent now",
      chooseDetails:
        data.WhatsApp_Conversational_Flow
          .Section_6_Flow_B_Connect_With_An_Agent[0],
      chooseDetailsOptions: data.WhatsApp_Conversational_Flow
        .details_options ?? [
        "Offer Details",
        "Help with scheduling",
        "General inquiries",
      ],
      endingMessage:
        data.WhatsApp_Conversational_Flow
          .Section_7_Flow_B_Agent_Handoff_Confirmation[0],
    },
  },
  validationSchema: toTypedSchema(
    object({
      initialMessage: string().required(),
      secondMessage: string().required(),
      options: array().of(string().required()),
      scheduleACall: object({
        title: string().required(),
        chooseADay: string().required(),
        chooseADayOptions: array().of(string().required()),
        chooseTimeSlot: string().required(),
        chooseTimeSlotOptions: array().of(string().required()),
        endingMessage: string().required(),
      }).required(),
      talkToAgentNow: object({
        title: string().required(),
        chooseDetails: string().required(),
        chooseDetailsOptions: array().of(string().required()),
        endingMessage: string().required(),
      }).required(),
    }),
  ),
  keepValuesOnUnmount: true,
});

const onSubmit = handleSubmit(async (values) => {
  isLoading.value = true;

  await WhatsappBotFunnelAPI.configure(projectId, {
    ...data,
    WhatsApp_Conversational_Flow: {
      Section_1_Initial_Greeting_Message: [values.initialMessage],
      Section_2_Follow_Up_Greeting_With_Options: [values.secondMessage],
      Section_3_Flow_A_Days_Of_The_Week_Options: [
        values.scheduleACall.chooseADay,
      ],
      Section_4_Flow_A_Choose_Hours_Options: [
        values.scheduleACall.chooseTimeSlot,
      ],
      Section_5_Flow_A_Goodbye_Options: [values.scheduleACall.endingMessage],
      Section_6_Flow_B_Connect_With_An_Agent: [
        values.talkToAgentNow.chooseDetails,
      ],
      Section_7_Flow_B_Agent_Handoff_Confirmation: [
        values.talkToAgentNow.endingMessage,
      ],
      "follow-up-greeting_options": [
        values.scheduleACall.title,
        values.talkToAgentNow.title,
      ],
      day_options: values.scheduleACall.chooseADayOptions,
      time_slot_options: values.scheduleACall.chooseTimeSlotOptions,
      details_options: values.talkToAgentNow.chooseDetailsOptions,
    },
  });

  router.push({ name: "PaidSocial" });
});
</script>

<template>
  <WizardCard paddingY="lg">
    <form
      @submit="onSubmit"
      class="tw:flex tw:flex-col tw:gap-[40px] tw:lg:gap-[60px]"
    >
      <div
        class="tw:flex tw:flex-col tw:justify-between tw:gap-6 tw:lg:flex-row tw:lg:items-center"
      >
        <div class="tw:max-w-[600px]">
          <h1 class="tw:mb-1 tw:text-2xl tw:font-extrabold">
            Appointment Scheduling Bot
          </h1>
          <p>
            This bot allows users to schedule appointments with your team. It
            also includes an option for users to connect with a live
            representative via WhatsApp for personalized assistance.
          </p>
        </div>

        <ButtonAskLuca class="tw:lg:basis-[280px]" />
      </div>

      <div
        class="tw:scroll-mt-default tw:flex tw:flex-col tw:gap-12 tw:lg:flex-row tw:xl:gap-[74px]"
        ref="chatParent"
      >
        <BotCard>
          <BotSection>
            <BotSectionTitle>
              1. Initial Greeting Message (60 characters)
            </BotSectionTitle>

            <FieldEditableText name="initialMessage" required />
          </BotSection>

          <BotSection>
            <BotSectionTitle>
              2. Follow-Up Greeting with Options
            </BotSectionTitle>

            <FieldEditableText name="secondMessage" required />

            <CardTitle icon="tabler-git-fork" iconVariant="success">
              Quick Reply Options:
            </CardTitle>

            <div class="tw:flex tw:max-w-[237px] tw:flex-col tw:gap-3">
              <FieldEditableText
                name="scheduleACall.title"
                required
                color="dark"
              />

              <FieldEditableText
                name="talkToAgentNow.title"
                required
                color="dark"
              />
            </div>
          </BotSection>

          <BotSection>
            <BotOptionsCard>
              <BotSection>
                <BotSectionTitle
                  @viewSimulation="handleViewSimulation('scheduleACall')"
                >
                  2.1 Flow A: Days of the Week Options
                </BotSectionTitle>

                <BotParagraphField
                  title="Choose a Day"
                  name="scheduleACall.chooseADay"
                />

                <BotOptions name="scheduleACall.chooseADayOptions" />
              </BotSection>

              <BotSection>
                <BotParagraphField
                  title="Choose Time Slot"
                  name="scheduleACall.chooseTimeSlot"
                />

                <BotOptions name="scheduleACall.chooseTimeSlotOptions" />
              </BotSection>

              <BotSection>
                <BotParagraphField
                  title="Flow A: Goodbye Options"
                  name="scheduleACall.endingMessage"
                />
              </BotSection>
            </BotOptionsCard>

            <BotOptionsCard>
              <BotSection>
                <BotSectionTitle
                  @viewSimulation="handleViewSimulation('talkToAnAgentNow')"
                >
                  2.2 Flow B: Connect with an Agent
                </BotSectionTitle>

                <BotParagraphField
                  title="Choose Details"
                  name="talkToAgentNow.chooseDetails"
                />

                <BotOptions name="talkToAgentNow.chooseDetailsOptions" />
              </BotSection>

              <BotSection>
                <BotParagraphField
                  title="Flow A: Goodbye Options"
                  name="talkToAgentNow.endingMessage"
                />
              </BotSection>
            </BotOptionsCard>
          </BotSection>
        </BotCard>

        <BotChat>
          <BotChatMessage>
            <BotChatMessageText>
              {{ values.initialMessage }}
            </BotChatMessageText>
          </BotChatMessage>

          <BotChatMessage>
            <BotChatMessageText>
              {{ values.secondMessage }}
            </BotChatMessageText>

            <BotChatMessageText type="option">
              {{ values.scheduleACall?.title }}
            </BotChatMessageText>

            <BotChatMessageText type="option">
              {{ values.talkToAgentNow?.title }}
            </BotChatMessageText>
          </BotChatMessage>

          <template v-if="viewedSimulation === 'scheduleACall'">
            <BotChatMessage own>
              <BotChatMessageText>
                {{ values.scheduleACall?.title }}
              </BotChatMessageText>
            </BotChatMessage>

            <BotChatMessage>
              <BotChatMessageText>
                {{ values.scheduleACall?.chooseADay }}
              </BotChatMessageText>

              <BotChatMessageText
                v-for="option in values.scheduleACall?.chooseADayOptions"
                type="option"
              >
                {{ option }}
              </BotChatMessageText>
            </BotChatMessage>

            <BotChatMessage own>
              <BotChatMessageText>
                {{ values.scheduleACall?.chooseADayOptions?.[0] }}
              </BotChatMessageText>
            </BotChatMessage>

            <BotChatMessage>
              <BotChatMessageText>
                {{ values.scheduleACall?.chooseTimeSlot }}
              </BotChatMessageText>

              <BotChatMessageText
                v-for="option in values.scheduleACall?.chooseTimeSlotOptions"
                type="option"
              >
                {{ option }}
              </BotChatMessageText>
            </BotChatMessage>

            <BotChatMessage own>
              <BotChatMessageText>
                {{ values.scheduleACall?.chooseTimeSlotOptions?.[0] }}
              </BotChatMessageText>
            </BotChatMessage>

            <BotChatMessage>
              <BotChatMessageText>
                {{ values.scheduleACall?.endingMessage }}
              </BotChatMessageText>
            </BotChatMessage>
          </template>

          <template v-if="viewedSimulation === 'talkToAnAgentNow'">
            <BotChatMessage own>
              <BotChatMessageText>
                {{ values.talkToAgentNow?.title }}
              </BotChatMessageText>
            </BotChatMessage>

            <BotChatMessage>
              <BotChatMessageText>
                {{ values.talkToAgentNow?.chooseDetails }}
              </BotChatMessageText>

              <BotChatMessageText
                v-for="option in values.talkToAgentNow?.chooseDetailsOptions"
                type="option"
              >
                {{ option }}
              </BotChatMessageText>
            </BotChatMessage>

            <BotChatMessage own>
              <BotChatMessageText>
                {{ values.talkToAgentNow?.chooseDetailsOptions?.[0] }}
              </BotChatMessageText>
            </BotChatMessage>

            <BotChatMessage>
              <BotChatMessageText>
                {{ values.talkToAgentNow?.endingMessage }}
              </BotChatMessageText>
            </BotChatMessage>
          </template>
        </BotChat>
      </div>

      <WizardCardActions>
        <WizardButtonGoBack :to="{ name: 'WhatsappBotFunnel' }" />

        <WizardButtonNext :isLoading="isLoading"> SAVE BOT </WizardButtonNext>
      </WizardCardActions>
    </form>
  </WizardCard>
</template>
