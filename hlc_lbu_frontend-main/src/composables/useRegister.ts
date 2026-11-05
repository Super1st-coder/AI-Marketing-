import { ref } from "vue";
import { $apiAuth } from "../utils/api";
import { BaseApiResponseData, RegisterForm } from "../utils/type-declarations";
import { handleSingUpFinishError } from "@/services/common-errors";

export type SingUpFinishResponse = BaseApiResponseData<{
  ok: number;
  message?: {
    code: string;
    text: string;
  };
}>;

export type ResendemailResponse = BaseApiResponseData<{
  ok: number;
  message?: {
    code: string;
    text: string;
  };
}>;

export default function useRegister() {
  const registerForm = ref<RegisterForm>({
    nombres: "",
    apellidos: "",
    email: "",
    password: "",
    aceptaTerminos: false,
  });

  const errors = ref<string>("");

  const passwordIsValid = (password: string): boolean => {
    // Al menos 8 caracteres, al menos un número y al menos un caracter especial # $ &
    const regex = /^(?=.*[0-9])(?=.*[#\$&]).{8,}$/;
    return regex.test(password);
  };

  const isValid = computed(() =>
    Boolean(
      registerForm.value.email &&
      passwordIsValid(registerForm.value.password) &&
      registerForm.value.nombres &&
      registerForm.value.apellidos &&
      registerForm.value.aceptaTerminos,
    ),
  );

  const submitRegister = async (): Promise<number> => {
    if (isValid.value) {
      const status = await register();
      return status;
    } else {
      errors.value = "Formulario Invalido. LLene todos los campos requeridos";
      setTimeout(() => {
        errors.value = "";
      }, 5000);
      return 0;
    }
  };

  const register = async (): Promise<number> => {
    let status = 0;
    try {
      const res = await $apiAuth("/v1/member/signup", {
        method: "POST",
        body: {
          email: registerForm.value.email,
          first_name: registerForm.value.nombres,
          last_name: registerForm.value.apellidos,
          password: registerForm.value.password,
        },
        onResponseError({ response }) {
          errors.value = "Error: " + response._data.message.text;
          console.log("errors ****: " + JSON.stringify(response._data.message));
          setTimeout(() => {
            errors.value = "";
            return status;
          }, 5000);
        },
      });
      console.log("res : " + JSON.stringify(res));
      if (res.ok === 1) {
        return 1;
      } else {
        return 0;
      }
    } catch (err) {
      console.error(err);
      return status;
    }
  };

  const signupFinish = async (
    email: string,
    code: string,
  ): Promise<SingUpFinishResponse> => {
    try {
      const res = await $apiAuth<SingUpFinishResponse>(
        "/v1/member/signup/finish",
        {
          method: "PUT",
          body: {
            email: email,
            confirmation_code: code,
          },
        },
      );
      return res;
    } catch (error: any) {
      const finishError: SingUpFinishResponse = {
        ok: 1,
        data: {
          ok: 1,
          message: {
            code: "SYSVAL001",
            text: "",
          },
        },
      };
      if (error.response._data.message.code === "SYSVAL001") {
        errors.value = error.response._data.message.code;
        return finishError;
      } else {
        handleSingUpFinishError(error);
        throw error;
      }
    }
  };

  const unsubscribeAccount = async (
    email: string,
    code: string,
  ): Promise<SingUpFinishResponse> => {
    try {
      const res = await $apiAuth<SingUpFinishResponse>(
        "/v1/member/unsubscribe",
        {
          method: "PUT",
          body: {
            email: email,
            confirmation_code: code,
          },
        },
      );
      return res;
    } catch (error: any) {
      handleSingUpFinishError(error);
      throw error;
    }
  };

  const resendEmailConfirmation = async (
    email: string,
  ): Promise<ResendemailResponse> => {
    try {
      const res = await $apiAuth<ResendemailResponse>(
        "/v1/member/signup/resend_confirmation",
        {
          method: "POST",
          body: {
            email: email,
          },
        },
      );
      return res;
    } catch (error: any) {
      handleSingUpFinishError(error);
      throw error;
    }
  };

  return {
    registerForm,
    submitRegister,
    isValid,
    errors,
    signupFinish,
    resendEmailConfirmation,
    unsubscribeAccount,
  };
}
