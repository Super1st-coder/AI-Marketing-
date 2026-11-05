import { kebabCase } from "lodash";

export function capitalizeFirstLetter(string: string) {
  return string[0].toUpperCase() + string.slice(1).toLowerCase();
}

/**
 * Derives display initials from a person's or account's full name.
 * Uses the first character of each whitespace-separated word, up to `maxInitials`.
 *
 * @example getUserInitials("Jane Doe Rivera") // "JD"
 * @example getUserInitials("Jane Doe Rivera", 1) // "J"
 */
export function getUserInitials(fullname: string, maxInitials = 2): string {
  const userNames = fullname.split(" ");

  return userNames
    .slice(0, maxInitials)
    .map((name) => name.charAt(0).toLocaleUpperCase())
    .join("");
}

export function extractStrings(obj: unknown, results?: string[]): string[] {
  let strings = results ?? [];

  if (typeof obj === "string" && obj != "") {
    strings.push(obj);
  }

  if (typeof obj === "object" && obj != null) {
    for (const key in obj) {
      extractStrings(obj[key as keyof typeof obj], strings);
    }
  }

  return strings;
}

export function snakeCaseToText(text: string): string {
  let strings = text.split("_");

  return capitalizeFirstLetter(strings.join(" "));
}

export function textToSnakeCase(text: string): string {
  let strings = text.trim().toLocaleLowerCase().split(" ");

  return strings.join("_").toLowerCase();
}

export function kebabCaseToText(text: string): string {
  let strings = text.split("-");

  return capitalizeFirstLetter(strings.join(" "));
}

export function anyCaseToText(text: string): string {
  return snakeCaseToText(kebabCaseToText(text));
}

/**
 * vue-i18n's default path resolver treats ", ', ., [ and ] as path syntax, so
 * a free-text value (e.g. a name coming from the backend) breaks $t/$te
 * lookups when interpolated as-is into a key path. Kebab-casing it produces a
 * safe, deterministic key segment (and matches this repo's i18n key style).
 */
export function toI18nKeySegment(text: string): string {
  return kebabCase(text);
}
