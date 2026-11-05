export type AtLeast<T, K extends keyof T> = Partial<T> & Pick<T, K>;

// Utility type to make picked properties both required and non-nullable
export type RequiredNonNullable<T, K extends keyof T> = {
  [P in K]-?: NonNullable<T[P]>;
};

// estado para Register form
export type RegisterForm = {
  nombres: string;
  apellidos: string;
  email: string;
  password: string;
  aceptaTerminos: boolean;
};

// estado para Forgot your password
export type ForgotForm = {
  email: string;
};

// estado para Create your password
export type CreateForm = {
  password: string;
  confirmPassword: string;
};

export type PermissionFunctionName =
  | "ADMIN_ORG"
  | "ADMIN_USER"
  | "ADMIN_ROLES"
  | "BRAND"
  | "PRODUCT"
  | "TARGET_CUSTOMER"
  | "CAMPAIGN_SETUP"
  | "PROJECT"
  | "UMBRELLA_CAMPAIGN"
  | "FUNNEL_FLOW"
  | "APPROVAL_PROCESS"
  | "CAMPAIGN_CREATIVE"
  | "CAMPAIGN_LAUNCHPAD";

export type UserRoleAndActions = {
  actions: {
    id: string;
    name: string;
  }[];
  function_name: PermissionFunctionName;
  function_long_name: string;
  rol_name: string;
  rol_long_name: string;
};

export type UserPermission = Pick<
  UserRoleAndActions,
  "actions" | "function_name" | "function_long_name"
>;

// type para el response de login
export type ApiResponseLogin = {
  ok: number;
  data: {
    extra_info: {
      username: string;
      status: string;
      full_name: string;
      permissions: UserRoleAndActions[];
    };
    access_token: string;
    refresh_token: string;
  };
};

export type BaseApiResponse = {
  ok: number;
  message?: {
    code: string;
    text: string;
  };
  response?: any;
};

export type BaseApiResponseData<T> = BaseApiResponse & { data: T };

export type BaseApiPaginatedResponseData<T> = BaseApiResponse & {
  data: T[];
  count: number;
  total: number;
};

export type RefinerAttributes = Record<string, string[]>;

export type CategorySelectorAttributes = Record<string, string[]>;

export type ApiSortMode = "desc" | "asc";
export type ApiSortRecord = Record<string, ApiSortMode>;
export type ApiFilterRecord = { name: string | undefined } & Record<
  string,
  string | undefined
>;

export type ApiDefaultPaginationOptions = {
  range?: [number] | [number, number];
  order?: ApiSortRecord;
  filter?: ApiFilterRecord;
};

// Product Image

export interface ProductImageResponse {
  ok: number;
  data?: {
    project_id: number;
    product_image_id: string;
  };
  message?: {
    code: string;
    text: string;
  };
}

// Image prompts
export interface ImagePrompt {
  id: number;
  preferred: number;
  description: string;
}

// For some reason, umbrella campaigns have a different type for prompts
export interface ImagePrompt2 {
  id: number;
  preferred: number;
  prompt: string;
}

//************************ */

export function flattenPrompts(
  buyerPersonImagePrompts?: ImagePrompt[] | ImagePrompt2[] | null,
): string[] {
  return (
    buyerPersonImagePrompts?.map((item: ImagePrompt | ImagePrompt2) =>
      "description" in item ? item.description : item.prompt,
    ) ?? []
  );
}

export async function generateMockPrompts() {
  const prompts: ImagePrompt[] = [...Array(6)].map<ImagePrompt>((_, index) => ({
    id: index,
    description:
      "This is some text within a card body. Jelly lemon drops tiramisu chocolate topping cheesecake chocolate bar. Danish muffin icing donut.",
    preferred: 0,
  }));

  await sleep(1000);

  return prompts;
}
