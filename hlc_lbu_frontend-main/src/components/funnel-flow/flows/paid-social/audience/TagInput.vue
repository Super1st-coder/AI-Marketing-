<template>
  <div
    class="tw:flex tw:cursor-text tw:flex-wrap tw:items-center tw:gap-x-2.5 tw:gap-y-2 tw:rounded-lg tw:border tw:bg-white tw:px-3 tw:py-2.5"
    :class="[
      focused ? 'tw:border-primary' : '',
      props.error ? 'tw:border-error' : 'tw:border-secondary/30',
    ]"
    @click="focusInput"
  >
    <template v-for="(tag, i) in internalTags" :key="tag + '-' + i">
      <span
        class="tw:inline-flex tw:items-center tw:gap-2 tw:rounded-2xl tw:bg-[#fff3ea] tw:px-2.5 tw:py-1.5 tw:text-sm tw:leading-none tw:whitespace-normal tw:text-[#5a4d43]"
      >
        {{ tag }}
        <button
          class="tw:cursor-pointer tw:border-0 tw:bg-transparent tw:text-base tw:leading-none tw:text-[#6d5f55] tw:hover:opacity-80"
          type="button"
          @click.stop="removeTag(i)"
        >
          ×
        </button>
      </span>
    </template>

    <input
      ref="inputEl"
      v-model="draft"
      class="tw:flex-1 tw:border-0 tw:px-0 tw:py-1.5 tw:text-sm tw:placeholder:text-secondary/70 tw:focus:outline-hidden"
      :placeholder="placeholder"
      @keydown="onKeydown"
      @blur="onBlur"
      @focus="focused = true"
      @input="onInput"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, watch, computed } from "vue";

type Emit = {
  (e: "update:modelValue", v: string[]): void;
  (e: "add", v: string): void;
  (e: "remove", v: string): void;
  (e: "change", v: string[]): void;
};

const props = withDefaults(
  defineProps<{
    modelValue: string[];
    placeholder?: string;
    separators?: string[];
    allowDuplicates?: boolean;
    max?: number | null;
    trimOnPaste?: boolean;
    error?: string | boolean;
  }>(),
  {
    placeholder: "Type interests",
    separators: () => [","],
    allowDuplicates: false,
    max: null,
    trimOnPaste: true,
    error: "",
  },
);

const emit = defineEmits<Emit>();

const internalTags = ref<string[]>([...props.modelValue]);
watch(
  () => props.modelValue,
  (v) => (internalTags.value = [...v]),
);

const draft = ref("");
const inputEl = ref<HTMLInputElement | null>(null);
const focused = ref(false);

const normalizedDraft = computed(() => draft.value.trim());

function focusInput() {
  inputEl.value?.focus();
}

function commitDraft() {
  if (!normalizedDraft.value) return;
  addTag(normalizedDraft.value);
  draft.value = "";
}

function addTag(raw: string) {
  let value = raw.trim();
  if (!value) return;
  if (!props.allowDuplicates) {
    const exists = internalTags.value.some(
      (t) => t.toLowerCase() === value.toLowerCase(),
    );
    if (exists) return;
  }
  if (props.max !== null && internalTags.value.length >= props.max) return;

  internalTags.value.push(value);
  emit("update:modelValue", internalTags.value);
  emit("add", value);
  emit("change", internalTags.value);
}

function removeTag(index: number) {
  const [removed] = internalTags.value.splice(index, 1);
  emit("update:modelValue", internalTags.value);
  emit("remove", removed);
  emit("change", internalTags.value);
}

function onKeydown(e: KeyboardEvent) {
  const key = e.key;
  const isSeparator =
    key === "Enter" ||
    key === "Tab" ||
    (props.separators?.includes(",") && key === ",") ||
    props.separators?.includes(key);

  if (isSeparator) {
    e.preventDefault();
    commitDraft();
    return;
  }

  if (key === "Backspace" && !draft.value && internalTags.value.length) {
    e.preventDefault();
    removeTag(internalTags.value.length - 1);
    return;
  }

  if (key === "Enter") e.preventDefault();
}

function onBlur() {
  focused.value = false;
  commitDraft();
}

function onInput(e: Event) {
  const target = e.target as HTMLInputElement;
  if (props.trimOnPaste && target.value.includes(",")) {
    const parts = target.value
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
    if (parts.length > 1) {
      parts.forEach(addTag);
      draft.value = "";
    }
  }
}
</script>

hrthe,ejert,y454
