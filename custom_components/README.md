# Custom components

Each subdirectory under `custom_components/` is a Home Assistant integration
(domain folder). Add a new integration like this:

```text
custom_components/
  my_new_integration/
    __init__.py
    manifest.json
    brand/
      icon.png
    README.md
    ...
```

## Rules

1. **One domain per folder.** Folder name must match `manifest.json` → `domain`.
2. **Ship a `manifest.json`** with at least `domain`, `name`, `documentation`,
   `issue_tracker`, `codeowners`, and `version`.
3. **Ship brand assets** at `brand/icon.png` (HACS / Home Assistant brands).
4. **Document the integration** in that folder’s `README.md`.
5. **Add or extend tests** under `tests/` (prefer `tests/<domain>/` as the set grows).

## HACS note

HACS custom repositories support **one integration per GitHub repository**.
This monorepo can hold multiple integrations for development and manual install,
but only one can be the HACS-managed entry (configured by the root `hacs.json`).

When a second integration needs its own HACS listing, publish it from a
dedicated public repository (or split it out of this monorepo).
