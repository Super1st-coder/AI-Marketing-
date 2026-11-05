<script lang="ts" setup>
import WhatsappBotFunnelAPI, {
  WhatsappBotFunnelType,
  whatsappBotFunnelTypes,
} from "@/services/legacy/WhatsappBotFunnelAPI";
import { toTypedSchema } from "@vee-validate/yup";
import { useRoute, useRouter } from "vue-router";
import { mixed, object, string } from "yup";

const router = useRouter();
const route = useRoute();
const isModalOpen = ref(false);
const isLoading = ref(false);

const projectId = parseInt(route.params.id as string);
const { data: generatedData } =
  await WhatsappBotFunnelAPI.getElements(projectId);
const { data: configuredData } =
  await WhatsappBotFunnelAPI.getConfigured(projectId);

const { handleSubmit, resetForm, isFieldDirty, meta, values } =
  useFormWithErrorScrolling({
    validationSchema: toTypedSchema(
      object().shape({
        prompt: string().required("Este campo es requerido"),
        type: mixed<WhatsappBotFunnelType>()
          .oneOf(whatsappBotFunnelTypes)
          .required(),
      }),
    ),
  });

const handleSelect = (type: WhatsappBotFunnelType) => {
  isModalOpen.value = true;

  const prompt =
    type === configuredData.whatsapp_bot_scheduling_configured.selected_type
      ? generatedData.whatsapp_bot_scheduling_custom_tone_message
      : undefined;

  resetForm({
    values: {
      prompt,
      type,
    },
  });
};

const onSubmit = handleSubmit(async (values) => {
  isLoading.value = true;

  if (isFieldDirty("prompt")) {
    await WhatsappBotFunnelAPI.generateElements(projectId, values.prompt);
    await WhatsappBotFunnelAPI.configure(projectId, {
      selected_type: values.type,
    });
  }

  router.push({ name: "WhatsappBotFunnelSettings" });
});
</script>

<template>
  <WizardCard
    paddingY="lg"
    class="tw:flex tw:flex-col tw:gap-[40px] tw:lg:gap-[60px]"
  >
    <div>
      <WizardCardTitle>
        WhatsApp bot funnel
        <template #button>
          <HelpButton> Help info </HelpButton>
        </template>
      </WizardCardTitle>

      <WizardCardParagraph>
        Automate follow-up communication with leads via WhatsApp, providing
        instant responses, product information, and guidance through the funnel.
      </WizardCardParagraph>
    </div>

    <CardGrid class="tw:items-start">
      <BotIntensityCard
        imageSrc="/images/emoji-smiling-face-with-halo.png"
        @select="handleSelect('information_and_support_bot')"
        :selected="
          configuredData.whatsapp_bot_scheduling_configured?.selected_type ===
          'information_and_support_bot'
        "
      >
        <template #title> Information & Support Bot </template>

        <template #tags>
          <Chip size="md">Product Links</Chip>
          <Chip size="md">Support Agent</Chip>
        </template>

        <template #description>
          This bot helps deliver key information to users about your products or
          services in a clear and friendly manner. It also includes an option
          for users to connect with a live representative via WhatsApp for
          personalized assistance.
        </template>
      </BotIntensityCard>

      <BotIntensityCard
        imageSrc="/images/emoji-robot.png"
        @select="handleSelect('appointment_scheduling_bot')"
        :selected="
          configuredData.whatsapp_bot_scheduling_configured?.selected_type ===
          'appointment_scheduling_bot'
        "
      >
        <template #title> Appointment Scheduling Bot </template>

        <template #tags>
          <Chip size="md">Scheduler</Chip>
          <Chip size="md">Support Agent</Chip>
        </template>

        <template #description>
          This bot allows users to schedule appointments with your team. Let
          users select the time and method that suits them best. It also
          includes an option for users to connect with a live representative via
          WhatsApp for personalized assistance.
        </template>
      </BotIntensityCard>

      <BotIntensityCard
        imageSrc="/images/emoji-saluting-face.png"
        @select="handleSelect('contact_directory_bot')"
        :selected="
          configuredData.whatsapp_bot_scheduling_configured?.selected_type ===
          'contact_directory_bot'
        "
      >
        <template #title> Contact Directory Bot </template>

        <template #tags>
          <Chip size="md">Contact Directory</Chip>
          <Chip size="md">Support Agent</Chip>
        </template>

        <template #description>
          This bot provides links to specific departments within your
          organization and direct phone numbers. It also includes an option for
          users to connect with a live representative via WhatsApp for
          personalized assistance.
        </template>
      </BotIntensityCard>
    </CardGrid>

    <Modal v-model="isModalOpen" closeButton innerClass="tw:max-w-[848px]!">
      <form @submit="onSubmit" class="tw:flex tw:flex-col tw:gap-8">
        <h2 class="tw:text-[28px] tw:font-extrabold tw:text-black">
          Customize Your Bot’s Tone and Message
        </h2>

        <FieldTextarea
          name="prompt"
          label="Add details to guide the tone and content of your bot"
          placeholder="e.g. Focus on our Black Friday discount and use a friendly and professional tone."
        />

        <Button :isLoading="isLoading">
          {{
            values.type ===
            configuredData.whatsapp_bot_scheduling_configured.selected_type
              ? meta.dirty
                ? "Generate bot again"
                : "Edit bot"
              : "Generate bot"
          }}
        </Button>
      </form>
    </Modal>

    <WizardCardActions>
      <WizardButtonGoBack :to="{ name: 'PaidSocial' }" />
    </WizardCardActions>
  </WizardCard>
</template>
