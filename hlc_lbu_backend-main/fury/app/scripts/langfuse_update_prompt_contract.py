"""Append the pipeline's prompt sections to the Langfuse prompts of the ads agents.

Sections (each one is skipped if its marker line is already in the prompt):
  CONTEXT SOURCE   — do not call get_adset_context; the context is injected in the input
  OUTPUT CONTRACT  — JSON types and variant_key (Diversity_Path)

The agents load `label="latest"`, and Langfuse moves `latest` to every new version, so
`--apply` takes effect in production on the next prompt-cache refresh (<= 60 s), for the
Legacy_Path and the Diversity_Path alike.

Usage (from fury/app, with LANGFUSE_* set for the target environment):
    PYTHONPATH=. env/bin/python scripts/langfuse_update_prompt_contract.py --prompt fury.image_prompter
    PYTHONPATH=. env/bin/python scripts/langfuse_update_prompt_contract.py --prompt fury.image_prompter --apply

Before publishing, the current text is saved to <prompt>_v<version>.txt so it can be
restored with:
    ... --prompt <prompt> --restore <prompt>_v<version>.txt --apply

Seed mode (only for the prompts in SEED_PROMPTS, i.e. fury.validador_adset): if the prompt
does not exist yet, publish the agent's fallback instruction as its first version (type
`text`, config={"model": FALLBACK_MODEL}); if it already exists, do nothing.
    PYTHONPATH=. env/bin/python scripts/langfuse_update_prompt_contract.py --prompt fury.validador_adset --seed
    PYTHONPATH=. env/bin/python scripts/langfuse_update_prompt_contract.py --prompt fury.validador_adset --seed --apply
"""
from __future__ import annotations

import argparse
import importlib
import pathlib
import sys

from core.config import settings

CONTEXT = ("agents.tools.injected_context", "CONTEXT_SOURCE_MARKER", "CONTEXT_SOURCE_SECTION")


def _contract(module: str) -> tuple[str, str, str]:
    return (module, "OUTPUT_CONTRACT_MARKER", "OUTPUT_CONTRACT_SECTION")


# Langfuse prompt name -> sections to append, in order: (module, marker attr, section attr)
PROMPTS: dict[str, list[tuple[str, str, str]]] = {
    "fury.estratega": [CONTEXT],
    "fury.copywriter": [CONTEXT, _contract("agents.copywriter_agent")],
    "fury.image_prompter": [CONTEXT, _contract("agents.image_prompter_agent")],
}

# Langfuse prompt name -> (module, instruction attr, model attr) published by --seed
SEED_PROMPTS: dict[str, tuple[str, str, str]] = {
    "fury.validador_adset": ("agents.validador_adset_agent", "_FALLBACK_INSTRUCTION", "FALLBACK_MODEL"),
}


def _client():
    from langfuse import Langfuse

    if not (settings.LANGFUSE_PUBLIC_KEY and settings.LANGFUSE_SECRET_KEY and settings.LANGFUSE_BASE_URL):
        sys.exit("LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY / LANGFUSE_BASE_URL are not set")
    return Langfuse(public_key=settings.LANGFUSE_PUBLIC_KEY, secret_key=settings.LANGFUSE_SECRET_KEY,
                    host=settings.LANGFUSE_BASE_URL)


def _sections(name: str) -> list[tuple[str, str]]:
    out = []
    for module, marker_attr, section_attr in PROMPTS[name]:
        mod = importlib.import_module(module)
        marker, section = getattr(mod, marker_attr), getattr(mod, section_attr)
        if "{{" in section:
            sys.exit(f"{module}.{section_attr} contains '{{{{' (mustache variable)")
        out.append((marker, section))
    return out


def _seed_content(name: str) -> tuple[str, str]:
    module, instruction_attr, model_attr = SEED_PROMPTS[name]
    mod = importlib.import_module(module)
    instruction, model = getattr(mod, instruction_attr), getattr(mod, model_attr)
    if "{{" in instruction:
        sys.exit(f"{module}.{instruction_attr} contains '{{{{' (mustache variable)")
    return instruction, model


