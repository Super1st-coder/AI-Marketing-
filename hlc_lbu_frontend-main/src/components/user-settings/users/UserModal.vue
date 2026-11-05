<script setup lang="ts">
import AdminRolesApi, {
  AdminUser,
  AdminUserCreationBody,
  AdminUserEmailIsRegistered,
} from "@/services/settings/AdminRolesApi";
import { PermissionError } from "@/services/common-errors";
import { toTypedSchema } from "@vee-validate/yup";
import { array, number, object, string } from "yup";

const props = defineProps<{
  isEditing?: boolean;
  data?: AdminUser;
}>();

const emit = defineEmits<{ success: [] }>();
const isOpen = defineModel<boolean>({ required: true });

const { t, te } = useI18n();
const { data: roles } = await AdminRolesApi.getList();

const roleOptions = computed(() =>
  roles.map((role) => {
    const key = `roles.${role.name}.title`;

    return {
      label: te(key) ? t(key) : role.name,
      value: role.id,
    };
  }),
);

const schema = computed(() =>
  toTypedSchema(
    object({
      firstName: string().required(t("forms.required-field")),
      lastName: string().required(t("forms.required-field")),
      emailAddress: string().required(t("forms.required-field")),
      roles: array()
        .of(number().required())
        .required(t("forms.required-field")),
    }),
  ),
);

const { handleSubmit, isSubmitting, resetForm } = useFormWithErrorScrolling({
  validationSchema: schema,
  initialValues:
    props.isEditing && props.data
      ? {
          firstName: props.data.extra_info.first_name,
          lastName: props.data.extra_info.last_name,
          emailAddress: props.data.account,
          roles: props.data.roles.map((role) => role.id),
        }
      : undefined,
});

const generalErrorMessage = ref<string>();

const onSubmit = handleSubmit(async (values) => {
  // Create user
  try {
    // Prepare data
    const data: AdminUserCreationBody = {
      first_name: values.firstName,
      last_name: values.lastName,
      email: values.emailAddress,
      roles: values.roles,
    };

    // Whether we are editing or creating
    if (props.isEditing) {
      await AdminRolesApi.updateUser(data);
    } else {
      await AdminRolesApi.addUser(data);
    }
  } catch (error) {
    if (error instanceof AdminUserEmailIsRegistered) {
      generalErrorMessage.value = t("settings.users.errors.email-registered");
      return;
    } else if (error instanceof PermissionError) {
      generalErrorMessage.value = t("settings.users.errors.no-permission");
      return;
    } else {
      throw error;
    }
  }

  // Reset the form
  resetForm({
    values: {
      firstName: undefined,
      lastName: undefined,
      emailAddress: undefined,
      roles: undefined,
    },
  });

  // Close
  isOpen.value = false;
  emit("success");
});

const isInvitationBeingSent = ref(false);
const isInvitationSent = ref(false);

async function handleSendInvitation() {
  if (props.isEditing && !isInvitationSent.value && props.data) {
    isInvitationBeingSent.value = true;
    await AdminRolesApi.sendUserInvitation({
      email: props.data.account,
    });
    isInvitationSent.value = true;

    isInvitationBeingSent.value = false;
  }
}
</script>

<template>
  <Modal
    v-model="isOpen"
    :maxWidth="500"
    :closeButton="!isSubmitting"
    :closeOnClickOutside="!isSubmitting"
    v-slot="{ close }"
    as="form"
    @submit.prevent="onSubmit"
  >
    <ModalHeader>
      <template v-if="isEditing">{{ $t("settings.users.edit-user") }}</template>
      <template v-else>{{ $t("settings.users.add-new-user") }}</template>
    </ModalHeader>

    <ModalBody>
      <FieldsContainer>
        <FieldText
          name="firstName"
          :label="$t('settings.users.form.first-name.label')"
          :placeholder="$t('settings.users.form.first-name.placeholder')"
          required
        />

        <FieldText
          name="lastName"
          :label="$t('settings.users.form.last-name.label')"
          :placeholder="$t('settings.users.form.last-name.placeholder')"
          required
        />

        <FieldText
          name="emailAddress"
          :label="$t('settings.users.form.email-address.label')"
          :placeholder="$t('settings.users.form.email-address.placeholder')"
          required
          :disabled="isEditing"
        />

        <FieldNewSelect
          name="roles"
          :label="$t('settings.users.form.roles.label')"
          :placeholder="$t('settings.users.form.roles.placeholder')"
          :options="roleOptions"
          multiple
          chips
        />

        <Button
          v-if="
            isEditing &&
            props.data &&
            (props.data.status === 'P' || props.data.status === 'I')
          "
          variant="label"
          :leftIcon="isInvitationSent ? 'tabler-check' : 'tabler-send'"
          :color="isInvitationSent ? 'success' : 'primary'"
          @click="handleSendInvitation"
          type="button"
          :isLoading="isInvitationBeingSent"
        >
          <template v-if="isInvitationSent">{{
            $t("settings.users.invitation-sent")
          }}</template>
          <template v-else>{{
            $t("settings.users.invitation-resend")
          }}</template>
        </Button>

        <Alert v-if="generalErrorMessage" type="error" autoScroll>
          {{ generalErrorMessage }}
        </Alert>
      </FieldsContainer>
    </ModalBody>

    <ModalFooter>
      <Button
        variant="outlined"
        type="button"
        :disabled="isSubmitting"
        @click="close"
      >
        {{ $t("global.cancel") }}
      </Button>

      <Button :isLoading="isSubmitting">
        <template v-if="isEditing">{{ $t("global.save") }}</template>
        <template v-else>{{ $t("settings.users.create-button") }}</template>
      </Button>
    </ModalFooter>
  </Modal>
</template>
