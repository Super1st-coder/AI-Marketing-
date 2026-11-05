import ProjectsAPI, { ProjectData } from "@/services/legacy/ProjectsAPI";
import { RefinerAttributes } from "@/utils/type-declarations";
import { defineStore } from "pinia";

const adGenerationScreens = [
  "firstPhase",
  "firstPhaseReady",
  "secondPhasePresentation",
  "secondPhase",
  "secondPhaseReady",
  "thirdPhasePresentation",
  "thirdPhase",
] as const;
type AdGenerationScreens = (typeof adGenerationScreens)[number];

type StatusTest = {
  screen: AdGenerationScreens;
  step?: string;
  shouldBeUsed: (data: ProjectData) => boolean;
};

function areAttributesValid(attributes?: RefinerAttributes | string) {
  if (
    typeof attributes === "string" ||
    (typeof attributes === "object" && Object.keys(attributes).length === 0)
  ) {
    return false;
  }

  return !!attributes;
}

const statusTests: StatusTest[] = [
  //#region First phase

  {
    screen: "firstPhase",
    step: "hypothesis",
    shouldBeUsed: (data) => data.marketing_hypothesis == undefined,
  },
  {
    screen: "firstPhase",
    step: "yourProduct",
    shouldBeUsed: (data) =>
      data.brand_name === undefined ||
      data.product_name === undefined ||
      data.product_attributes_generated === undefined,
  },
  {
    screen: "firstPhase",
    step: "yourProductRefinement",
    shouldBeUsed: (data) => !areAttributesValid(data.product_attributes_saved),
  },
  {
    screen: "firstPhase",
    step: "yourTarget",
    shouldBeUsed: (data) =>
      data.target_customer_description === undefined ||
      data.target_customer_attributes_generated === undefined,
  },
  {
    screen: "firstPhase",
    step: "yourTargetRefinement",
    shouldBeUsed: (data) =>
      !areAttributesValid(data.target_customer_attributes_saved),
  },
  {
    screen: "firstPhase",
    step: "element",
    shouldBeUsed: (data) =>
      data.hypothesis_element_description === undefined ||
      data.hypothesis_element_attributes_generated === undefined,
  },
  {
    screen: "firstPhase",
    step: "elementRefinement",
    shouldBeUsed: (data) =>
      !areAttributesValid(data.hypothesis_element_attributes_saved),
  },
  {
    screen: "firstPhase",
    step: "goal",
    shouldBeUsed: (data) =>
      data.goal_description === undefined ||
      data.goal_attributes_generated === undefined,
  },
  {
    screen: "firstPhase",
    step: "goalRefinement",
    shouldBeUsed: (data) => !areAttributesValid(data.goal_attributes_saved),
  },
  {
    screen: "firstPhase",
    step: "buyerChallenge",
    shouldBeUsed: (data) =>
      data.advantages_description === undefined ||
      data.advantages_attributes_generated === undefined,
  },
  {
    screen: "firstPhase",
    step: "buyerChallengeRefinement",
    shouldBeUsed: (data) =>
      !areAttributesValid(data.advantages_attributes_saved),
  },

  //#endregion

  //#region  Second phase
  {
    screen: "firstPhaseReady",
    shouldBeUsed: (data) => data.buyer_persons === undefined,
  },
  {
    screen: "secondPhasePresentation",
    shouldBeUsed: () => false,
  },
  {
    screen: "secondPhase",
    step: "targetBuyer",
    shouldBeUsed: (data) =>
      data.preferred_buyer_person === undefined ||
      data.selected_buyer_person_image_prompt === undefined ||
      data.products === undefined,
  },
  {
    screen: "secondPhase",
    step: "product",
    shouldBeUsed: (data) => data.preferred_product === undefined,
  },
  {
    screen: "secondPhase",
    step: "yourHypothesis",
    shouldBeUsed: (data) =>
      data.hypothesis_builder_preferred_option === undefined,
  },

  //#endregion

  //#region Third phase

  {
    screen: "secondPhaseReady",
    shouldBeUsed: (data) =>
      data.audience === undefined ||
      // Due to a bug (that now has been resolved) in a campaign endpoint, the audience field
      // was being replaced by campaigns and some projects were left with that, so here we check
      // if the audience has the correct format
      !!data.audience.find((audience) => !audience.Demographics),
  },
  {
    screen: "thirdPhasePresentation",
    shouldBeUsed: () => false,
  },
  {
    screen: "thirdPhase",
    step: "audience",
    shouldBeUsed: (data) => data.preferred_audience === undefined,
  },
  {
    screen: "thirdPhase",
    step: "creativeConceptIntro",
    shouldBeUsed: (data) =>
      data.creative_concept_description === undefined ||
      data.creative_concept_attributes_generated === undefined,
  },
  {
    screen: "thirdPhase",
    step: "creativeConceptDetails",
    shouldBeUsed: () => false,
  },
  {
    screen: "thirdPhase",
    step: "creativeConceptRefinement",
    shouldBeUsed: (data) =>
      !areAttributesValid(data.creative_concept_attributes_saved) ||
      data.creative_concepts === undefined,
  },
  {
    screen: "thirdPhase",
    step: "creativeConcept",
    shouldBeUsed: (data) =>
      data.preferred_creative_concept === undefined ||
      data.campaigns === undefined,
  },
  {
    screen: "thirdPhase",
    step: "campaignConcept",
    shouldBeUsed: (data) =>
      data.preferred_campaign === undefined ||
      data.campaign_image_prompts === undefined ||
      data.selected_campaign_image_prompt === undefined,
  },
  {
    screen: "thirdPhase",
    step: "funnelBuilderIntro1",
    shouldBeUsed: (_data) => false,
  },
  {
    screen: "thirdPhase",
    step: "funnelBuilderIntro2",
    shouldBeUsed: (_data) => false,
  },
  {
    screen: "thirdPhase",
    step: "chooseFunnelFramework",
    shouldBeUsed: (_data) => true,
  },

  //#endregion
];

