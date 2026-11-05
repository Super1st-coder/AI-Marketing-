# Project Conventions

- Prefer Vue 3 Composition API with `<script setup lang="ts">` in components.
- Prefer camelCase for component props (e.g. `hasContext`, `maxWidth`) in definitions and template bindings.
- Reuse existing base components before adding new UI patterns.
- Prefer Tailwind utility classes for styling; follow existing utility patterns before adding custom CSS.
- Follow existing naming and folder conventions for components and composables.
- In `catch` blocks, always log the error with `console.error` before handling or re-throwing. Use a short, descriptive message when helpful (e.g. `console.error("Failed to load ads table:", error)`).
- Prefer Chrome DevTools MCP over the built-in Cursor browser for UI verification.
- Load the data a component needs to render with a top-level `await` in `<script setup>`, inside a `<Suspense>` boundary, and let errors reach the nearest `ErrorBoundary`. See the "Loading data with `Suspense` and top-level `await`" section in [project-conventions.mdc](.cursor/rules/project-conventions.mdc) for details.

## Scoped rules

This repo also has Cursor rules under [.cursor/rules/](.cursor/rules/) that only apply to specific file patterns. Read the relevant file before editing matching code:

- [form-fields.mdc](.cursor/rules/form-fields.mdc) — matches `src/components/forms/**/*.{vue,ts}`, `src/**/*Form*.vue`, `src/**/*Field*.vue`. How to reuse form field components (`Field*` vs `FieldBase*`, `FieldBaseControl` layout).
- [forms.mdc](.cursor/rules/forms.mdc) — no file pattern; apply whenever creating or editing a component with a vee-validate form, fields, or a submit action. Schemas with yup + `useFormWithErrorScrolling`, `isSubmitting` for loading and disabled fields, `type="button"` on non-submit buttons, and when to lock a modal while submitting vs. close it.
- [translation-text-updates.mdc](.cursor/rules/translation-text-updates.mdc) — applies whenever a request involves changing static text or i18n translations. Handling static text vs. translation keys, plurals, terminology consistency.
- [custom-icons.mdc](.cursor/rules/custom-icons.mdc) — matches `src/icons.ts`; also apply when adding or registering icons. Prefer Iconify/Tabler, then `addIcon` with inner paths, `currentColor`, and `fill="none"` on strokes.

These source files are the canonical rule content — if they change, re-read them rather than relying on this summary.
