import { CSSProperties } from "vue";

export default function useCommonComponentClasses(props?: {
  color?: MaybeRefOrGetter<CommonComponentColor | undefined>;
  variant?: MaybeRefOrGetter<CommonComponentVariant | undefined>;
  disabled?: MaybeRefOrGetter<boolean | undefined>;
  customColor?: MaybeRefOrGetter<string | undefined>;
  hoverable?: MaybeRefOrGetter<boolean | undefined>;
}) {
  const className = computed<ClassName>(() => {
    const color = toValue(props?.color);
    const variant = toValue(props?.variant);
    const disabled = toValue(props?.disabled);
    const hoverable = toValue(props?.hoverable);

    return {
      // Disabled
      "tw:opacity-45": disabled,

      // Hover
      "tw:cursor-pointer tw:hover:brightness-95": hoverable && !disabled,

      // Default color
      "tw:bg-gray-300 tw:text-primary-text":
        color === "default" && variant === "solid",

      // Outlined variant
      "tw:border tw:bg-white": variant === "outlined",
      "tw:border-[currentColor]":
        variant === "outlined" && color !== "secondary",

      // Text color
      "tw:text-white": color !== "default" && variant === "solid",

      // Primary
      "tw:bg-primary": color === "primary" && variant === "solid",
      "tw:bg-primary-100": color === "primary" && variant === "label",
      "tw:text-primary": color === "primary" && variant !== "solid",

      // Secondary
      "tw:bg-gray-300": color === "secondary" && variant === "solid",
      "tw:bg-gray-100": color === "secondary" && variant === "label",
      "tw:text-gray-800":
        color === "secondary" && variant !== "text" && variant !== "solid",
      "tw:text-gray-600": color === "secondary" && variant === "text",
      "tw:border-gray-300": color === "secondary" && variant === "outlined",

      // Success
      "tw:bg-success": color === "success" && variant === "solid",
      "tw:bg-success/16": color === "success" && variant === "label",
      "tw:text-success": color === "success" && variant !== "solid",

      // Error
      "tw:bg-error": color === "error" && variant === "solid",
      "tw:bg-error/16": color === "error" && variant === "label",
      "tw:text-error": color === "error" && variant !== "solid",

      // Warning
      "tw:bg-warning": color === "warning" && variant === "solid",
      "tw:bg-warning/16": color === "warning" && variant === "label",
      "tw:text-warning": color === "warning" && variant !== "solid",

      // Info
      "tw:bg-info": color === "info" && variant === "solid",
      "tw:bg-info/16": color === "info" && variant === "label",
      "tw:text-info": color === "info" && variant !== "solid",
    };
  });

  const style = computed<CSSProperties>(() => {
    const variant = toValue(props?.variant);
    const customColor = toValue(props?.customColor);

    return {
      color: customColor && variant !== "solid" ? customColor : undefined,
      backgroundColor:
        customColor && (variant === "solid" || variant === "label")
          ? customColor
          : undefined,
    };
  });

  return { className, style };
}
