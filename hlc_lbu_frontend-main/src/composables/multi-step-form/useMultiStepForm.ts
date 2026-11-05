export interface FormStep<T = any> {
  name?: string;
  label?: string;
  invisible?: boolean;
  icon?: string;
  children?: FormStep[];
  requires?: RoutePermissionMeta[];
  next?: (data: T) => string | null;

  disabled?: MaybeRefOrGetter<boolean> | ((data: T) => boolean);
  hasAlert?: MaybeRefOrGetter<boolean> | ((data: T) => boolean);
  hasTooltip?: MaybeRefOrGetter<boolean> | ((data: T) => boolean);
}

type GoToStepOptions = { isDirty?: boolean };

export type MultiStepFormInjectionData<T> = {
  steps: Ref<FormStep<T>[]>;
  flattenSteps: ComputedRef<(FormStep<T> & { parent?: FormStep<T> })[]>;
  getFlatIndexOfStep: (step: FormStep<T>) => number;
  currentFlatStepIndex: Ref<number>;
  lastCompletedFlatStepIndex: Ref<number>;
  currentFlatStep: ComputedRef<FormStep<T>>;
  goToStep: (index: number, options?: GoToStepOptions) => void;
  goBack: () => void;
  goNext: (options?: GoToStepOptions) => void;
  data: Ref<T>;
  saveData: (newData: Partial<T>) => void;
  getIsStageDirty: (stage: string) => boolean;
  setDirtyStage: (stage: string, value: boolean) => void;
  previousStep: Ref<FormStep<T> | undefined>;
  freeMovement?: MaybeRefOrGetter<boolean>;

  handleLinkClick: (step: FormStep<T>) => void;
  getIsLinkCompleted: (step: FormStep<T>) => boolean;
  getIsLinkSelected: (step: FormStep<T>) => boolean;
  getIsLinkDisabled: (step: FormStep<T>) => boolean;
  getHasLinkAlert: (step: FormStep<T>) => boolean;
  getHasLinkTooltip: (step: FormStep<T>) => boolean;
};

export const multiStepFormInjectionKey = Symbol() as InjectionKey<
  MultiStepFormInjectionData<any>
>;

