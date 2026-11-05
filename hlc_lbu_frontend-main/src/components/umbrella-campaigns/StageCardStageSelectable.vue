<script setup lang="ts">
interface Stage {
  name: string;
  display_name: string;
  text?: string;
}

const props = defineProps<{
  stages: Stage[];
  modelValue?: string[] | null;
}>();

const emit = defineEmits([
  "update:modelValue",
  "add-custom-stage",
  "edit-stage-context",
]);

const selectedStages = computed(() => props.modelValue ?? []);

function handleClick(stage: Stage) {
  if (selectedStages.value.includes(stage.name)) {
    // Delete
    emit(
      "update:modelValue",
      selectedStages.value.filter((s) => s !== stage.name),
    );
  } else {
    // Add
    emit("update:modelValue", [...selectedStages.value, stage.name]);
    emit("edit-stage-context", stage);
  }
}

const normalizedStages = computed(() =>
  props.stages.map((stage) => ({
    name: stage.name,
    display_name: stage.display_name,
    text: stage.text ?? "",
  })),
);
</script>

<template>
  <div>
    <h3 class="tw:mb-4 tw:text-xl tw:font-bold">
      {{ $t("umbrella-campaign.step-scene.stages.available-stages") }}
    </h3>
    <div class="tw:grid tw:grid-cols-2 tw:gap-4 tw:md:grid-cols-4">
      <button
        v-for="stage in normalizedStages"
        :key="stage.name"
        @click="handleClick(stage)"
        class="tw:relative tw:flex tw:h-[120px] tw:cursor-pointer tw:flex-col tw:items-center tw:justify-center tw:rounded-xl tw:border-2 tw:bg-white tw:p-4 tw:text-center tw:shadow tw:transition"
        :class="
          selectedStages.includes(stage.name)
            ? 'tw:border-[#28c76f] tw:bg-[#f3fff6] tw:shadow-[0_0_0_2px_#28c76f33]'
            : 'tw:border-transparent tw:hover:border-[#28c76f]'
        "
        type="button"
      >
        <span
          class="tw:block tw:text-center tw:text-base tw:font-medium tw:whitespace-pre-line"
          >{{ stage.display_name }}</span
        >
        <!-- Check arriba derecha si está seleccionada -->
        <span
          v-if="selectedStages.includes(stage.name)"
          class="tw:absolute tw:top-2 tw:right-2 tw:flex tw:items-center tw:justify-center tw:rounded-full tw:bg-white tw:p-1 tw:shadow"
        >
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="12" fill="#28C76F" />
            <path
              d="M7 13.5L10.5 17L17 10.5"
              stroke="white"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
            />
          </svg>
        </span>
      </button>
      <!-- Card para agregar custom stage -->
      <div
        class="tw:flex tw:h-[120px] tw:items-center tw:justify-center tw:rounded-xl tw:bg-white tw:p-4 tw:shadow"
      >
        <button
          type="button"
          class="tw:cursor-pointer tw:rounded-lg tw:border-0 tw:px-6 tw:py-2 tw:text-base tw:font-medium"
          style="background-color: #ff881129; color: #ff8811"
          @click="$emit('add-custom-stage')"
        >
          {{ $t("umbrella-campaign.step-scene.stages.add-custom-stage") }}
        </button>
      </div>
    </div>
  </div>
</template>
