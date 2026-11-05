import type { FormErrors } from "vee-validate";

/** Prefer this over `[name]` when a field should scroll to a specific element. */
export const ERROR_SCROLL_TARGET_ATTR = "data-error-scroll-target";

export const scrollElementIntoView = (element: Element) => {
  element.scrollIntoView({ behavior: "instant", block: "nearest" });
};

/**
 * Scrolls to the a element treating it as a field
 */
export const scrollToFieldElement = async (element: Element) => {
  await sleep(0);
  element.scrollIntoView({
    behavior: "instant",
    block: "nearest",
    inline: "nearest",
  });
};

function queryFieldScrollElement(fieldName: string): HTMLElement | null {
  return (
    document.querySelector<HTMLElement>(
      `[${ERROR_SCROLL_TARGET_ATTR}="${fieldName}"]`,
    ) ?? document.querySelector<HTMLElement>(`[name="${fieldName}"]`)
  );
}

/**
 * Scrolls to the field with a given name
 */
export const scrollToField = async (fieldName: string): Promise<boolean> => {
  const element = queryFieldScrollElement(fieldName);
  if (element) {
    await scrollToFieldElement(element);
    return true;
  }

  return false;
};

/**
 * Scrolls to the first field with a validation error
 */
export const scrollToFirstError = async (
  errors: FormErrors<Record<string, any>>,
) => {
  const errorKeys = Object.keys(errors);
  if (errorKeys.length === 0) return;

  // Wait for error UI (e.g. FieldError with data-error-scroll-target) to render
  await nextTick();

  const errorKeySet = new Set(errorKeys);

  // Prefer DOM order so the visually first invalid field is targeted.
  // Object.keys(errors) is not guaranteed to match field order on the page.
  const fieldsInDomOrder = document.querySelectorAll<HTMLElement>(
    `[${ERROR_SCROLL_TARGET_ATTR}], [name]`,
  );
  for (const element of fieldsInDomOrder) {
    const fieldName =
      element.getAttribute(ERROR_SCROLL_TARGET_ATTR) ??
      element.getAttribute("name");
    if (!fieldName || !errorKeySet.has(fieldName)) {
      continue;
    }

    const target = queryFieldScrollElement(fieldName);
    if (target) {
      await scrollToFieldElement(target);
      return;
    }
  }
};

export const resetElementScroll = (element: HTMLElement) => {
  element.scrollTop = 0;
};

export const scrollElementToItsBottom = (element: HTMLElement) => {
  element.scrollTop = element.scrollHeight;
};

export const scrollWindowToTop = () => {
  window.scrollTo(0, 0);
};
