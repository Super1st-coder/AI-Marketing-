import { test, expect } from "@playwright/test";
import { faker } from "@faker-js/faker";

test.describe("Login", () => {
  test.beforeEach(async ({ page }) => {
    await page.context().clearCookies();
    await page.goto("/");
  });

  test("Debe realizar un login exitoso", async ({ page }) => {
    await page.fill('[data-testid="username"]', "ramon@hiluca.com");
    await page.fill('[data-testid="password"]', "admin1234");
    await page.click('[data-testid="rememberMe"]');

    await page.click('[data-testid="submit"]');

    await expect(page).toHaveURL("/brands");

    console.log("✅ El test de login E2E fue exitoso.");
  });
});

test.describe("Recuperar contraseña", () => {
  test.beforeEach(async ({ page }) => {
    await page.context().clearCookies();
    await page.goto("/");
  });

  test("Debe enviar recuperar contraseña", async ({ page }) => {
    await page.click('[data-testid="forgotPasswordLink"]');

    await page.fill(
      '[data-testid="forgotPasswordInputEmail"]',
      "ramon@hiluca.com",
    );

    await page.click('[data-testid="forgotPasswordSubmitBtn"]');

    await expect(page).toHaveURL("/");

    console.log("✅ El test de recuperar contraseña E2E fue exitoso.");
  });
});

test.describe("Registro", () => {
  test.beforeEach(async ({ page }) => {
    await page.context().clearCookies();
    await page.goto("/register");
  });

  test("Debe habilitar el botón solo con datos válidos", async ({ page }) => {
    const submit = page.getByTestId("createAccountSubmit");
    await expect(submit).toBeDisabled();

    await page.getByTestId("createAccountNames").fill("Juan");
    await page.getByTestId("createAccountLastNames").fill("Pérez");
    await page.getByTestId("createAccountEmail").fill("juan.perez@example.com");
    await page.getByTestId("createAccountTerms").check();
    await page.getByTestId("createAccountPassword").fill("GFV7#nq@n^7w0%L7");

    await expect(submit).toBeEnabled();

    console.log(
      "✅ El test de habilitar el botón de registro solo con datos válidos ha sido exitoso.",
    );
  });

  // test("Debe realizar un registro exitoso", async ({ page }) => {
  //   const firstName = faker.person.firstName();
  //   const lastName = faker.person.lastName();
  //   const email = faker.internet.email({ firstName, lastName });
  //
  //   const submit = page.getByTestId("createAccountSubmit");
  //   await expect(submit).toBeDisabled();
  //
  //   await page.getByTestId("createAccountNames").fill(firstName);
  //   await page.getByTestId("createAccountLastNames").fill(lastName);
  //   await page.getByTestId("createAccountEmail").fill(email);
  //   await page.getByTestId("createAccountTerms").check();
  //   await page.getByTestId("createAccountPassword").fill("GFV7#nq@n^7w0%L7");
  //
  //   await expect(submit).toBeEnabled();
  //   await submit.click();
  //
  //   await expect(page.getByText("Verify your email")).toBeVisible();
  //   await expect(page.getByText(email)).toBeVisible();
  //
  //   console.log(`✅ Registro exitoso con el usuario ${email}`);
  // });
});
