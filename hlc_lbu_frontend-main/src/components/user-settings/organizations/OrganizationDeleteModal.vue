<script setup lang="ts">
import AdminOrganizationsApi, {
  AdminOrganization,
} from "@/services/settings/AdminOrganizationsApi";

const props = defineProps<{
  data: AdminOrganization;
}>();
const emit = defineEmits<{ success: [] }>();

const isOpen = defineModel<boolean>({ required: true });
const isDeleting = ref(false);
const { t } = useI18n();

async function handleDelete() {
  // Call the API to delete the organization
  isDeleting.value = true;
  await AdminOrganizationsApi.delete(props.data.account);
  isDeleting.value = false;

  // Close the modal and emit success
  isOpen.value = false;
  emit("success");
}
</script>

<template>
  <ModalGeneric
    v-model="isOpen"
    :maxWidth="660"
    :closeButton="!isDeleting"
    :closeOnClickOutside="!isDeleting"
    imageSrc="/images/emojis/crying-face.png"
    @close="isOpen = false"
  >
    <template #title>
      {{ t("settings.organizations.delete-modal.title") }}
    </template>

    <template #description>
      <p class="tw:whitespace-pre-line">
        {{ t("settings.organizations.delete-modal.description") }}
      </p>
    </template>

    <template #actions>
      <Button variant="outlined" :disabled="isDeleting" @click="isOpen = false">
        {{ t("global.cancel") }}
      </Button>

      <Button @click="handleDelete" :isLoading="isDeleting">
        {{ t("settings.organizations.delete-modal.confirm") }}
      </Button>
    </template>
  </ModalGeneric>
</template>
