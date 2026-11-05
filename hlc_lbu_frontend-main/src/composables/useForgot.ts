import { ref } from "vue";
import { $apiAuth } from "../utils/api";
import { useRouter } from "vue-router";
import { ForgotForm } from "../utils/type-declarations";
import { SingUpFinishResponse } from "./useRegister";
import { handleResetPasswordError } from "@/services/common-errors";

type ForgotFinishForm = {
  password: string;
};
export default function useForgot() {
  const router = useRouter();
  const forgotForm = ref<ForgotForm>({ email: "" });
  const forgotFinishForm = ref<ForgotFinishForm>({ password: "" });

  const errors = ref<string>("");

  const isValid = ref(true);

  const submitEmail = () => {
    isValid.value = Boolean(forgotForm.value.email);

    if (isValid.value) {
      sendEmail().then();
    } else {
      errors.value = "Form is invalid. Please fill in all required fields.";
      setTimeout(() => {
        errors.value = "";
        isValid.value = true;
      }, 2000);
    }
  };

  const resetPassword = async (
    email: string,
    code: string,
  ): Promise<SingUpFinishResponse> => {
    try {
      const res = await $apiAuth<SingUpFinishResponse>(
        "/v1/member/password/reset/finish",
        {
          method: "PUT",
          body: {
            email: email,
            confirmation_code: code,
            new_password: forgotFinishForm.value.password,
          },
        },
      );
      return res;
    } catch (error: any) {
      handleResetPasswordError(error);
      throw error;
    }
  };

  const sendEmail = async () => {
    try {
      const res = await $apiAuth("/v1/member/password/reset", {
        method: "POST",
        body: {
          email: forgotForm.value.email,
        },
        onResponseError({ response }) {
          errors.value = "Verify your email!";
          console.log("errors : " + JSON.stringify(response._data.errors));
          setTimeout(() => {
            errors.value = "";
          }, 2000);
        },
      });
      if ((res.status = 200)) router.push("/");
    } catch (err) {
      console.error(err);
    }
  };

  return {
    forgotForm,
    forgotFinishForm,
    submitEmail,
    resetPassword,
    isValid,
    errors,
  };
}
