<script setup lang="ts">
import { toTypedSchema } from "@vee-validate/yup";
import { array, object, string } from "yup";
import { ProjectFormData } from "./ProjectForm.vue";
import ProjectsApi from "@/services/projects/ProjectsApi";

const { t } = useI18n();
const router = useRouter();
const brandId = useBrandId();

const { data, goBack } = useMultiStepFormContext<ProjectFormData>();

const showModal = ref(false);

const schema = computed(() =>
  toTypedSchema(
    object({
      language: string().required(t("forms.required-field")),
      facing_the_challenge: string().required(t("forms.required-field")).trim(),
      struggling_to_find_solution: string()
        .required(t("forms.required-field"))
        .trim(),
      discovering_new_possibilities: string()
        .required(t("forms.required-field"))
        .trim(),
      customer_goal: array()
        .of(string().required(t("forms.required-field")))
        .required(t("forms.required-field")),
      main_goal: string().required(t("forms.required-field")),
    }),
  ),
);

const { handleSubmit, isSubmitting, meta } = useFormWithErrorScrolling({
  keepValuesOnUnmount: true,
  validationSchema: schema,
  initialValues: {
    language: data.value.language,
    facing_the_challenge:
      data.value.summary_saved?.facing_the_challenge ??
      data.value.summary_generated?.facing_the_challenge,
    struggling_to_find_solution:
      data.value.summary_saved?.struggling_to_find_solution ??
      data.value.summary_generated?.struggling_to_find_solution,
    discovering_new_possibilities:
      data.value.summary_saved?.discovering_new_possibilities ??
      data.value.summary_generated?.discovering_new_possibilities,
    customer_goal: data.value.bperson?.customer_goal ?? undefined,
    main_goal: data.value.main_goal ?? data.value.bperson?.customer_goal?.[0],
  },
});

const disableSaveAlert = ref(false);

const handleConfirm = handleSubmit(async (values) => {
  // Update summary
  await ProjectsApi.saveSummary(brandId, data.value!.id, {
    summary_generated: data.value.summary_generated,
    summary_saved: {
      facing_the_challenge: values.facing_the_challenge,
      struggling_to_find_solution: values.struggling_to_find_solution,
      discovering_new_possibilities: values.discovering_new_possibilities,
    },
    main_goal: values.main_goal,
  });

  // Save data and go next
  showModal.value = false;
  disableSaveAlert.value = true;
  router.push({ name: "ProjectList" });
});

const onSubmit = handleSubmit(async () => {
  showModal.value = true;
});
</script>

<template>
  <FormStepLayout @submit.prevent="onSubmit" :disabled="isSubmitting">
    <ProductFormSummaryLockModal v-model="showModal" @confirm="handleConfirm" />

    <div class="tw:flex tw:flex-col tw:md:block">
      <PageTitle
        helpButton
        helpVideoUrl="https://www.youtube.com/watch?v=QuW10s5nejs"
      >
        {{ data.name }}
        <template #description>
          {{ $t("projects.summary.description") }}
        </template>
      </PageTitle>

      <i18n-t
        keypath="projects.summary.lets-build-a-story"
        tag="p"
        class="tw:mt-4 tw:text-[24px] tw:font-extrabold tw:text-snackbar"
      >
        <template #customer>
          <span class="tw:text-[#FF8811]">{{ data.bperson?.name }}</span>
        </template>
        <template #product>
          <span class="tw:text-[#FF8811]">{{ data.product?.name }}</span>
        </template>
        <template #goal>
          <YourHypothesisCardOption
            name="main_goal"
            :index="1"
            :options="data.bperson?.customer_goal ?? []"
          >
          </YourHypothesisCardOption>
        </template>
      </i18n-t>
    </div>

    <div class="tw:flex tw:flex-col tw:gap-4 tw:xl:flex-row tw:xl:items-start">
      <!-- Target Customer Card -->
      <CardBase
        class="tw:flex tw:w-full tw:shrink-0 tw:flex-col tw:gap-[18px] tw:p-5 tw:xl:basis-[260px]"
      >
        <div class="tw:flex tw:justify-between">
          <h2 class="tw:text-lg tw:font-extrabold">
            {{ data.bperson?.name }}
          </h2>
        </div>
        <Separator />
        <CardDynamicImage
          :src="data.bperson?.thumbnail_url ?? undefined"
          class="tw:aspect-square tw:w-full"
        />
        <p class="tw:line-clamp-5">
          {{ data.bperson?.bperson_story }}
        </p>
      </CardBase>

      <!-- Accordion Components -->
      <div class="tw:flex tw:grow tw:flex-col tw:gap-4">
        <AccordionList>
          <AccordionWithEditableText
            icon="tabler-flag"
            :title="$t('projects.summary.facing-the-challenge')"
            name="facing_the_challenge"
            editable
          />
          <AccordionWithEditableText
            :title="$t('projects.summary.struggling-to-find-a-solution')"
            icon="tabler-switch-3"
            name="struggling_to_find_solution"
            editable
          />
          <AccordionWithEditableText
            :title="$t('projects.summary.discovering-new-possibilities')"
            icon="tabler-bulb"
            name="discovering_new_possibilities"
            editable
          />
        </AccordionList>
      </div>

      <!-- Product Card -->
      <CardBase
        class="tw:flex tw:w-full tw:shrink-0 tw:flex-col tw:gap-[18px] tw:p-5 tw:xl:basis-[260px]"
      >
        <div class="tw:flex tw:justify-between">
          <h2 class="tw:text-lg tw:font-extrabold">
            {{ data.product?.name }}
          </h2>
        </div>
        <Separator />
        <CardDynamicImage
          :src="data.product?.thumbnail_url ?? undefined"
          class="tw:aspect-square tw:w-full"
        />
        <p class="tw:line-clamp-5">
          {{ data.product?.product_story }}
        </p>
      </CardBase>
    </div>

    <template #actions>
      <WizardCardActions>
        <ButtonGoBack @click="goBack" />
        <ButtonNext :isLoading="isSubmitting">
          {{ $t("global.save") }}
        </ButtonNext>
      </WizardCardActions>
    </template>

    <ModalFormSaveAlert :isDirty="meta.dirty" :disable="disableSaveAlert" />
  </FormStepLayout>
</template>
