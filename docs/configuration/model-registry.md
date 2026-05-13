# Model Registry Configuration

AI Workbench MCP ships with a public default model registry at `configs/model_registry.yaml`. Public adopters can keep that file unchanged and add local routing preferences in `configs/model_registry.local.yaml`.

The local file is ignored by git. It is intended for provider names, model IDs, and runtime preferences that are specific to one machine or organization.

## Bring Your Own Models

Start from the example:

```bash
copy configs\model_registry.example.yaml configs\model_registry.local.yaml
```

Then edit the local file for your Goose and provider setup. At minimum, most users customize these public routing tiers:

```text
local_coding
cheap_cloud
mid_cloud
frontier
```

The structural tiers `deterministic_tool` and `human_review` should usually stay in the committed base registry. They represent command execution, validation, and manual approval gates rather than normal model-provider choices.

## Merge Rules

`configs/model_registry.local.yaml` merges into `configs/model_registry.yaml` before selection:

- dictionaries merge recursively
- lists replace the base list
- scalar values replace the base value

For example, this override replaces only the local coding model and keeps the base provider, uses, and fallback behavior:

```yaml
models:
  local_coding:
    model: your-local-coding-model
```

This override keeps the base frontier `reasoning_effort` and adds another parameter:

```yaml
models:
  frontier:
    parameters:
      max_output_tokens: 16000
```

This override replaces the full fallback list for one tier:

```yaml
models:
  local_coding:
    fallback_models:
      - your-backup-local-model
```

## Validation

After merging, every tier must define:

- `provider`
- `model`
- `use_for`

The model selector also validates that every selector reference resolves:

- `default_model`
- every `rules[].select`
- every key under `fallbacks`
- every tier listed inside each fallback list

Invalid local overrides fail during model selection with a clear error. Missing local override files are fine and preserve the committed defaults.

## Source Metadata

Each `model_selection.json` records minimal registry source metadata:

```json
{
  "model_registry": {
    "base_registry_path": "configs/model_registry.yaml",
    "local_override_loaded": true,
    "local_override_path": "configs/model_registry.local.yaml"
  }
}
```

Paths are repo-relative. The selection artifact does not record provider credentials, expanded local paths, or secrets.

## Scope

This is file-based override support only. It does not add interactive provider setup, event sinks, dashboards, eval harnesses, or automatic routing-policy mutation.