def _seed(lf, name: str, apply: bool) -> int:
    """Publish the fallback instruction as version 1 of `name` if it does not exist yet."""
    from langfuse.api import NotFoundError

    try:
        current = lf.get_prompt(name, label="latest", cache_ttl_seconds=0)
    except NotFoundError:
        current = None
    if current is not None:
        print(f"{name} already exists (version={current.version} labels={current.labels} "
              f"host={settings.LANGFUSE_BASE_URL}): nothing to do.")
        return 0

    instruction, model = _seed_content(name)
    config = {"model": model}
    print(f"{name} does not exist on {settings.LANGFUSE_BASE_URL}: "
          f"seeding type=text config={config} chars={len(instruction)}")
    print(f"\n--- text to publish (first 2000 chars of {len(instruction)}) ---\n{instruction[:2000]}")
    if not apply:
        print("\nDry run: nothing published. Re-run with --apply to create the first version.")
        return 0

    created = lf.create_prompt(name=name, prompt=instruction, labels=[], type="text",
                               config=config, commit_message="Seed from fallback instruction")
    lf.flush()
    print(f"\nPublished {name} version={created.version} labels={created.labels}.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--prompt", choices=sorted(set(PROMPTS) | set(SEED_PROMPTS)), required=True)
    parser.add_argument("--apply", action="store_true", help="create the new version (default: dry run)")
    parser.add_argument("--restore", type=pathlib.Path, help="publish this saved text instead")
    parser.add_argument("--seed", action="store_true",
                        help=f"create the prompt from its fallback if missing (only {', '.join(sorted(SEED_PROMPTS))})")
    args = parser.parse_args(argv)
    name = args.prompt
    if args.seed:
        if name not in SEED_PROMPTS:
            parser.error(f"--seed only supports: {', '.join(sorted(SEED_PROMPTS))}")
        if args.restore:
            parser.error("--seed and --restore are mutually exclusive")
    elif name not in PROMPTS:
        parser.error(f"{name} can only be used with --seed")

    lf = _client()
    if args.seed:
        lf.clear_prompt_cache()
        return _seed(lf, name, args.apply)
    lf.clear_prompt_cache()
    current = lf.get_prompt(name, label="latest", cache_ttl_seconds=0)
    if getattr(current, "is_fallback", False):
        sys.exit(f"{name} could not be loaded from {settings.LANGFUSE_BASE_URL}")
    text = current.prompt
    if not isinstance(text, str):
        sys.exit(f"{name} is a chat prompt; this script only handles text prompts")
    print(f"{name}: version={current.version} labels={current.labels} "
          f"config={current.config} chars={len(text)} host={settings.LANGFUSE_BASE_URL}")

    if args.restore:
        new_text = args.restore.read_text()
        message = f"Restore from {args.restore.name}"
        print(f"\n--- text to publish (first 2000 chars of {len(new_text)}) ---\n{new_text[:2000]}")
    else:
        missing = [(m, s) for m, s in _sections(name) if m not in text]
        if not missing:
            print("All sections already present: nothing to do.")
            return 0
        new_text = text.rstrip() + "\n" + "".join(section for _, section in missing)
        message = "Add " + " + ".join(marker for marker, _ in missing)
        print(f"\n--- sections to append ({len(new_text) - len(text):+d} chars) ---")
        print(new_text[len(text.rstrip()):])
    if not args.apply:
        print("\nDry run: nothing published. Re-run with --apply to create the new version.")
        return 0

    backup = pathlib.Path(f"{name.replace('.', '_')}_v{current.version}.txt")
    backup.write_text(text)
    labels = [label for label in (current.labels or []) if label != "latest"]
    created = lf.create_prompt(name=name, prompt=new_text, labels=labels, type="text",
                               config=current.config, commit_message=message[:200])
    lf.flush()
    print(f"\nPublished {name} version={created.version} labels={created.labels}. "
          f"Previous text saved to {backup}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
