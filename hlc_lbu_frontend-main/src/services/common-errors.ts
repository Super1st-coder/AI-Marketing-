import { BaseApiResponse } from "@/utils/type-declarations";
import { AuthRedirectError } from "@/utils/api";
import { handleSessionExpired } from "@/utils/auth";
import { FetchError } from "ofetch";

export class NotFoundError extends Error {
  readonly is404 = true;

  constructor(message: string) {
    super(message);
    this.name = this.constructor.name;
  }
}

export class PermissionError extends Error {
  constructor() {
    super("PERMISSION_ERROR");
    this.name = this.constructor.name;
  }
}

export class NetworkError extends Error {
  constructor() {
    super("NETWORK_ERROR");
    this.name = this.constructor.name;
  }
}

export class UnidentifiedError extends Error {
  constructor() {
    super("UNIDENTIFIED_ERROR");
    this.name = this.constructor.name;
  }
}

export class LlmOutputError extends Error {
  constructor(message = "LLM_OUTPUT_ERROR") {
    super(message);
    this.name = this.constructor.name;
  }
}

/**
 * A request ended before its answer arrived: the backend stopped waiting for
 * another service, the load balancer did, or the browser did. The work it
 * started may still finish on the backend.
 *
 * Extends `LlmOutputError` because timeouts were thrown as one before, and
 * the screens that catch it to show an inline message keep doing so.
 */
export class RequestTimeoutError extends LlmOutputError {
  constructor() {
    super("REQUEST_TIMEOUT");
  }
}

/**
 * Luca Credits refusals. Sinergia passes Fury's billing code through as `message.code`
 * (it used to flatten every one of them into FURY001). Thrown as typed errors so a screen can
 * show "buy more" vs "video limit" vs "try again later" instead of a generic failure.
 */
export class BillingError extends Error {
  readonly code: string;
  readonly detail?: string;

  constructor(code: string, detail?: string) {
    super(code);
    this.name = this.constructor.name;
    this.code = code;
    this.detail = detail;
  }
}

/** The company has run out of credits (402 INSUFFICIENT_CREDITS). */
export class InsufficientCreditsError extends BillingError {
  constructor(detail?: string) {
    super("INSUFFICIENT_CREDITS", detail);
  }
}

/** The company reached its video-generation spending limit (402 LIMIT_REACHED). */
export class CreditLimitReachedError extends BillingError {
  constructor(detail?: string) {
    super("LIMIT_REACHED", detail);
  }
}

/** The credits service couldn't be reached, so nothing was generated (503). */
export class BillingUnavailableError extends BillingError {
  constructor(detail?: string) {
    super("BILLING_UNAVAILABLE", detail);
  }
}

/** The company/brand couldn't be identified for billing (422). */
export class BillingIdentityMissingError extends BillingError {
  constructor(detail?: string) {
    super("BILLING_IDENTITY_MISSING", detail);
  }
}

/** The AI model that ran has no price in Luca Credits, so the call was refused (402). */
export class UnbillableModelError extends BillingError {
  constructor(detail?: string) {
    super("UNBILLABLE_MODEL", detail);
  }
}

const BILLING_ERRORS: Record<string, typeof InsufficientCreditsError> = {
  INSUFFICIENT_CREDITS: InsufficientCreditsError,
  LIMIT_REACHED: CreditLimitReachedError,
  BILLING_UNAVAILABLE: BillingUnavailableError,
  BILLING_IDENTITY_MISSING: BillingIdentityMissingError,
  UNBILLABLE_MODEL: UnbillableModelError,
};

export class ImageRequiredAttributesEmpty extends Error {
  constructor() {
    super("IMAGE_REQUIRED_ATTRIBUTES_EMPTY");
    this.name = this.constructor.name;
  }
}

export class ProjectNotFoundError extends NotFoundError {
  constructor() {
    super("PROJECT_NOT_FOUND");
  }
}

export class BrandNotFoundError extends NotFoundError {
  constructor() {
    super("BRAND_NOT_FOUND");
  }
}

export class ProductNotFoundError extends NotFoundError {
  constructor() {
    super("PRODUCT_NOT_FOUND");
  }
}

export class BuyerPersonNotFoundError extends NotFoundError {
  constructor() {
    super("BUYER_PERSON_NOT_FOUND");
  }
}

export class UmbrellaCampaignNotFoundError extends NotFoundError {
  constructor() {
    super("UMBRELLA_CAMPAIGN_NOT_FOUND");
  }
}

export class CampaignNotFoundError extends NotFoundError {
  constructor() {
    super("CAMPAIGN_NOT_FOUND");
  }
}

export class AdNotFoundError extends NotFoundError {
  constructor() {
    super("AD_NOT_FOUND");
  }
}

export class SingUpFinishResponseError extends Error {
  constructor() {
    super("ERROR_SING_UP_FINISH");
    this.name = this.constructor.name;
  }
}

export class EmailNotFoundError extends Error {
  constructor() {
    super("EMAIL_NOT_FOUND");
    this.name = this.constructor.name;
  }
}

export class EmailResendConfirmationError extends Error {
  constructor() {
    super("EMAIL_RESEND_CONFIRMATION_ERROR");
    this.name = this.constructor.name;
  }
}

