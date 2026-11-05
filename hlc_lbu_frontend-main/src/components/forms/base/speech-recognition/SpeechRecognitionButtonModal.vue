<script lang="ts" setup>
const isOpen = defineModel<boolean>({ required: true });
</script>

<template>
  <Modal v-model="isOpen" class="tw:max-w-[660px] tw:p-10" closeButton>
    <div class="tw:mb-12 tw:flex tw:flex-col tw:items-center tw:gap-3">
      <img src="/images/emojis/microphone.png" class="tw:max-h-[120px]" />

      <h2 class="tw:text-center tw:text-[28px] tw:font-extrabold">
        {{ $t("forms.speech-recognition.title") }}
      </h2>

      <div>
        <p class="tw:mb-2">
          {{ $t("forms.speech-recognition.description.paragraph-1") }}
        </p>

        <ul class="tw:mb-8 tw:list-disc tw:pl-8">
          <li>{{ $t("forms.speech-recognition.description.list-item-1") }}</li>
          <li>{{ $t("forms.speech-recognition.description.list-item-2") }}</li>
        </ul>

        <p>
          {{ $t("forms.speech-recognition.description.paragraph-2") }}
        </p>
      </div>
    </div>

    <div class="tw:flex tw:justify-center">
      <Button class="tw:basis-[230px]" type="button" @click="isOpen = false">
        <slot name="continue">
          {{ $t("global.close") }}
        </slot>
      </Button>
    </div>
  </Modal>
</template>
