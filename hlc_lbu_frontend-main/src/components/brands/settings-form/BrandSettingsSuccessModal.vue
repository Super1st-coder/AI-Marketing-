<script setup lang="ts">
const isOpen = defineModel<boolean>({ required: true });

defineProps<{
  variant: "manual" | "extracted";
}>();

const router = useRouter();
const route = useRoute();

const handleClose = () => {
  // Remove the justCreated query parameter
  router.replace({
    name: route.name ?? undefined,
    params: route.params,
    query: { ...route.query, justCreated: undefined },
  });
  isOpen.value = false;
};

const handleContinue = () => {
  handleClose();
};
</script>

<template>
  <ModalGeneric
    v-model="isOpen"
    imageSrc="/images/celebrar-image.png"
    :maxWidth="500"
    variant="centered"
    @close="handleClose"
  >
    <template #title>
      {{
        $t(
          variant === "manual"
            ? "brands.settings.success-modal.manual-title"
            : "brands.settings.success-modal.title",
        )
      }}
    </template>

    <template #description>
      {{
        $t(
          variant === "manual"
            ? "brands.settings.success-modal.manual-description"
            : "brands.settings.success-modal.description",
        )
      }}
    </template>

    <template #actions>
      <Button @click="handleContinue">
        {{
          $t(
            variant === "manual"
              ? "brands.settings.success-modal.get-started"
              : "global.continue",
          )
        }}
      </Button>
    </template>
  </ModalGeneric>
</template>
