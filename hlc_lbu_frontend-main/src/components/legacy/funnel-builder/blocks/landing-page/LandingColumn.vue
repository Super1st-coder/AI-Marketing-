<script lang="ts" setup>
interface Props {
  type?: "header" | "content" | "footer";
}

withDefaults(defineProps<Props>(), {
  type: "content",
});

const isOpen = ref(false);
</script>

<template>
  <div>
    <Separator v-if="type != 'header'" />

    <div class="tw:grid tw:gap-9 tw:lg:grid-cols-3">
      <div
        class="tw:flex tw:flex-col tw:gap-8 tw:pt-8 tw:pb-3"
        :class="{
          'tw:hidden tw:lg:block': type === 'header',
        }"
      >
        <slot name="guidelines" />
      </div>

      <div
        v-if="type != 'header'"
        class="tw:lg:order-last tw:lg:pt-8 tw:lg:pb-3"
      >
        <ButtonAskLuca size="md" class="tw:w-full" />
      </div>

      <div
        :class="[
          'tw:h-full tw:rounded-[20px] tw:bg-white tw:px-5 tw:pt-8 tw:pb-3',
          'tw:shadow-[0px_8px_16px] tw:shadow-primary-text/8',
          {
            'tw:lg:rounded-none': type === 'content',
            'tw:hidden tw:lg:block tw:lg:rounded-b-none': type === 'header',
            'tw:lg:rounded-t-none': type === 'footer',
          },
        ]"
      >
        <component
          :is="type !== 'header' ? 'button' : 'div'"
          @click="isOpen = true"
          type="button"
          class="tw:flex tw:flex-col tw:items-start tw:gap-8 tw:text-left"
        >
          <slot />
        </component>
      </div>
    </div>

    <ModalStandard v-if="type !== 'header'" v-model="isOpen">
      <template #header>
        <CardTitle is="h2">
          <slot name="modalTitle" />
        </CardTitle>
        <CardParagraph v-if="$slots.modalDescription" variant="light">
          <slot name="modalDescription" />
        </CardParagraph>
      </template>

      <template #headerActions>
        <ButtonAskLuca />
      </template>

      <template #body>
        <CardSections>
          <slot name="modalBody" />
        </CardSections>
      </template>

      <template v-if="$slots.modalRight" #right>
        <slot name="modalRight" />
      </template>
    </ModalStandard>
  </div>
</template>
