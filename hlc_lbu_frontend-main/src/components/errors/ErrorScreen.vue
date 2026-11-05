<script setup lang="ts">
const props = defineProps<{ error: Error; useDefaultAction?: boolean }>();

const router = useRouter();

const is404Error = computed(
  () => (props.error as { is404?: boolean }).is404 === true,
);

const handleDefaultAction = () => {
  if (is404Error.value) {
    router.push({ name: "BrandList" });
    return;
  }

  router.go(0);
};
</script>

<template>
  <GradientBackground class="tw:w-full">
    <Container
      class="tw:flex tw:min-h-screen tw:items-center tw:justify-center"
      :maxWidth="600"
    >
      <CardBase class="tw:p-6 tw:lg:p-12">
        <CardTitle
          icon="tabler-alert-circle"
          iconVariant="error"
          class="tw:mb-4"
        >
          {{
            $te(`errors.${props.error.message}.title`)
              ? $t(`errors.${props.error.message}.title`)
              : $te(`errors.${props.error.name}.title`)
                ? $t(`errors.${props.error.name}.title`)
                : $t("errors.UNIDENTIFIED_ERROR.title")
          }}
        </CardTitle>

        <p
          class="tw:mb-6 tw:text-justify tw:whitespace-pre-line tw:text-secondary-text"
        >
          {{
            $te(`errors.${props.error.message}.description`)
              ? $t(`errors.${props.error.message}.description`)
              : $te(`errors.${props.error.name}.description`)
                ? $t(`errors.${props.error.name}.description`)
                : $t("errors.UNIDENTIFIED_ERROR.description")
          }}
        </p>

        <div
          v-if="$slots.actions || useDefaultAction"
          class="tw:flex tw:justify-center"
        >
          <Button
            v-if="useDefaultAction"
            type="submit"
            @click="handleDefaultAction"
          >
            {{
              is404Error ? $t("global.go-to-homepage") : $t("global.try-again")
            }}
          </Button>

          <slot name="actions" />
        </div>
      </CardBase>
    </Container>
  </GradientBackground>
</template>
