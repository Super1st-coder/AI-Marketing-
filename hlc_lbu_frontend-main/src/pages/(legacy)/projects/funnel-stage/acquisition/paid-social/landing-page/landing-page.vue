<script lang="ts">
export const landingPageSchema = object().shape({
  heroTitle: string().required(),
  heroSubtitle: string().required(),
  heroParagraph: string().required(),
  heroCta: string().required(),
  heroImage: imageGenerationSchema,
  formTitle: string().required(),
  formSubtitle: string().required(),
  formCta: string().required(),
  valuePropositionTitle: string().required(),
  valuePropositionSubtitle: string().required(),
  valuePropositionParagraph: string().required(),
  valuePropositionCta: string().required(),
  howItWorksTitle: string().required(),
  howItWorksSubtitle: string().required(),
  howItWorksSteps: array().of(string().required()).required(),
  howItWorksParagraph: string().required(),
  howItWorksCta: string().required(),
  trustTitle: string().required(),
  trustParagraph: string().required(),
  trustTestimonials: array().of(string().required()).required(),
  finalPushTitle: string().required(),
  finalPushSubtitle: string().required(),
  finalPushCta: string().required(),
});
// .test("need-image", "You have to generate the hero image.", (value) => {
//   return value.heroImage?.generatedImage;
// });

export type LandingPage = InferType<typeof landingPageSchema>;
</script>

<script lang="ts" setup>
import { array, InferType, object, string } from "yup";
import { toTypedSchema } from "@vee-validate/yup";
import { useRoute, useRouter } from "vue-router";
import { imageGenerationSchema } from "@/components/images/image-generation/ImageGenerator.vue";
import LandingPageHeroAPI from "@/services/legacy/LandingPageHeroAPI";
import LandingPageTestimonialAPI, {
  getTestimonialReviewWithUser,
} from "@/services/legacy/LandingPageTestimonialAPI";
import LandingPageHowWeDoAPI from "@/services/legacy/LandingPageHowWeDoAPI";
import LandingPageBenefitsAPI from "@/services/legacy/LandingPageBenefitsAPI";
import LandingPageCompetiAdvantagesAPI from "@/services/legacy/LandingPageCompetiAdvantagesAPI";
//import LandingPageBenefitsAPI from "@/services/LandingPageBenefitsAPI";
//import LandingPageCompetiAdvantagesAPI from "@/services/LandingPageCompetiAdvantagesAPI";

const router = useRouter();
const route = useRoute();

const projectId = parseInt(route.params.id as string);

// Fetch the hero
const heroData = await LandingPageHeroAPI.getConfiguredOrGenerate(
  projectId,
  "N",
);
// Fetch testimonials
const testimonialData = await LandingPageTestimonialAPI.getConfiguredOrGenerate(
  projectId,
  "N",
);
const testimonialReview = getTestimonialReviewWithUser(
  testimonialData.Testimonial_1,
);
// Fetch howoWeDo
const howoWeDo = await LandingPageHowWeDoAPI.getConfiguredOrGenerate(
  projectId,
  "N",
);

//Fetch Benefits
const benefits = await LandingPageBenefitsAPI.getConfiguredOrGenerate(
  projectId,
  "N",
);

// Fetch Competitive Advantages
const CompetitiveAdvantages =
  await LandingPageCompetiAdvantagesAPI.getConfiguredOrGenerate(projectId, "N");

//#region Form

const { handleSubmit } = useFormWithErrorScrolling({
  initialValues: {
    // Hero

    heroTitle: heroData.Header[0],
    heroSubtitle: heroData.SubHeader[0],
    heroParagraph: heroData.Paragraph[0],
    heroCta: heroData.CTA_Button_Text[0],
    // Form
    formTitle: CompetitiveAdvantages.Action_Paragraph[0] ?? "", //"Lorem ipsum dolor sit amet, consecte tur adipiscing elit",
    formSubtitle:
      "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.",
    formCta: CompetitiveAdvantages.CTA_Button_Text_2[0] ?? "", //"GET YOUR PLATA CARD",
    // Value proposition
    valuePropositionTitle: CompetitiveAdvantages.Header[0] ?? "",
    ///"Get More from Every Purchase with Plata Card",
    valuePropositionSubtitle: CompetitiveAdvantages.SubHeader[0] ?? "",
    //"Credit card with high limits, minimal fees, ideal for maximizing rewards while shopping or traveling.",
    valuePropositionParagraph: CompetitiveAdvantages.Paragraph[0] ?? "",
    //"Take advantage of unique benefits with our card, such as high credit limits and cashback.\n\nReceive constant rewards when making your everyday purchases and maximize your shopping experience.",
    valuePropositionCta: CompetitiveAdvantages.CTA_Button_Text_1[0] ?? "", //"GET YOUR PLATA CARD",
    // How it works
    howItWorksTitle: howoWeDo.Header[0] ?? "",
    //  "How the Plata Card Works",
    howItWorksSubtitle: howoWeDo.Header[1] ?? "",
    //"Enjoy premium rewards in just three easy steps.\n\nFollow the process and maximize your benefits without complications.",
    howItWorksSteps: howoWeDo.Step_Process_1.Paragraph,
    /* [
      "Apply online using our quick and easy form. Complete your application in just a few minutes.",
      "Get instant approval and start using your card in minutes. Enjoy instant benefits.",
      "Use your card for every purchase and earn 5% cashback on all your transactions.",
    ],*/
    howItWorksParagraph: howoWeDo.Step_Process_1.Subheader[0] ?? "",
    //"Aprovecha la comodidad de un proceso rápido y sin estrés desde cualquier dispositivo.",
    howItWorksCta: howoWeDo.CTA_Button_Text[0] ?? "", //"GET YOUR PLATA CARD",
    // Trust
    trustTitle: testimonialData.Header[0] ?? "",
    trustParagraph: testimonialData.Header[1] ?? "", //"Customers love the flexible spending limits and incredible cashback rewards!",
    trustTestimonials: testimonialReview,
    finalPushTitle: benefits.Header[0] ?? "", //  "Don’t Miss Out on Exclusive Plata Card Rewards",
    finalPushSubtitle: benefits.Paragraph[0] ?? "",
    //"Apply now to enjoy low-interest rates and get 5% cashback on every purchase!",
    finalPushCta: benefits.CTA_Button_Text[0] ?? "", //"GET YOUR PLATA CARD TODAY",
  },
  validationSchema: toTypedSchema(landingPageSchema),
});
const isLoading = ref(false);
// handleSubmit section
const saveTheHeroData = async (values: any) => {
  try {
    await LandingPageHeroAPI.configure(
      projectId,
      {
        Header: [values.heroTitle],
        SubHeader: [values.heroSubtitle],
        Paragraph: [values.heroParagraph],
        CTA_Button_Text: [values.heroCta],
      },
      "N",
    );
  } catch (error) {
    console.log(error);
  }
};