export class ResetPasswordError extends Error {
  constructor() {
    super(" SHOULD_INIT_RESET_PSSWORD_PROCESS");
    this.name = this.constructor.name;
  }
}

export class IncorrectValidationCodeError extends Error {
  constructor() {
    super("INCORRECT_VALIDATION_CODE");
    this.name = this.constructor.name;
  }
}

export class ImageNotFoundError extends Error {
  constructor() {
    super("IMAGE_NOT_FOUND");
    this.name = this.constructor.name;
  }
}

// Legacy
export function handleProjectError(error: BaseApiResponse) {
  if (error.message?.text === "ERROR - Project NOT Found")
    throw new ProjectNotFoundError();
}

export function handleCommonErrors(error: BaseApiResponse) {
  // Get code and message from error
  const code =
    error.message?.code ??
    ((error as any)?.code as string | Record<string, any> | undefined);
  const message =
    error.message?.text ??
    ((error as any)?.message as string | Record<string, any> | undefined);
  const status =
    (error as any)?.status ||
    (error as any)?.statusCode ||
    (error as any)?.response?.status;

  console.error(
    "Error in handleCommonErrors:\n",
    { code, message },
    "\n",
    error,
  );

  // Fall through abort errors
  if ((error as any)?.name === "AbortError") {
    throw error;
  }

  // Timeouts: the browser stopped waiting (ofetch's `timeout`), or the load
  // balancer did, which answers with its own HTML page
  if (
    (error instanceof FetchError &&
      ((error.cause as Error | undefined)?.name === "TimeoutError" ||
        status === 504)) ||
    (typeof error === "string" && /504 gateway time-?out/i.test(error))
  ) {
    throw new RequestTimeoutError();
  }

  // Detect network errors (fetch throws TypeError on network errors)
  if (error instanceof FetchError) {
    throw new NetworkError();
  }

  if (error instanceof AuthRedirectError) throw error;
  handleProjectError(error);

  // Handle token expired errors
  if (
    code === "Token expired" ||
    (typeof message === "object" &&
      (message as any)?.text === "Token expired") ||
    (typeof message === "object" && (message as any)?.code === "ESEC001")
  ) {
    handleSessionExpired("token_expired_in_common_errors");
    throw new AuthRedirectError("Token expired. Redirecting to login.");
  }

  // Handle access denied errors
  if (
    status === 401 ||
    code === "Access Denied" ||
    message === "Access Denied"
  ) {
    throw new PermissionError();
  }

  // Luca Credits refusals (codes passed through by Sinergia from Fury)
  if (typeof code === "string" && code in BILLING_ERRORS) {
    throw new BILLING_ERRORS[code](
      typeof message === "string" ? message : undefined,
    );
  }

  // Handle errors with message as string
  if (message && typeof message === "string") {
    const normalizedMessage = message.toLocaleLowerCase();

    // The backend stopped waiting for another service, e.g. Sinergia for
    // Fury: "Read timed out. (read timeout=280)"
    if (message.includes("timed out") || message.includes("timeout")) {
      throw new RequestTimeoutError();
    }

    // IA and N8N related errors
    if (
      code?.startsWith("IA") ||
      message === "ERROR - Processing IA LLM Output" ||
      message === "ERROR - Processing in IA LLM Model" ||
      code?.startsWith("N8N") ||
      message?.includes("n8n")
    )
      throw new LlmOutputError();

    // Brand not found
    if (normalizedMessage.includes("brand not found")) {
      throw new BrandNotFoundError();
    }

    // Product not found
    if (normalizedMessage.includes("product not found")) {
      throw new ProductNotFoundError();
    }

    if (message === "ERROR - Saving Product Locked") {
      throw new Error("PRODUCT_LOCKED");
    }

    // Target person not found
    if (normalizedMessage.includes("buyer person not found")) {
      throw new BuyerPersonNotFoundError();
    }

    if (message === "ERROR - Saving Buyer Person Locked") {
      throw new Error("BUYER_PERSON_LOCKED");
    }

    if (normalizedMessage.includes("project not found")) {
      throw new ProjectNotFoundError();
    }

    if (normalizedMessage.includes("umbrella campaign not found")) {
      throw new UmbrellaCampaignNotFoundError();
    }

    if (normalizedMessage.includes("campaign not found")) {
      throw new CampaignNotFoundError();
    }

    if (normalizedMessage.includes("ad not found")) {
      throw new AdNotFoundError();
    }

    if (code === "BRAND00" || message === "ERROR - Brand name already exists")
      throw new Error("BRAND_ALREADY_EXISTS");
  }
}

export function handleSingUpFinishError(error: BaseApiResponse) {
  const errorMessage = error.response._data.message.text;
  switch (errorMessage) {
    case "Incorrect Status for Activation!":
      throw new SingUpFinishResponseError();
    case "Email Not Found!":
      throw new EmailNotFoundError();
    case "Incorrect Status for Resend Confirmation!":
      throw new EmailResendConfirmationError();
  }
}

export function handleResetPasswordError(error: BaseApiResponse) {
  const errorMessage = error.response._data.message.text;
  switch (errorMessage) {
    case "Should Init Reset Password Process!":
      throw new ResetPasswordError();
    case "Email is not Registered!":
      throw new EmailNotFoundError();
    case "Incorrect Validation Code!":
      throw new IncorrectValidationCodeError();
  }
}
