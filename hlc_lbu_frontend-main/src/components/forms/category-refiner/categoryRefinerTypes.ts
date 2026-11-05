import { IconCardVariant } from "@/components/cards/IconCard.vue";
import { RefinerAttributes } from "@/utils/type-declarations";

export interface RefinerItem {
  name: string;
  checked?: boolean;
}

export interface RefinerCategory {
  name: string;
  items: RefinerItem[];
  isSaved?: boolean;
  hasBeenOpened?: boolean;
  hasBeenClosed?: boolean;
  isOpen?: boolean;
  canBeDeleted?: boolean;
  minimumItems?: number;
  maxItems?: number;
}

export type CategoryRefinerStyles = Record<
  string,
  { icon?: string; variant?: IconCardVariant }
>;

export const categoryRefinerKey = Symbol() as InjectionKey<
  Ref<RefinerCategory[]>
>;

type TransformToRefinerCategoriesOptions = Pick<
  RefinerCategory,
  "isSaved" | "canBeDeleted" | "minimumItems" | "maxItems"
>;

export function transformToRefinerCategories(
  data: RefinerAttributes,
  options?: TransformToRefinerCategoriesOptions,
): RefinerCategory[] {
  return Object.keys(data).map((key) => ({
    name: key,
    items: data[key].map<RefinerItem>((item: string) => ({
      name: item,
      checked: options?.isSaved,
    })),
    isSaved: options?.isSaved ?? false,
    hasBeenOpened: options?.isSaved,
    ...options,
  }));
}

export function transformRefinerCategoriesToJson(
  refinerCategories: RefinerCategory[],
  onlyChecked: boolean = false,
): Record<string, string[]> {
  const jsonConvertido: Record<string, string[]> = {};

  refinerCategories.forEach((category) => {
    jsonConvertido[category.name] = category.items
      .filter((item) => !onlyChecked || item.checked)
      .map((item) => item.name);
  });

  return jsonConvertido;
}

type GetRefinerCategoriesOptions = Pick<
  RefinerCategory,
  "canBeDeleted" | "minimumItems" | "maxItems"
> & {
  categories?: Record<
    string,
    Pick<RefinerCategory, "canBeDeleted" | "minimumItems" | "maxItems">
  >;
};

export function filterCategoryAttributes(items: string[]) {
  return items.filter((item) => item !== "Info not available");
}

export function getRefinerCategories(
  saved?: RefinerAttributes | null,
  generated?: RefinerAttributes | null,
  options?: GetRefinerCategoriesOptions,
): RefinerCategory[] {
  let result: RefinerCategory[] = [];

  // Add saved categories
  if (saved) {
    result = Object.entries(saved).map(([name, items]) => {
      // Filter out the "Info not available" items
      items = filterCategoryAttributes(items);
      const categoryOptions = options?.categories?.[name];

      const minimumItems =
        categoryOptions?.minimumItems ?? options?.minimumItems;
      const maxItems = categoryOptions?.maxItems ?? options?.maxItems;

      // Is the card of this category saved?
      let isSaved = false;
      if (minimumItems !== undefined) {
        isSaved = items.length >= minimumItems;
      } else {
        // If no specific minimum is defined, it's "saved" if it has any items.
        isSaved = items.length > 0;
      }

      // A category is not "saved" if it exceeds the max items limit.
      if (isSaved && maxItems !== undefined) {
        isSaved = items.length <= maxItems;
      }

      return {
        name: name,
        items: items.map<RefinerItem>((item: string) => ({
          name: item,
          checked: true,
        })),
        isSaved: isSaved,
        hasBeenOpened: isSaved,
        isOpen: false,
        minimumItems: minimumItems,
        maxItems: maxItems,
        canBeDeleted: categoryOptions?.canBeDeleted ?? options?.canBeDeleted,
      };
    });
  }

  // Merge generated categories
  if (generated) {
    Object.entries(generated).forEach(
      ([generatedCategoryName, generatedCategoryItems]) => {
        // Filter out the "Info not available" items
        generatedCategoryItems = filterCategoryAttributes(
          generatedCategoryItems,
        );

        // Find a saved category that has the same name
        const savedCategory = result.find(
          (category) => category.name === generatedCategoryName,
        );

        if (savedCategory) {
          // The category already exists, so we need to merge the saved one and the generated one
          generatedCategoryItems.forEach((generatedItemName) => {
            // Find out if the generated item already exists in the saved items
            const savedItem = savedCategory.items.find(
              (item) => item.name === generatedItemName,
            );

            if (!savedItem) {
              // The item doesn't exist, we'll include it
              savedCategory.items.push({
                name: generatedItemName,
                checked: false,
              });
            }
          });
        } else {
          // The category didn't exist in the saved ones, so we create it
          const categoryOptions = options?.categories?.[generatedCategoryName];
          const minimumItems =
            categoryOptions?.minimumItems ?? options?.minimumItems;
          const maxItems = categoryOptions?.maxItems ?? options?.maxItems;

          result.push({
            name: generatedCategoryName,
            items: generatedCategoryItems.map<RefinerItem>((item: string) => ({
              name: item,
              checked: false,
            })),
            isSaved: false,
            hasBeenOpened: false,
            isOpen: false,
            minimumItems: minimumItems,
            maxItems: maxItems, // <-- Asignación de maxItems
            canBeDeleted:
              categoryOptions?.canBeDeleted ?? options?.canBeDeleted,
          });
        }
      },
    );
  }

  return result;
}

export function getSummaryRefinerCategories(
  saved?: RefinerAttributes | null,
  generated?: RefinerAttributes | null,
) {
  if (!saved || Object.keys(saved).length === 0) {
    return generated ? transformToRefinerCategories(generated) : [];
  }

  return transformToRefinerCategories(saved);
}
