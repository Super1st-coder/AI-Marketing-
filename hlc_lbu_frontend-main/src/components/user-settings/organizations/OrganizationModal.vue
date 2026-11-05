<script setup lang="ts">
import AdminOrganizationsApi, {
  AdminOrganization,
  AdminOrganizationCreationBody,
  AdminOrganizationEmailIsRegistered,
} from "@/services/settings/AdminOrganizationsApi";
import AdminRolesApi from "@/services/settings/AdminRolesApi";
import { toTypedSchema } from "@vee-validate/yup";
import { array, number, object, string } from "yup";

const props = defineProps<{
  isEditing?: boolean;
  data?: AdminOrganization;
}>();

const emit = defineEmits<{ success: [] }>();
const isOpen = defineModel<boolean>({ required: true });

const { t } = useI18n();
const { data: roles } = await AdminRolesApi.getList();

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

const closeAndReloadTable = () => {
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
};

const onSubmit = handleSubmit(async (values) => {
  // Create organization
  try {
    // Prepare data
    const data: AdminOrganizationCreationBody = {
      first_name: values.firstName,
      last_name: values.lastName,
      email: values.emailAddress,
      roles: values.roles,
    };

    // Whether we are editing or creating
    if (props.isEditing) {
      await AdminOrganizationsApi.update(data);
    } else {
      await AdminOrganizationsApi.create(data);
    }
  } catch (error) {
    if (error instanceof AdminOrganizationEmailIsRegistered) {
      generalErrorMessage.value = t(
        "settings.organizations.errors.email-registered",
      );
      return;
    } else {
      throw error;
    }
  }

  closeAndReloadTable();
});

const isInvitationBeingSent = ref(false);
const isInvitationSent = ref(false);
async function handleSendInvitation() {
  if (props.isEditing && !isInvitationSent.value && props.data) {
    isInvitationBeingSent.value = true;
    await AdminOrganizationsApi.sendInvitation({
      email: props.data.account,
    });
    isInvitationSent.value = true;

    isInvitationBeingSent.value = false;
  }
}

const isReactivating = ref(false);

const isBusy = computed(() => isSubmitting.value || isReactivating.value);

async function handleReactive() {
  if (props.isEditing && props.data) {
    isReactivating.value = true;
    await AdminOrganizationsApi.reactivate({
      email: props.data.account,
    });

    isReactivating.value = false;

    closeAndReloadTable();
  }
}
</script>

<template>
  <Modal
    v-model="isOpen"
    :maxWidth="500"
    :closeButton="!isBusy"
    :closeOnClickOutside="!isBusy"
    v-slot="{ close }"
    as="form"
    @submit.prevent="onSubmit"
  >
    <ModalHeader>
      <template v-if="isEditing">
        {{ t("settings.organizations.modal.edit-title") }}
      </template>
      <template v-else>
        {{ t("settings.organizations.modal.add-title") }}
      </template>
    </ModalHeader>

    <ModalBody>
      <FieldsContainer>
        <FieldText
          name="firstName"
          :label="t('settings.organizations.form.first-name.label')"
          :placeholder="t('settings.organizations.form.first-name.placeholder')"
          required
        />

        <FieldText
          name="lastName"
          :label="t('settings.organizations.form.last-name.label')"
          :placeholder="t('settings.organizations.form.last-name.placeholder')"
          required
        />

        <FieldText
          name="emailAddress"
          :label="t('settings.organizations.form.email-address.label')"
          :placeholder="
            t('settings.organizations.form.email-address.placeholder')
          "
          required
          :disabled="isEditing"
        />

        <FieldNewSelect
          name="roles"
          :label="t('settings.organizations.form.roles.label')"
          :placeholder="t('settings.organizations.form.roles.placeholder')"
          :options="
            roles.map((role) => ({
              label: role.name,
              value: role.id,
            }))
          "
          multiple
          chips
        />

        <Button
          v-if="isEditing && props.data && props.data.status === 'P'"
          variant="label"
          :leftIcon="isInvitationSent ? 'tabler-check' : 'tabler-send'"
          :color="isInvitationSent ? 'success' : 'primary'"
          @click="handleSendInvitation"
          type="button"
          :isLoading="isInvitationBeingSent"
        >
          <template v-if="isInvitationSent">
            {{ t("settings.organizations.invitation.sent") }}
          </template>
          <template v-else>
            {{ t("settings.organizations.invitation.resend") }}
          </template>
        </Button>

        <Button
          v-if="isEditing && props.data && props.data.status === 'I'"
          variant="label"
          leftIcon="tabler-refresh"
          color="primary"
          @click="handleReactive"
          type="button"
          :isLoading="isReactivating"
        >
          {{ t("settings.organizations.reactivate-button") }}
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
        :upercase="false"
        :disabled="isBusy"
        @click="close"
      >
        {{ t("global.cancel") }}
      </Button>

      <Button :upercase="false" :isLoading="isSubmitting">
        <template v-if="isEditing">
          {{ t("global.save") }}
        </template>
        <template v-else>
          {{ t("settings.organizations.create-button") }}
        </template>
      </Button>
    </ModalFooter>
  </Modal>
</template>
