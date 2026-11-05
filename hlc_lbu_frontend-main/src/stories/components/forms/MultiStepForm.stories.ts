import type { Meta, StoryObj } from "@storybook/vue3-vite";
import MultiStepForm from "@/components/forms/multi-step/MultiStepForm.vue";
import SidebarTitle from "@/components/navigation/SidebarTitle.vue";
import FormStepLayout from "@/components/forms/multi-step/FormStepLayout.vue";
import FormStep from "@/components/forms/multi-step/FormStep.vue";
import PageTitle from "@/components/texts/headings/PageTitle.vue";
import FieldText from "@/components/forms/base/FieldText.vue";
import FieldsContainer from "@/components/forms/base/FieldsContainer.vue";
import FieldLanguage from "@/components/forms/FieldLanguage.vue";
import WizardCardActions from "@/components/legacy/wizard-form/WizardCardActions.vue";
import ButtonGoBack from "@/components/buttons/ButtonGoBack.vue";
import ButtonNext from "@/components/buttons/ButtonNext.vue";
import { toTypedSchema } from "@vee-validate/yup";
import { object, string } from "yup";

const meta: Meta<typeof MultiStepForm> = {
  title: "Components/Forms/MultiStepForm",
  tags: ["autodocs"],
  parameters: {
    controls: {
      include: [],
    },
  },
  argTypes: {},
  args: {},
  render: (args) => ({
    components: {
      MultiStepForm,
      FormStepLayout,
      FormStep,
      SidebarTitle,
      PageTitle,
      FieldsContainer,
      FieldText,
      FieldLanguage,
      ButtonGoBack,
      ButtonNext,
      WizardCardActions,
    },
    setup() {
      const { t } = useI18n();

      const steps = computed<FormStep[]>(() => [
        {
          name: "step1",
          label: "Step 1",
          icon: "tabler:id",
        },
        {
          name: "step2",
          label: "Step 2",
          icon: "tabler-eye",
        },
      ]);

      const { goNext, goBack } = useMultiStepForm(steps);

      const schema = computed(() =>
        toTypedSchema(
          object().shape({
            language: string().required(t("forms.required-field")),
            name: string().required(t("forms.required-field")),
            website: string().url().required(t("forms.required-field")),
          }),
        ),
      );

      const { handleSubmit, isSubmitting } = useFormWithErrorScrolling({
        validationSchema: schema,
      });

      const onSubmit = handleSubmit(async (values) => {
        console.log(values);
        await sleep(1000);
        goNext();
      });

      return { args, onSubmit, goBack, isSubmitting };
    },
    template: `
      <MultiStepForm freeMovement>
        <template #sidebarHeader>
          <SidebarTitle variant="secondary" size="md"> Form </SidebarTitle>
        </template>

        <FormStep name="step1">
          <FormStepLayout @submit.prevent="onSubmit">
            <!-- TODO: add help video URL later -->
            <PageTitle>
              {{ $t("brands.identity.title") }}
            </PageTitle>

            <FieldsContainer class="tw:grow">
              <FieldLanguage
                name="language"
                :label="$t('brands.identity.language.label')"
                :placeholder="$t('brands.identity.language.placeholder')"
                required
              />

              <FieldText
                name="name"
                :label="$t('brands.identity.name.label')"
                :placeholder="$t('brands.identity.name.placeholder')"
                required
              />

              <FieldText
                name="website"
                :label="$t('brands.identity.website.label')"
                :placeholder="$t('brands.identity.website.placeholder')"
                required
              />
            </FieldsContainer>

            <template #actions>
              <WizardCardActions>
                <ButtonGoBack @click="goBack" />
                <ButtonNext :isLoading="isSubmitting" />
              </WizardCardActions>
            </template>
          </FormStepLayout>
        </FormStep>

        <FormStep name="step2">
          <FormStepLayout>
            <!-- TODO: add help video URL later -->
            <PageTitle>
              Lorem Ipsum
            </PageTitle>

            <template #actions>
              <WizardCardActions>
                <ButtonGoBack @click="goBack" />
              </WizardCardActions>
            </template>
          </FormStepLayout>
        </FormStep>
      </MultiStepForm>`,
  }),
};

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  args: {},
};
