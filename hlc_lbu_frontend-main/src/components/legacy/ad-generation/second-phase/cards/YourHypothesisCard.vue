<script lang="ts">
import { useField } from "vee-validate";
import { object, InferType, boolean, string, lazy, number } from "yup";
import { mapValues } from "lodash";

export const yourHypothesisSchema = object().shape({
  id: number().required(),
  selected: boolean(),
  name: string(),
  paragraph: string(),
  options: lazy((obj) => object(mapValues(obj, () => string().required()))),
});

export type YourHypothesis = InferType<typeof yourHypothesisSchema>;
</script>

<script lang="ts" setup>
interface Props {
  name: string;
  sentence: string;
  options?: Record<string, string[]>;
}

const props = defineProps<Props>();

const emits = defineEmits<{
  checked: [checked: boolean];
}>();

const { value: model } = useField<YourHypothesis>(() => props.name, undefined);
const { value: isSelected } = useField<boolean>(`${props.name}.selected`);
const { setValue: setParagraphValue } = useField<string>(
  `${props.name}.paragraph`,
  undefined,
);

watch(isSelected, () => {
  emits("checked", isSelected.value);
});

const splittedSentence = computed(() => {
  let result: string[] = [];
  let accumulator = "";

  for (const char of props.sentence) {
    if (char === "{") {
      result.push(accumulator);
      accumulator = char;
    } else if (char === "}") {
      accumulator += char;
      result.push(accumulator);
      accumulator = "";
    } else {
      accumulator += char;
    }
  }

  return result;
});

const isWordAnOption = (word: string) =>
  word.startsWith("{") && word.endsWith("}");

const optionIndexes = computed<Map<string, number>>(() => {
  const map = new Map<string, number>();

  let counter = 0;

  const words = splittedSentence.value;
  for (const word of words) {
    if (isWordAnOption(word)) {
      map.set(word, counter);
      counter++;
    }
  }

  return map;
});

const getOptionKey = (word: string) => word.replace("{", "").replace("}", "");
const ouputParagraph = computed(() => {
  return splittedSentence.value
    .map((part) => {
      if (isWordAnOption(part)) {
        return model.value.options[getOptionKey(part)];
      }

      return part;
    })
    .join("");
});

// Create the output whenever an option changes
watch(
  ouputParagraph,
  (value) => {
    setParagraphValue(value);
  },
  { immediate: true },
);
</script>

<template>
  <SelectableCard v-model:selected="isSelected">
    <template #header>
      <CardTitle is="h2">
        {{ model.name }}
      </CardTitle>
    </template>

    <div class="tw:rounded-[10px] tw:bg-[#F4F2F2] tw:p-3">
      <p class="tw:text-lg tw:text-secondary-text">
        <template v-for="word in splittedSentence">
          <YourHypothesisCardOption
            v-if="isWordAnOption(word)"
            :name="`${name}.options.${getOptionKey(word)}`"
            :index="optionIndexes.get(word) ?? 0"
            :options="options?.[getOptionKey(word)] ?? []"
          >
          </YourHypothesisCardOption>
          <span v-else>
            {{ word }}
          </span>
        </template>
      </p>
    </div>
    <ButtonAskLuca />
  </SelectableCard>
</template>
