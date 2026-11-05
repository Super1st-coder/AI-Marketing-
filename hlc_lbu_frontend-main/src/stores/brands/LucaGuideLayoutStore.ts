import NewBrandsApi, { BrandData } from "@/services/NewBrandsApi";
import LucaGuideOnboardingApi, {
  type LucaGuideMetaConnection,
  type LucaGuideNorthStarItem,
  type LucaGuideOnboardingState,
  type LucaGuideThresholdItem,
} from "@/services/guide/LucaGuideOnboardingApi";
import { getLucaGuideWorkspaceId } from "@/utils/guide/workspace";

type LucaGuideOnboardingProgress = {
  state: LucaGuideOnboardingState;
  meta: LucaGuideMetaConnection;
  northStar: LucaGuideNorthStarItem[];
  thresholds: LucaGuideThresholdItem[];
};

/**
 * Maps persisted onboarding resources to the step index to resume on
 * (also drives sidebar "X of 4" while incomplete).
 * welcome → meta → north star → thresholds.
 * When `has_completed`, resume on the final step (thresholds).
 */
function getCompletedOnboardingStepCount(
  progress: LucaGuideOnboardingProgress,
): number {
  if (progress.state.has_completed) {
    return 3;
  }

  // `show_tutorial: false` means the welcome/tutorial step was skipped or opted out.
  let completedSteps = progress.state.show_tutorial ? 0 : 1;

  if (progress.meta.status === "connected") {
    completedSteps = 1;
  }

  if (
    progress.meta.status === "connected" &&
    progress.meta.selected_ad_account_id
  ) {
    completedSteps = 2;
  }

  if (progress.northStar.length > 0) {
    completedSteps = 3;
  }

  return completedSteps;
}

async function getOnboardingProgress(): Promise<LucaGuideOnboardingProgress> {
  // Always read the real onboarding state from the backend. The backend resolves the brand's
  // workspace from the X-Brand-Id header (sent from the route on every request), so this must
  // NOT be gated on a locally-stored workspace id: after a logout/localStorage clear (or on a
  // new device) that id is gone, and short-circuiting to the default here wrongly forced an
  // already-onboarded brand back through onboarding (the login → onboarding loop).
  const [state, meta, northStar, thresholds] = await Promise.all([
    LucaGuideOnboardingApi.getState(),
    LucaGuideOnboardingApi.getMeta(),
    LucaGuideOnboardingApi.getNorthStar(),
    LucaGuideOnboardingApi.getThresholds(),
  ]);

  return { state, meta, northStar, thresholds };
}

export const useLucaGuideLayoutStore = defineStore(
  "LucaGuideLayoutStore",
  () => {
    const brand = ref<BrandData>();
    const meta = ref<LucaGuideMetaConnection>();
    const completedOnboardingSteps = ref(0);
    const totalOnboardingSteps = 4;
    const isOnboardingCompleted = ref(false);
    const showTutorial = useLocalStorage("luca-guide-show-tutorial", true);

    const currency = computed(() => meta.value?.currency ?? undefined);

    const refreshMeta = async () => {
      meta.value = await LucaGuideOnboardingApi.getMeta();
    };

    const initialize = async (brandId: number) => {
      const [brandResponse, progress] = await Promise.all([
        NewBrandsApi.getById(brandId),
        getOnboardingProgress(),
      ]);

      brand.value = brandResponse.data;
      meta.value = progress.meta;
      isOnboardingCompleted.value = progress.state.has_completed;

      if (
        getLucaGuideWorkspaceId(brandId) &&
        progress.state.show_tutorial !== showTutorial.value
      ) {
        try {
          await LucaGuideOnboardingApi.updateTutorial(showTutorial.value);
        } catch (error) {
          console.error("Failed to persist tutorial preference:", error);
        }
      }

      completedOnboardingSteps.value = getCompletedOnboardingStepCount({
        ...progress,
        state: {
          ...progress.state,
          show_tutorial: showTutorial.value,
        },
      });
    };

    return {
      brand,
      meta,
      currency,
      initialize,
      refreshMeta,
      completedOnboardingSteps,
      totalOnboardingSteps,
      isOnboardingCompleted,
      showTutorial,
    };
  },
);
