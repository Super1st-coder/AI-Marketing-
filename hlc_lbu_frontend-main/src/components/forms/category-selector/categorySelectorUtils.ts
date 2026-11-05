import {
  CategorySelector,
  CategorySelectorItem,
} from "./categorySelectorTypes";

// This function transforms the attributes object into an array of CategorySelector objects.
export function getCategorySelector(
  attributes: RefinerAttributes,
  saved?: CategorySelectorAttributes | null,
): CategorySelector[] {
  let categories = [
    ...Object.keys(attributes).map<CategorySelector>((key) => ({
      name: key,
      items: Array.isArray(attributes[key])
        ? attributes[key].map<CategorySelectorItem>((item: string) => ({
            name: item,
            checked: saved?.[key]?.includes(item) ?? false,
          }))
        : [
            {
              name: attributes[key],
              checked: saved?.[key]?.includes(attributes[key]) ?? false,
            },
          ],
    })),
  ];

  // Filter out categories that don't have any items
  categories = categories.filter((category) => category.items.length > 0);

  return categories;
}

// This function transforms the CategorySelector objects back into the original attributes object.
export function transformCategorySelectorToJson(
  refinerCategories: CategorySelector[],
): CategorySelectorAttributes {
  const attributes: CategorySelectorAttributes = {};

  refinerCategories.forEach((category) => {
    const items = category.items
      .filter((item) => item.checked)
      .map((item) => item.name);
    attributes[category.name] = items;
  });

  return attributes;
}
