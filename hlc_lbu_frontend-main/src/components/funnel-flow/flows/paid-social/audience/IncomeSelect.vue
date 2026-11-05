<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from "vue";

type Option = { label: string; value: string | number };

const props = withDefaults(
  defineProps<{
    modelValue: string | number | (string | number)[] | null;
    options: Option[];
    placeholder?: string;
    showClearOption?: boolean;
    multiple?: boolean;
    allowCustom?: boolean;
    error?: string;
  }>(),
  {
    placeholder: "",
    showClearOption: true,
    multiple: false,
    allowCustom: false,
    error: "",
  },
);

const customIncome = ref<string>("");

function selectCustom() {
  if (!props.allowCustom) return;

  const value = customIncome.value.trim();
  if (!value) return;

  emit("update:modelValue", value);
  emit("change", value);

  if (!props.options.some((o) => o.value === value)) {
    props.options.push({ value, label: value });
  }

  toggle(false);
}

const emit = defineEmits<{
  (
    e: "update:modelValue",
    v: string | number | (string | number)[] | null,
  ): void;
  (e: "change", v: string | number | (string | number)[] | null): void;
}>();

const open = ref(false);
const activeIndex = ref(-1);
const root = ref<HTMLElement | null>(null);
const listEl = ref<HTMLElement | null>(null);

const listboxId = `lb-${Math.random().toString(36).slice(2)}`;
const idFor = (i: number) => `${listboxId}-opt-${i}`;
const hasClear = computed(() => !!props.showClearOption && !props.multiple);
const offset = computed(() => (hasClear.value ? 1 : 0));

const activeId = computed(() =>
  activeIndex.value >= 0 ? idFor(activeIndex.value) : undefined,
);

const current = computed(() => {
  if (props.multiple) {
    if (!Array.isArray(props.modelValue)) {
      return [];
    }
    const values = props.modelValue as (string | number)[];
    return props.options.filter((o) => values.includes(o.value));
  } else {
    return props.options.find((o) => o.value === props.modelValue) ?? null;
  }
});

const placeholder = computed(() => props.placeholder ?? "");

function toggle(val?: boolean) {
  open.value = val ?? !open.value;
  if (open.value) {
    if (!props.modelValue && hasClear.value) {
      activeIndex.value = 0;
    } else {
      const idx = props.options.findIndex((o) =>
        props.multiple
          ? Array.isArray(props.modelValue) &&
            props.modelValue.includes(o.value)
          : o.value === props.modelValue,
      );
      activeIndex.value = Math.max(0, idx) + offset.value;
    }
    requestAnimationFrame(() => listEl.value?.focus());
  }
}

function selectNone() {
  emit("update:modelValue", null);
  emit("change", null);
  toggle(false);
}

function select(opt: Option) {
  if (props.multiple) {
    const currentValues = Array.isArray(props.modelValue)
      ? [...props.modelValue]
      : [];
    const exists = currentValues.includes(opt.value);
    const newValues = exists
      ? currentValues.filter((v) => v !== opt.value)
      : [...currentValues, opt.value];
    emit("update:modelValue", newValues);
    emit("change", newValues);
  } else {
    emit("update:modelValue", opt.value);
    emit("change", opt.value);
    toggle(false);
  }
}

function onKeydown(e: KeyboardEvent) {
  if (!open.value) return;
  const max = props.options.length + (hasClear.value ? 1 : 0) - 1;

  if (e.key === "ArrowDown") {
    e.preventDefault();
    move(1, max);
  } else if (e.key === "ArrowUp") {
    e.preventDefault();
    move(-1, max);
  } else if (e.key === "Home") {
    e.preventDefault();
    activeIndex.value = 0;
    scrollIntoView();
  } else if (e.key === "End") {
    e.preventDefault();
    activeIndex.value = max;
    scrollIntoView();
  } else if (e.key === "Enter" || e.key === " ") {
    e.preventDefault();
    if (hasClear.value && activeIndex.value === 0) {
      selectNone();
    } else {
      const idx = activeIndex.value - offset.value;
      if (idx >= 0 && idx < props.options.length) {
        select(props.options[idx]);
      }
    }
  } else if (e.key === "Escape") {
    e.preventDefault();
    toggle(false);
  }
}

function openAndMove(delta: number) {
  if (!open.value) toggle(true);
  const max = props.options.length + (hasClear.value ? 1 : 0) - 1;
  move(delta, max);
}

function move(delta: number, max: number) {
  const next = Math.min(max, Math.max(0, activeIndex.value + delta));
  activeIndex.value = next;
  scrollIntoView();
}

function scrollIntoView() {
  const el = document.getElementById(idFor(activeIndex.value));
  el?.scrollIntoView({ block: "nearest" });
}

function onClickOutside(e: MouseEvent) {
  if (!root.value) return;
  if (!root.value.contains(e.target as Node)) toggle(false);
}
onMounted(() => document.addEventListener("mousedown", onClickOutside));
onBeforeUnmount(() =>
  document.removeEventListener("mousedown", onClickOutside),
);
</script>

