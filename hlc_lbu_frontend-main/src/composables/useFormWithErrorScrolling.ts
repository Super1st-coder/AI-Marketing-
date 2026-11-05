import type {
  FormOptions,
  GenericObject,
  InvalidSubmissionHandler,
  RawFormSchema,
  SubmissionHandler,
  TypedSchema,
} from "vee-validate";

/**
 * Enhanced useForm that automatically scrolls to validation errors
 * Wraps vee-validate's useForm with error scrolling functionality
 */
export function useFormWithErrorScrolling<
  TValues extends GenericObject = GenericObject,
  TOutput extends GenericObject = TValues,
  TSchema extends RawFormSchema<TValues> | TypedSchema<TValues, TOutput> =
    | RawFormSchema<TValues>
    | TypedSchema<TValues, TOutput>,
>(
  opts?: FormOptions<TValues, TOutput, TSchema> & {
    resetDirtyOnSubmit?: MaybeRefOrGetter<boolean>;
  },
) {
  const form = useForm<TValues, TOutput, TSchema>(opts);

  // A bool used to know if the form was submitted succesfully
  const submitSuccess = ref(false);

  // // Watch for errors and scroll to first error
  // watch(form.errors, (errors) => {
  //   scrollToFirstError(errors);
  // });

  // Override handleSubmit to include error scrolling on submit
  const originalHandleSubmit = form.handleSubmit;
  const handleSubmit = <TReturn = unknown>(
    cb: SubmissionHandler<TValues, TOutput, TReturn>,
    onSubmitValidationErrorCb?: InvalidSubmissionHandler<TValues, TOutput>,
  ) => {
    return originalHandleSubmit(
      async (values, ctx) => {
        submitSuccess.value = false;

        const result = await cb(values, ctx);

        if (toValue(opts?.resetDirtyOnSubmit)) {
          // @ts-expect-error
          form.resetForm({ values });
        }

        submitSuccess.value = true;

        return result;
      },
      (ctx) => {
        submitSuccess.value = false;

        // Scroll to first error on submit validation failure
        scrollToFirstError(ctx.errors);

        // Call the original invalid callback if provided
        return onSubmitValidationErrorCb?.(ctx);
      },
    );
  };

  // Reset the state of submitSuccess when the form is dirty
  watch(
    () => form.meta.value.dirty,
    (dirty) => {
      if (dirty) {
        submitSuccess.value = false;
      }
    },
  );

  // Reset the state of submitSuccess when any field changes
  watch(form.values, () => {
    submitSuccess.value = false;
  });

  return {
    ...form,
    handleSubmit,
    submitSuccess,
    // Export utility in case manual scrolling is needed
    scrollToFirstError: () => scrollToFirstError(form.errors.value),
  };
}