export function useMultiStepForm<T>(
  steps: MaybeRefOrGetter<FormStep<T>[]>,
  options: {
    blockForwardNavigation?: MaybeRefOrGetter<boolean>;
    initialStep?: MaybeRefOrGetter<number | string>;
    initialData?: MaybeRefOrGetter<T>;
    id?: (data: T | undefined) => string;
    filterStep?: (step: FormStep<T>) => boolean;
    freeMovement?: MaybeRefOrGetter<boolean>;
    useLocalStorage?: MaybeRefOrGetter<boolean>;
    /**
     * External furthest reachable step index (e.g. API/Pinia progress).
     * When set, stepper enablement uses this instead of localStorage.
     */
    lastCompletedFlatStepIndex?: MaybeRefOrGetter<number>;
    /**
     * Name of the child to open when a step with children is clicked in the
     * sidebar. Return `undefined` to use the default behavior.
     */
    getStepEntry?: (step: FormStep<T>) => string | undefined;
  } = {},
) {
  const tracksFurthestStep = () =>
    options.lastCompletedFlatStepIndex !== undefined ||
    toValue(options.useLocalStorage);

  const stepsRef = computed(() => {
    const raw = toValue(steps);

    if (!options.filterStep) return raw;

    return raw
      .map((step) => {
        if (step.children) {
          step.children = step.children.filter(options.filterStep!);
        }
        return step;
      })
      .filter(options.filterStep);
  });

  const flattenSteps = computed(() => {
    const flatten: (FormStep<T> & {
      parent?: FormStep<T>;
    })[] = [];

    stepsRef.value.forEach((fullStep) => {
      if (fullStep.children && fullStep.children.length > 0) {
        fullStep.children?.forEach((child) =>
          flatten.push({ ...child, parent: fullStep }),
        );
      } else {
        flatten.push(fullStep);
      }
    });

    return flatten;
  });

  const getFlatIndexOfStep = (step: FormStep<T>) => {
    // If the step has children, we want to get the first child
    if (step.children && step.children.length > 0) {
      step = step.children[0];
    }

    const flattenStep =
      flattenSteps.value.find(
        (flattenStep) => flattenStep.name === step.name,
      ) ?? flattenSteps.value[0];

    return flattenSteps.value.indexOf(flattenStep);
  };

  const formId = computed(() => {
    const id = options?.id?.(data.value);

    return id ?? "";
  });

  // Determine the initial step based on the options, but fallback to the first step
  const optionsInitialStep = toValue(options?.initialStep);
  let initialStepIndex = 0;
  if (optionsInitialStep) {
    if (typeof optionsInitialStep === "string") {
      // The initial step was given as a name
      const foundStep =
        flattenSteps.value.find((step) => step.name == optionsInitialStep) ||
        stepsRef.value.find((step) => step.name == optionsInitialStep);

      if (foundStep) {
        if (foundStep.children && foundStep.children.length > 0) {
          initialStepIndex = getFlatIndexOfStep(foundStep.children[0]);
        } else {
          initialStepIndex = flattenSteps.value.indexOf(foundStep);
        }
      }
    } else {
      // The initial step was given as an index
      initialStepIndex = optionsInitialStep;
    }
  }

  const currentFlatStepIndex = ref<number>(initialStepIndex);
  const currentFlatStep = computed(
    () => flattenSteps.value[currentFlatStepIndex.value],
  );
  const data = ref(toValue(options?.initialData));

  const previousStep = ref<FormStep<T>>();

  const lastFlatIndexStorage = useLocalStorage<Record<string, number>>(
    "lastFlatIndices",
    {},
  );

  const firstAllowedStepIndex = computed(() => {
    return flattenSteps.value.length > 0 ? 0 : -1;
  });

  const lastCompletedFlatStepIndex = computed<number>({
    get: () => {
      if (options.lastCompletedFlatStepIndex !== undefined) {
        return toValue(options.lastCompletedFlatStepIndex);
      }

      if (!toValue(options.useLocalStorage)) {
        return 0;
      }

      if (
        options.blockForwardNavigation &&
        toValue(options.blockForwardNavigation)
      ) {
        return currentFlatStepIndex.value;
      }

      let value: number | undefined =
        lastFlatIndexStorage.value?.[formId.value];

      if (value === undefined) {
        value = currentFlatStepIndex.value;
        lastFlatIndexStorage.value[formId.value] = currentFlatStepIndex.value;
      }

      if (value < currentFlatStepIndex.value) {
        value = currentFlatStepIndex.value;
        lastFlatIndexStorage.value[formId.value] = currentFlatStepIndex.value;
      }

      return value;
    },
    set: (value) => {
      // External sources own their updates; localStorage is the only writable sink.
      if (
        options.lastCompletedFlatStepIndex !== undefined ||
        !toValue(options.useLocalStorage)
      ) {
        return;
      }

      lastFlatIndexStorage.value[formId.value] = value;
    },
  });

  watch(
    () => currentFlatStep.value,
    (step) => {
      if (!step) {
        const firstIndex = firstAllowedStepIndex.value;
        if (firstIndex >= 0) {
          currentFlatStepIndex.value = firstIndex;
        }
      }
    },
    { immediate: true },
  );

  const goToStep = (
    index: number,
    _options: { isDirty?: boolean } = { isDirty: true },
  ) => {
    if (tracksFurthestStep()) {
      // Increment the last index if we are going forward
      if (index > lastCompletedFlatStepIndex.value) {
        lastCompletedFlatStepIndex.value = index;
      }

      // Reset the last index if we are going forward and the step is dirty
      if (index > currentFlatStepIndex.value && _options.isDirty) {
        lastCompletedFlatStepIndex.value = index;
      }
    }

    previousStep.value = flattenSteps.value[currentFlatStepIndex.value];
    currentFlatStepIndex.value = index;
    window.scrollTo(0, 0);
  };

  const goNext = (options: GoToStepOptions = { isDirty: true }) => {
    const current = currentFlatStep.value;

    if (current.next) {
      const nextName = current.next(data.value);

      if (nextName) {
        const targetIndex = getFlatIndexOfStep({ name: nextName });
        return goToStep(targetIndex, options);
      }
    }

    goToStep(currentFlatStepIndex.value + 1, options);
  };

  const goBack = () => {
    goToStep(currentFlatStepIndex.value - 1);
  };

  const saveData = (newData: Partial<T>) => {
    data.value = { ...data.value, ...newData };
  };

  const dirtyStagesLocalStorage = useLocalStorage<
    Record<string, Record<string, boolean>>
  >("dirtyStages", {});

  const getIsStageDirty = (stage: string): boolean => {
    return dirtyStagesLocalStorage.value?.[formId.value]?.[stage] ?? false;
  };

  const setDirtyStage = (stage: string, value: boolean) => {
    // Add ID if it does not exists
    if (!(formId.value in dirtyStagesLocalStorage.value)) {
      dirtyStagesLocalStorage.value[formId.value] = {};
    }

    dirtyStagesLocalStorage.value[formId.value][stage] = value;
  };

  // Sidebar logic
  const handleLinkClick = async (step: FormStep<T>) => {
    // Save locking
    if ((await useSaveLockingStore().execute()) === "cancel") return;

    if (step.children && step.children.length > 0) {
      // The step has children
      const entryName = options.getStepEntry?.(step);

      if (entryName) {
        // The form decides which child to open
        goToStep(getFlatIndexOfStep({ name: entryName }), {
          isDirty: false,
        });
      } else if (tracksFurthestStep()) {
        // Go to the last child
        const lastChild = step.children[step.children.length - 1];
        const lastChildIndex = getFlatIndexOfStep(lastChild);

        if (lastCompletedFlatStepIndex.value >= lastChildIndex) {
          // If the last child has been completed, go to it
          goToStep(lastChildIndex, {
            isDirty: false,
          });
        } else {
          // Otherwise, go to the last completed step
          goToStep(lastCompletedFlatStepIndex.value, {
            isDirty: false,
          });
        }
      } else {
        // Go to the first child
        const firstChild = step.children[0];
        const firstChildIndex = getFlatIndexOfStep(firstChild);
        goToStep(firstChildIndex, {
          isDirty: false,
        });
      }
    } else {
      // The step has no children, go directly to it
      let targetIndex = getFlatIndexOfStep(step);
      goToStep(targetIndex, { isDirty: false });
    }
  };

  const getIsLinkCompleted = (step: FormStep<T>): boolean => {
    if (toValue(options.freeMovement)) {
      return false;
    }

    if (step.children && step.children.length > 0) {
      const lastChild = step.children[step.children.length - 1];
      const lastChildIndex = getFlatIndexOfStep(lastChild);

      return currentFlatStepIndex.value > lastChildIndex;
    } else {
      return getFlatIndexOfStep(step) < currentFlatStepIndex.value;
    }
  };

  const getIsLinkSelected = (step: FormStep) => {
    if (currentFlatStep.value.name === step.name) {
      return true;
    }

    return (
      step.children?.find(
        (_step) => currentFlatStep.value.name === _step.name,
      ) !== undefined
    );
  };

  const getIsLinkDisabled = (step: FormStep<T>) => {
    const stepIndex = getFlatIndexOfStep(step);

    // All buttons are enabled when free movement is allowed
    if (toValue(options.freeMovement)) {
      return false;
    }

    if (step.disabled !== undefined) {
      const value = toValue(step.disabled);

      if (typeof value === "function") {
        return value(data.value);
      }

      return value;
    }

    if (tracksFurthestStep()) {
      // Disable the step button if the step has not been completed yet
      const isDisabled = stepIndex > lastCompletedFlatStepIndex.value;
      return isDisabled;
    }

    return stepIndex > currentFlatStepIndex.value;
  };

  const getHasLinkAlert = (step: FormStep<T>) => {
    if (step.hasAlert !== undefined) {
      const value = toValue(step.hasAlert);

      if (typeof value === "function") {
        return value(data.value);
      }

      return value;
    }

    return false;
  };

  const getHasLinkTooltip = (step: FormStep<T>) => {
    if (step.hasTooltip !== undefined) {
      const value = toValue(step.hasTooltip);

      if (typeof value === "function") {
        return value(data.value);
      }

      return value;
    }

    return false;
  };

  provide(multiStepFormInjectionKey, {
    steps: stepsRef,
    flattenSteps,
    getFlatIndexOfStep,
    currentFlatStepIndex,
    lastCompletedFlatStepIndex,
    currentFlatStep,
    goToStep,
    goBack,
    goNext,
    data,
    saveData,
    getIsStageDirty,
    setDirtyStage,
    previousStep,
    freeMovement: options.freeMovement,

    handleLinkClick,
    getIsLinkCompleted,
    getIsLinkSelected,
    getIsLinkDisabled,
    getHasLinkAlert,
    getHasLinkTooltip,
  });

  return {
    steps: stepsRef,
    flattenSteps,
    getFlatIndexOfStep,
    currentFlatStepIndex,
    currentFlatStep,
    lastCompletedFlatStepIndex,
    goToStep,
    goBack,
    goNext,
    data,
    saveData,
    previousStep,
    freeMovement: options.freeMovement,

    handleLinkClick,
    getIsLinkCompleted,
    getIsLinkSelected,
    getIsLinkDisabled,
    getHasLinkAlert,
    getHasLinkTooltip,
  };
}
