<script setup lang="ts">
import AdminRolesApi, { AdminUser } from "@/services/settings/AdminRolesApi";

const props = defineProps<{
  data: AdminUser;
}>();
const emit = defineEmits<{ success: [] }>();

const isOpen = defineModel<boolean>({ required: true });
const isDeleting = ref(false);

async function handleDelete() {
  // Call the API to delete the user
  isDeleting.value = true;
  await AdminRolesApi.deleteUser(props.data.account);
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
    <template #title>{{ $t("settings.users.delete-modal.title") }}</template>

    <template #description>
      {{ $t("settings.users.delete-modal.description") }}
    </template>

    <template #actions>
      <Button variant="outlined" :disabled="isDeleting" @click="isOpen = false">
        {{ $t("global.cancel") }}
      </Button>

      <Button @click="handleDelete" :isLoading="isDeleting">
        {{ $t("settings.users.delete-modal.confirm") }}
      </Button>
    </template>
  </ModalGeneric>
</template>