const saveHowWeDoData = async (values: any) => {
  try {
    await LandingPageHowWeDoAPI.configure(
      projectId,
      {
        Header: [values.howItWorksTitle, values.howItWorksSubtitle],
        Step_Process_1: {
          Paragraph: [values.howItWorksParagraph],
          Subheader: values.howItWorksSteps,
        },
        Step_Process_2: {
          Paragraph: howoWeDo.Step_Process_2.Paragraph,
          Subheader: howoWeDo.Step_Process_2.Subheader,
        },
        Step_Process_3: {
          Paragraph: howoWeDo.Step_Process_3.Paragraph,
          Subheader: howoWeDo.Step_Process_3.Subheader,
        },
        CTA_Button_Text: [values.howItWorksCta],
        Action_Paragraph: howoWeDo.Action_Paragraph,
      },
      "N",
    );
  } catch (error) {
    console.log(error);
  }
};

const saveTestimonialData = async (values: any) => {
  try {
    await LandingPageTestimonialAPI.configure(
      projectId,
      {
        Header: [values.trustTitle, values.trustParagraph],
        Testimonial_1: {
          Review: values.trustTestimonials,
          User_Name: [],
        },
        Testimonial_2: {
          Review: testimonialData.Testimonial_2.Review,
          User_Name: testimonialData.Testimonial_2.User_Name,
        },
        Testimonial_3: {
          Review: testimonialData.Testimonial_3.Review,
          User_Name: testimonialData.Testimonial_3.User_Name,
        },
      },
      "N",
    );
  } catch (error) {}
};

const saveBenefitsData = async (values: any) => {
  try {
    await LandingPageBenefitsAPI.configure(
      projectId,
      {
        Image: {
          Alt_text: benefits.Image.Alt_text,
          Description: benefits.Image.Description,
        },
        Header: [values.finalPushTitle],
        Paragraph: [values.finalPushSubtitle],
        CTA_Button_Text: [values.finalPushCta],
        Action_Paragraph: benefits.Action_Paragraph,
      },
      "N",
    );
  } catch (error) {
    console.log(error);
  }
};

const saveCompetitiveAdvantagesData = async (values: any) => {
  try {
    await LandingPageCompetiAdvantagesAPI.configure(
      projectId,
      {
        Header: [values.valuePropositionTitle],
        SubHeader: [values.valuePropositionSubtitle],
        Paragraph: [values.valuePropositionParagraph],
        CTA_Button_Text_1: [values.valuePropositionCta],
        CTA_Button_Text_2: [values.formCta],
        Action_Paragraph: [values.formTitle],
      },
      "N",
    );
  } catch (error) {
    console.log(error);
  }
};

const onSubmit = handleSubmit(async (values) => {
  isLoading.value = true;
  console.log(values);

  //**** */
  Promise.all([
    saveTheHeroData(values),
    saveHowWeDoData(values),
    saveTestimonialData(values),
    saveBenefitsData(values),
    saveCompetitiveAdvantagesData(values),
  ])
    .then((results) => {
      console.log(results);
      isLoading.value = false;
      router.push({ name: "PaidSocial" });
    })
    .catch((error) => {
      console.error("Error al ejecutar las promesas :", error);
      isLoading.value = false;
    });
  //*** */
});
//#endregion
</script>

<template>
  <WizardCard paddingY="lg">
    <form
      @submit="onSubmit"
      class="tw:flex tw:flex-col tw:gap-[40px] tw:lg:gap-[60px]"
    >
      <div>
        <WizardCardTitle>
          Landing page builder
          <template #button>
            <HelpButton> Help info </HelpButton>
          </template>
        </WizardCardTitle>

        <WizardCardParagraph>
          We created an outline of a landing page to support your ad copies.
          Feel free to edit copy and generate images to make it compelling.
        </WizardCardParagraph>
      </div>

      <div>
        <LandingPageHeader />
        <LandingPageHero />
        <LandingPageForm />
        <LandingPageValueProposition />
        <LandingPageHowItWorks />
        <LandingPageTrust />
        <LandingPageFinalPush />
      </div>

      <WizardCardActions>
        <WizardButtonGoBack :to="{ name: 'PaidSocial' }" />

        <WizardButtonNext :isLoading="isLoading">
          SAVE LANDING PAGE
        </WizardButtonNext>
      </WizardCardActions>
    </form>
  </WizardCard>
</template>
