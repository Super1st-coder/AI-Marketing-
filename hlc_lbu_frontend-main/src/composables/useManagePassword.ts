export default function useManagePassword() {
  const router = useRouter();
  const createForm = ref<CreateForm>({ password: "", confirmPassword: "" });

  const error = ref<string>("");

  const success = ref<string>();

  const isValid = ref(true);

  const submitCreatePassword = async (): Promise<void> => {
    isValid.value = Boolean(createForm.value.password);

    if (isValid.value) {
      createPassword(
        getEmailFromQuery(router.currentRoute.value.query.account),
        router.currentRoute.value.query.code as string,
        createForm.value.password,
      ).then(() => {
        router.push({ name: "Login" });
      });
    } else {
      error.value = "Form is invalid. Please fill in all required fields.";
      setTimeout(() => {
        error.value = "";
        isValid.value = true;
      }, 2000);
    }
  };

  const submitForgotPassword = () => {
    isValid.value = Boolean(createForm.value.password);

    if (isValid.value) {
      forgotPassword(
        getEmailFromQuery(router.currentRoute.value.query.account),
        router.currentRoute.value.query.code as string,
        createForm.value.password,
      ).then();
    } else {
      error.value = "Form is invalid. Please fill in all required fields.";
      setTimeout(() => {
        error.value = "";
        isValid.value = true;
      }, 2000);
    }
  };

  const createPassword = async (
    email: string,
    code: string,
    password: string,
  ): Promise<boolean> => {
    try {
      await $apiAuth<any>("/v1/admin/member/register/finish", {
        method: "PUT",
        body: {
          email,
          confirmation_code: code,
          password,
          confirm_password: password,
        },
      });

      success.value = "Password successfully created!";
      error.value = "";

      router.push({ name: "Login" });

      return true;
    } catch (errorRes: any) {
      const backendMessage = errorRes?.data?.message;

      if (backendMessage?.code === "SYSVAL001") {
        error.value = backendMessage.text;
      } else {
        error.value = "An unexpected error occurred.";
      }

      success.value = "";
      return false;
    }
  };

  const forgotPassword = async (
    email: string,
    code: string,
    password: string,
  ): Promise<any | void> => {
    try {
      const res = await $apiAuth<any>("/v1/member/password/reset/finish", {
        method: "PUT",
        body: {
          email,
          confirmation_code: code,
          new_password: password,
        },
      });

      success.value = "Password successfully changed!";
      error.value = "";
      return res;
    } catch (errorRes: any) {
      const backendMessage = errorRes?.data?.message;

      if (backendMessage.code === "SYSVAL001") {
        error.value = backendMessage.text;
      } else {
        error.value = "An unexpected error occurred.";
      }

      success.value = "";
    }
  };

  return {
    createForm,
    submitCreatePassword,
    submitForgotPassword,
    isValid,
    error,
    success,
  };
}
