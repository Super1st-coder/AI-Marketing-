import { categoryRefinerKey, RefinerCategory } from "./categoryRefinerTypes";

export function useCategoryRefiner(initialCategories?: RefinerCategory[]) {
  const data = ref(initialCategories ?? []);

  provide(categoryRefinerKey, data);

  return { data };
}

export function useCategoryRefinerData() {
  const data = inject(categoryRefinerKey) as Ref<RefinerCategory[]>;

  return { data };
}