export const useAdGenerationStore = defineStore("AdGenerationStore", () => {
  const currentScreen = ref<AdGenerationScreens>(adGenerationScreens[0]);

  const firstPhaseStore = useAdGenerationFirstPhaseStore();
  const secondPhaseStore = useAdGenerationSecondPhaseStore();
  const thirdPhaseStore = useAdGenerationThirdPhaseStore();

  const getStore = (screen: AdGenerationScreens) => {
    if (screen === "firstPhase") {
      return firstPhaseStore;
    }

    if (screen === "secondPhase") {
      return secondPhaseStore;
    }

    if (screen === "thirdPhase") {
      return thirdPhaseStore;
    }

    return undefined;
  };

  const currentScreenIndex = computed(() =>
    adGenerationScreens.findIndex((item) => item === currentScreen.value),
  );

  const previousScreen = computed(() => {
    const currentIndex = currentScreenIndex.value;
    if (currentIndex > 0) {
      return adGenerationScreens[currentIndex - 1];
    }

    return null;
  });

  const nextScreen = computed(() => {
    const currentIndex = currentScreenIndex.value;
    if (currentIndex < adGenerationScreens.length) {
      return adGenerationScreens[currentIndex + 1];
    }

    return null;
  });

  const goToNextScreen = () => {
    if (nextScreen.value) {
      currentScreen.value = nextScreen.value;
      window.scrollTo(0, 0);
    }
  };

  const goToPreviousScreen = () => {
    if (previousScreen.value) {
      currentScreen.value = previousScreen.value;
      window.scrollTo(0, 0);

      const store = getStore(currentScreen.value);
      store?.goToLastStage();
    }
  };

  const projectId = ref(NaN);
  const data = ref<ProjectData>({
    id: NaN,
    name: "Undefined",
    createdAt: "",
    updatedAt: "",
    publishedAt: "",
  });

  const setData = (_projectId: number, _data: ProjectData) => {
    projectId.value = _projectId;
    data.value = _data;

    //#region Target screen or step from back-end

    // Here we'll inspect the project status and see if it's corresponds to an existing
    // screen or an existing step in some of the screens.

    let targetScreen: AdGenerationScreens | undefined = undefined;
    let targetStep: string | undefined = undefined;

    if (_data.status) {
      const screen = _data.status as AdGenerationScreens;

      if (adGenerationScreens.includes(screen)) {
        // A screen was found and we'll use it
        targetScreen = screen;
      } else {
        // A screen was not found, let's now see if the status is an existing step
        const step = _data.status;
        if (
          firstPhaseStore.flattenSteps.includes(step) ||
          secondPhaseStore.flattenSteps.includes(step) ||
          thirdPhaseStore.flattenSteps.includes(step)
        ) {
          targetStep = step;
        }
      }
    }

    //#endregion

    // Here we'll finally set the screen and step but we'll also take into consideration
    // the previously found screen and step found in the project status
    for (const test of statusTests) {
      if (
        test.shouldBeUsed(_data) ||
        (targetScreen != undefined && targetScreen === test.screen) ||
        (targetStep != undefined && targetStep === test.step)
      ) {
        currentScreen.value = test.screen;

        const store = getStore(test.screen);
        if (store && test.step) {
          store.currentStep = test.step;
        }

        break;
      }
    }
  };

  const goNext = async () => {
    const store = getStore(currentScreen.value);

    if (store && store.nextStep) {
      // Save the next step as the status
      await ProjectsAPI.setStatus(projectId.value, store.nextStep);

      // Go to the next step in the same screen
      store.goToNextStep();
      return;
    }

    if (nextScreen.value) {
      const nextScreenStore = getStore(nextScreen.value);

      // Save status
      if (nextScreenStore) {
        // Save the first step of the next screen as the status
        await ProjectsAPI.setStatus(
          projectId.value,
          nextScreenStore.stages[0].steps[0],
        );
      } else {
        // Save the screen itself as the status
        await ProjectsAPI.setStatus(projectId.value, nextScreen.value);
      }

      // Go to the next screen
      goToNextScreen();
    }
  };

  const goBack = () => {
    const store = getStore(currentScreen.value);

    if (store && store.previousStep) {
      store.goToPreviousStep();
      return;
    }

    goToPreviousScreen();
  };

  return {
    currentScreen,
    projectId,
    data,
    setData,
    goNext,
    goBack,
  };
});
