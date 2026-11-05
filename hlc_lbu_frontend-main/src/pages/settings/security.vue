<script setup lang="ts">
import SettingsApi from "@/services/settings/SettingsApi";
import { toTypedSchema } from "@vee-validate/yup";
import { object, string } from "yup";

const { t } = useI18n();
usePageTitle(() => t("routes.user-settings-security"));
const router = useRouter();
const isLoading = ref(false);
const showModal = ref(false);
const labelNewPassword = ref(t("settings.security.label-new-password"));
const labelCurrentPassword = ref(t("settings.security.label-Old-password"));
const { handleSubmit, errors } = useFormWithErrorScrolling({
  validationSchema: toTypedSchema(
    object({
      security: object({
        oldPassword: string().required(),
        newPassword: string().required(),
      }),
    }),
  ),
  initialValues: {
    security: {
      oldPassword: "",
      newPassword: "",
    },
  },
});

const onSubmit = handleSubmit(async (values) => {
  isLoading.value = true;

  await SettingsApi.updatePassword(
    values.security.oldPassword,
    values.security.newPassword,
  );
  showModal.value = true;
  isLoading.value = false;
});

const handleConfirm = () => {
  router.push({ name: "BrandList" });
};
</script>

<template>
  <form
    class="tw:flex tw:h-full tw:flex-col tw:gap-6 tw:py-6 tw:pb-12"
    @submit.prevent="onSubmit"
  >
    <SettingsFormSecurityChangePasswordModal
      v-model="showModal"
      @confirm="handleConfirm"
    />

    <!-- TODO: add help video URL later -->
    <PageTitle>
      {{ t("settings.security.page-title") }}
    </PageTitle>

    <FieldsContainer>
      <FieldText
        name="security.oldPassword"
        type="password"
        :label="labelCurrentPassword"
        placeholder=""
        orientation="horizontal"
        required
      />
      <FieldText
        name="security.newPassword"
        type="password"
        :label="labelNewPassword"
        placeholder=""
        orientation="horizontal"
        required
      />
    </FieldsContainer>

    <Alert v-if="errors.security" type="error">
      {{ errors.security }}
    </Alert>
    <div class="tw:flex tw:justify-between tw:gap-5 tw:self-stretch">
      <ButtonGoBack type="button" outline :to="{ name: 'BrandList' }" />
      <Button> {{ t("global.update") }}</Button>
    </div>
  </form>
</template>
