<script setup lang="ts">
export interface AdPreviewProps {
  clampLines?: boolean;
  accountName?: string;
  primaryText?: string;
  headline?: string;
  description?: string;
  cta?: string;
  imageSrc?: string;
  videoSrc?: string;
  isVideo?: boolean;
  uppercase?: boolean;
  likeCount?: number;
  commentCount?: number;
  size?: "sm" | "lg";
  aspectRatio?: "auto" | number;
}

const props = withDefaults(defineProps<AdPreviewProps>(), {
  clampLines: false,
  isVideo: false,
  uppercase: true,
  size: "sm",
  aspectRatio: 4 / 5,
});

const emit = defineEmits<{
  /** The video couldn't be loaded or played, e.g. its link expired. */
  videoError: [];
}>();

const { t, te } = useI18n();

const accountInitial = computed(() =>
  props.accountName ? getUserInitials(props.accountName.trim(), 1) : "",
);

const ctaTranslationKey = computed(() =>
  props.cta ? `meta-ads.cta.options.${props.cta}` : undefined,
);

const ctaText = computed(() =>
  ctaTranslationKey.value && te(ctaTranslationKey.value)
    ? t(ctaTranslationKey.value)
    : anyCaseToText(props.cta ?? ""),
);
</script>

<template>
  <CardBase class="tw:flex tw:flex-col tw:overflow-hidden tw:text-left">
    <!-- Account -->
    <div
      v-if="accountName"
      class="tw:flex tw:items-center tw:gap-2.5"
      :class="{ 'tw:p-3': size === 'sm', 'tw:px-5 tw:py-4': size === 'lg' }"
    >
      <!-- Account initial/image -->
      <div
        class="tw:flex tw:shrink-0 tw:items-center tw:justify-center tw:rounded-full tw:bg-primary/15"
        :class="{ 'tw:size-10': size === 'sm', 'tw:size-12': size === 'lg' }"
      >
        <span
          class="tw:font-medium tw:text-primary"
          :class="{
            'tw:text-lg': size === 'lg',
            'tw:text-base': size === 'sm',
          }"
        >
          {{ accountInitial }}
        </span>
      </div>

      <div class="tw:flex tw:min-w-0 tw:flex-col tw:gap-0.5">
        <!-- Account name -->
        <p
          class="tw:truncate tw:font-bold"
          :class="{
            'tw:text-xs': size === 'sm',
            'tw:text-sm': size === 'lg',
          }"
        >
          {{ accountName }}
        </p>

        <!-- Sponsored -->
        <p class="tw:flex tw:items-center tw:gap-1 tw:text-gray-400">
          <span class="tw:text-xs">{{ $t("meta-ad-preview.sponsored") }}</span>

          <Icon icon="tabler:world" class="tw:text-[16px]" />
        </p>
      </div>
    </div>

    <!-- Primary text -->
    <div
      v-if="primaryText"
      class="tw:pb-2.5"
      :class="{
        'tw:pt-0': accountName,
        'tw:p-3': size === 'sm',
        'tw:px-5 tw:py-4': size === 'lg',
      }"
    >
      <p
        class="tw:whitespace-pre-line"
        :class="{
          'tw:line-clamp-3': clampLines,
          'tw:text-xs': size === 'sm',
          'tw:text-sm': size === 'lg',
        }"
      >
        {{ primaryText }}
      </p>
    </div>

    <!-- Media -->
    <div
      class="tw:relative tw:isolate tw:w-full tw:bg-gray-100"
      :style="{ aspectRatio: aspectRatio }"
    >
      <slot name="media">
        <!-- With a fixed aspect ratio the box sets the size, so the video fills it -->
        <video
          v-if="videoSrc"
          :src="videoSrc"
          :poster="imageSrc"
          class="tw:block tw:w-full tw:bg-black tw:object-contain"
          :class="{
            'tw:absolute tw:inset-0 tw:h-full': aspectRatio !== 'auto',
          }"
          controls
          playsinline
          preload="metadata"
          @error="emit('videoError')"
        />
        <ImgAndPdf
          v-else-if="imageSrc"
          :src="imageSrc"
          class="tw:h-full tw:w-full tw:object-contain"
        />
        <div
          v-else
          class="tw:absolute tw:inset-0 tw:flex tw:flex-col tw:items-center tw:justify-center tw:gap-2 tw:text-secondary-text"
        >
          <Icon icon="tabler:photo" class="tw:text-[48px]" />

          <span class="tw:text-xs">
            {{ $t("meta-ad-preview.no-image") }}
          </span>
        </div>
      </slot>

      <Chip
        v-if="isVideo"
        size="sm"
        color="secondary"
        variant="label"
        leftIcon="tabler:video"
        :uppercase="uppercase"
        class="tw:pointer-events-none tw:absolute tw:top-2 tw:left-2"
      >
        {{ $t("meta-ad-preview.video") }}
      </Chip>
    </div>

    <!-- Headline and description -->
    <div
      v-if="headline || description || cta"
      class="tw:flex tw:items-start tw:bg-[#F0F2F5]"
      :class="{
        'tw:gap-2 tw:p-3 tw:pt-2.5': size === 'sm',
        'tw:gap-4 tw:px-5 tw:pt-4 tw:pb-6': size === 'lg',
      }"
    >
      <div v-if="headline || description" class="tw:grow">
        <!-- Headline -->
        <div
          v-if="headline"
          class="tw:font-semibold tw:whitespace-pre-line"
          :class="{
            'tw:line-clamp-1': clampLines,
            'tw:text-xs': size === 'sm',
            'tw:text-base': size === 'lg',
          }"
        >
          {{ headline }}
        </div>

        <!-- Description -->
        <div
          v-if="description"
          class="tw:whitespace-pre-line tw:text-secondary-text"
          :class="{
            'tw:line-clamp-1': clampLines,
            'tw:text-xs': size === 'sm',
            'tw:text-sm': size === 'lg',
          }"
        >
          {{ description }}
        </div>
      </div>

      <div
        v-if="cta"
        class="tw:rounded-lg tw:bg-[#E4E6EB] tw:font-medium tw:whitespace-nowrap"
        :class="{
          'tw:px-3 tw:py-2 tw:text-xs': size === 'sm',
          'tw:px-4 tw:py-3 tw:text-sm': size === 'lg',
        }"
      >
        {{ ctaText }}
      </div>
    </div>

    <!-- Engagement footer -->
    <div
      v-if="Boolean(accountName || likeCount || commentCount)"
      class="tw:flex tw:items-center tw:justify-between tw:text-secondary-text"
      :class="{
        'tw:text-xs': size === 'sm',
        'tw:text-sm': size === 'lg',

        'tw:px-5 tw:py-4': size === 'lg',
        'tw:px-3 tw:py-2.5': size === 'sm',
      }"
    >
      <!-- Like count -->
      <span class="tw:flex tw:items-center tw:gap-1">
        <Icon icon="tabler:thumb-up" class="tw:text-[16px]" />

        <span v-if="likeCount !== undefined">
          {{ likeCount.toLocaleString() }}
        </span>
        <span v-else>{{ $t("meta-ad-preview.like") }}</span>
      </span>

      <!-- Comment count -->
      <span v-if="commentCount !== undefined">
        {{
          $t("meta-ad-preview.comment-count", {
            count: commentCount.toLocaleString(),
          })
        }}
      </span>
      <span v-else>{{ $t("meta-ad-preview.comment") }}</span>
    </div>
  </CardBase>
</template>
