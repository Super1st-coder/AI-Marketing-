// Copy of the type used by @vueuse/router
type ReactiveRouteOptionsWithTransform<V, R> =
  | ((val: V) => R)
  | {
      get?: (value: V) => R;
      set?: (value: R) => V;
    };

export const optionalNumber: ReactiveRouteOptionsWithTransform<
  string | null | number,
  number | null | undefined
> = {
  get: (value) => {
    if (value != null) {
      if (typeof value === "number") {
        return value;
      }

      return parseInt(value);
    }

    return undefined;
  },
  set: (value) => {
    if (value != undefined && value != null) {
      return value.toString();
    }

    return null;
  },
};
