<script setup lang="ts">
const dontShowAgain = useLocalStorage<boolean>(
  "dontShowAgain.ads-editor-tutorial",
  false,
);

const isOpen = ref(!dontShowAgain.value);

// Lets the editor header's help button reopen the tutorial on demand
function open() {
  isOpen.value = true;
}

defineExpose({ open });
</script>

<template>
  <ModalGeneric
    v-model="isOpen"
    v-model:dontShowAgain="dontShowAgain"
    name="ads-editor-tutorial"
    :maxWidth="848"
    videoSrc="https://www.youtube.com/watch?v=Z9g9rL6T3IE"
    displayShowCheckbox
  >
    <template #title>
      {{ $t("funnel-flow.paid-social.ads.refine.editor.tutorial.title") }}
    </template>

    <template #description>
      <span class="tw:whitespace-pre-line">
        {{
          $t("funnel-flow.paid-social.ads.refine.editor.tutorial.description")
        }}
      </span>
    </template>

    <template #continue>
      {{ $t("funnel-flow.paid-social.ads.refine.editor.tutorial.confirm") }}
    </template>
  </ModalGeneric>
</template>
