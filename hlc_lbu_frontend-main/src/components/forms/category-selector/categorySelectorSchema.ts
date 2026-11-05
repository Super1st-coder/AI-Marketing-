import { array, boolean, object, string } from "yup";

export const categorySelectorSchema = array()
  .of(
    object({
      name: string().required(),
      items: array()
        .of(
          object({
            name: string().required(),
            checked: boolean().default(false).required(),
          }),
        )
        .required(),
    }),
  )
  .required()
  .test("need-file", "category-selector.errors.min-items", (data) => {
    const selectedItemCount = data.reduce((acc, category) => {
      const selectedItems = category.items.filter((item) => item.checked);
      return acc + selectedItems.length;
    }, 0);

    return selectedItemCount >= 3;
  });
