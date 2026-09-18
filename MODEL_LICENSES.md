# Model and Dataset Licensing

EVIE's MIT License covers project-owned orchestration code, prompts, schemas, adapters, workflows, and documentation.

It does **not** automatically cover model weights, datasets, or hosted model services.

## Referenced model paths

EVIE configuration can target providers or runtimes such as:

- OpenAI models;
- Anthropic models;
- Ollama-served local models;
- local embedding models;
- ComfyUI image-generation models;
- optional Whisper-family transcription models.

No general MIT grant is made for those external models.

## User data and generated datasets

EVIE's Vault can ingest documents and generate indexes, artifacts, and derived datasets.

Those runtime outputs are intentionally excluded from the clean Commons source tree.

A user's right to redistribute generated datasets or fine-tuning material depends on the source content, provider terms, model license, and any other applicable rights.

## Release rule

A future public release that bundles model weights or datasets must document:

1. exact model/dataset name and version;
2. upstream source;
3. governing license or terms;
4. redistribution permission;
5. required attribution and notices.
