import { array, bool, object, string } from "yup";

const defaultError =
  "category-refiner.errors.select-at-least-one-item-from-each-category";
const listCannotBeEmptyError = "category-refiner.errors.list-cannot-be-empty";

export const categoryRefinerSchema = array()
  .required(listCannotBeEmptyError)
  .of(
    object({
      name: string().required(),
      isSaved: bool().required(defaultError).is([true], defaultError),
      items: array()
        .required()
        .of(object({ name: string().required() })),
    }),
  );

const mandatoryCompletedError =
  "category-refiner.errors.mandatory-categories-must-be-fully-completed";

export const mandatoryCategoryRefinerSchema = array()
  .required()
  .of(
    object({
      name: string().required().trim(),
      isSaved: bool()
        .required(mandatoryCompletedError)
        .is([true], mandatoryCompletedError),
      items: array()
        .required()
        .of(object({ name: string().required().trim() })),
    }),
  );

export const optionalCategoryRefinerSchema = array()
  .required()
  .of(
    object({
      name: string().required(),
      isSaved: bool(),
      items: array()
        .required()
        .of(object({ name: string().required() })),
    }),
  );
