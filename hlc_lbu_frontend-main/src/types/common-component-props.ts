export type CommonComponentColor =
  | "default"
  | "primary"
  | "secondary"
  | "success"
  | "error"
  | "warning"
  | "info";

export type CommonComponentVariant = "solid" | "outlined" | "text" | "label";

export type CommonComponentSize = "xs" | "sm" | "md" | "lg" | "xl" | "2xl";

type SingleClassName = undefined | null | string | Record<string, any>;

export type ClassName = SingleClassName | SingleClassName[];