<template>
  <div class="tw:relative tw:w-full" @keydown.stop="onKeydown" ref="root">
    <button
      class="tw:flex tw:w-full tw:items-center tw:justify-between tw:gap-2 tw:rounded-lg tw:border tw:bg-white tw:px-3 tw:py-2.5 tw:text-start tw:focus:border-primary tw:focus:outline-hidden"
      :class="[
        props.error
          ? 'tw:border-error'
          : 'tw:border-secondary/30 tw:text-black',
      ]"
      type="button"
      :aria-expanded="open ? 'true' : 'false'"
      :aria-controls="listboxId"
      @click="toggle()"
      @keydown.down.prevent="openAndMove(1)"
      @keydown.up.prevent="openAndMove(-1)"
    >
      <span v-if="multiple">
        <template v-if="(current as Option[]).length">
          {{ (current as Option[]).map((c) => c.label).join(", ") }}
        </template>
        <template v-else>{{ placeholder }}</template>
      </span>
      <span v-else>
        {{ (current as Option | null)?.label ?? placeholder }}
      </span>

      <svg
        class="tw:h-[18px] tw:w-[18px]"
        viewBox="0 0 24 24"
        aria-hidden="true"
      >
        <path d="M7 10l5 5 5-5" fill="none" stroke="#6d5f55" stroke-width="2" />
      </svg>
    </button>

    <div
      v-if="open"
      class="tw:absolute tw:inset-x-0 tw:z-100 tw:mt-[6px] tw:max-h-[280px] tw:overflow-auto tw:rounded-lg tw:border tw:border-secondary/30 tw:bg-white tw:outline-hidden"
      role="listbox"
      :id="listboxId"
      :aria-activedescendant="activeId"
      tabindex="-1"
      ref="listEl"
    >
      <div
        v-if="hasClear"
        :id="idFor(0)"
        role="option"
        :aria-selected="modelValue == null ? 'true' : 'false'"
        @mousemove="activeIndex = 0"
        @click="selectNone"
        class="tw:grid tw:grid-cols-[1fr_auto] tw:gap-2 tw:px-[14px] tw:py-3 tw:text-sm tw:hover:cursor-pointer tw:hover:bg-secondary/10"
        :class="{
          'tw:bg-secondary/10': activeIndex === 0,
          'tw:bg-primary/10 tw:font-semibold': modelValue == null,
        }"
      >
        <div class="tw:truncate">{{ placeholder }}</div>
      </div>

      <div
        v-for="(opt, i) in options"
        :key="opt.value"
        :id="idFor(i + offset)"
        role="option"
        :aria-selected="
          multiple
            ? Array.isArray(modelValue) && modelValue.includes(opt.value)
            : opt.value === modelValue
        "
        @mousemove="activeIndex = i + offset"
        @click="select(opt)"
        class="tw:flex tw:items-center tw:gap-2 tw:px-[14px] tw:py-3 tw:text-sm tw:hover:cursor-pointer tw:hover:bg-secondary/10"
        :class="{
          'tw:bg-secondary/10': activeIndex === i + offset,
          'tw:bg-primary/10 tw:font-semibold': multiple
            ? Array.isArray(modelValue) && modelValue.includes(opt.value)
            : opt.value === modelValue,
          'tw:border-t tw:border-primary/10': i + offset > 0,
        }"
      >
        <template v-if="multiple">
          <input
            type="checkbox"
            class="tw:h-4 tw:w-4 tw:rounded tw:border-secondary"
            :checked="
              Array.isArray(modelValue) && modelValue.includes(opt.value)
            "
            @change.stop="select(opt)"
          />
        </template>

        <div class="tw:truncate">{{ opt.label }}</div>
      </div>

      <div
        v-if="!multiple && allowCustom"
        :id="idFor(props.options.length + offset)"
        role="option"
        :aria-selected="
          typeof modelValue === 'string' &&
          !options.some((o) => o.value === modelValue)
        "
        @mousemove="activeIndex = props.options.length + offset"
        class="tw:flex tw:flex-col tw:gap-2 tw:px-[14px] tw:py-3 tw:text-sm tw:hover:cursor-pointer tw:hover:bg-secondary/10"
        :class="{
          'tw:bg-secondary/10': activeIndex === props.options.length + offset,
          'tw:bg-primary/10 tw:font-semibold':
            typeof modelValue === 'string' &&
            !options.some((o) => o.value === modelValue),
          'tw:border-t tw:border-primary/10': props.options.length > 0,
        }"
      >
        <div @click.stop>
          <div class="tw:mb-1">
            {{ $t("global.other") }}
          </div>
          <div class="tw:flex">
            <input
              v-model="customIncome"
              type="text"
              class="tw:w-full tw:flex-1 tw:rounded tw:border tw:border-secondary/40 tw:px-2 tw:py-1 tw:text-sm tw:focus:border-primary tw:focus:outline-hidden"
              :placeholder="
                $t('funnel-flow.paid-social.income-select.enter-custom-income')
              "
              @keydown.enter.prevent="selectCustom"
            />
            <Button
              v-if="customIncome"
              :size="'sm'"
              @click="selectCustom"
              class="tw:ml-2 tw:rounded tw:bg-primary tw:px-2 tw:py-1 tw:text-xs tw:text-white tw:hover:bg-primary/80"
            >
              {{ $t("global.save") }}
            </Button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
