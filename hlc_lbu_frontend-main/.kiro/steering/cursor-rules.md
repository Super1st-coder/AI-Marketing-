# Project Rules

This project's rules live in Cursor rule files under `.cursor/rules/`. They are the single source of truth: don't copy them into Kiro steering files. Read the rule file itself, and re-read it if it changes, rather than relying on the summaries below.

## Always apply

`project-conventions.mdc` applies to every task. Read `.cursor/rules/project-conventions.mdc` in full at the start of any task that reads or changes code, before making changes.

## Scoped rules

These only apply to some tasks. Before working on matching code, read the relevant file in full from `.cursor/rules/`:

- `form-fields.mdc` — when editing `src/components/forms/**/*.{vue,ts}`, `src/**/*Form*.vue` or `src/**/*Field*.vue`, or when adding or choosing a form field. How to reuse form field components (`Field*` vs `FieldBase*`, `FieldBaseControl` layout).
- `forms.mdc` — when creating or editing any component with a vee-validate form, fields or a submit action. Schemas with yup and `useFormWithErrorScrolling`, `isSubmitting` for loading and disabled fields, `type="button"` on non-submit buttons, and when to lock a modal while submitting vs. close it.
- `translation-text-updates.mdc` — whenever a request involves changing static text or i18n translations. Static text vs. translation keys, plurals, terminology consistency.
- `custom-icons.mdc` — when editing `src/icons.ts`, or when adding or registering icons. Prefer Iconify/Tabler, then `addIcon` with inner paths, `currentColor`, and `fill="none"` on strokes.

If a rule's front matter (`globs`, `description`) disagrees with this list, the rule file wins.
