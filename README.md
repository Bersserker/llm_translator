# Technical document translator

Python 3.12+ CLI for translating TXT, Markdown and DOCX through a local
OpenAI-compatible API. Uses LangChain prompt templates and LCEL chains.
There is no cloud endpoint configured by default.

## Setup and API diagnostics

Install [uv](https://docs.astral.sh/uv/) and start your local API server, then:

```bash
uv sync
uv run tech-translator test-api --config configs/default.yaml --model local-model
uv run tech-translator test-api --config configs/default.yaml --json
```

The diagnostic sends a short translation request. Model listing is optional;
successful generation determines the exit status. `model_available: null` means
listing could not be checked. Request timing covers generation, including retries.
Failures return exit code 1 with bounded diagnostics; API keys and server error
bodies are not printed.

## Translation

Place source documents in `input/` and save translations in `output/`.
Both folders are included in the project; their data files are ignored by Git.

```bash
uv run tech-translator translate input/manual.txt -o output/manual.ru.txt --config configs/default.yaml
uv run tech-translator translate input/manual.md -o output/manual.ru.md --config configs/default.yaml
uv run tech-translator translate input/manual.docx -o output/manual.ru.docx --config configs/default.yaml
```

Input and output must have the same format and different paths. Existing output
requires `--force`. UTF-8 text files retain line endings and blank lines. Markdown
retains source syntax, fenced/indented code, link destinations and HTML blocks;
HTML blocks are passed through without translating their contents. DOCX retains
formatting, tables, hyperlinks, images, headers and footers by translating text
nodes individually. Code styles are passed through. Text split across DOCX runs
is translated separately, which can reduce fluency. Embedded documents and image
text are not translated. Review terminology and accuracy before publishing.

Segments include glossary entries and the previous two source/translated segments
as context. Context is trimmed to fit a conservative UTF-8 byte token estimate.
If instructions and glossary alone exceed the budget, translation fails clearly.
For long translations, raise `max_tokens` or lower `chunk_size`.

## Configuration

Copy `configs/default.yaml`. Relative glossary paths resolve from the YAML file's
directory. A glossary is a YAML mapping of source terms to preferred translations;
terms are supplied to the model as instructions, not replaced mechanically.

All settings support environment overrides with `__` for nested fields:

```bash
export LLM__BASE_URL=http://localhost:1234/v1
export LLM__MODEL=your-loaded-model
export TRANSLATION__TARGET_LANGUAGE=ru
# Only if the server needs a key; otherwise the placeholder "local" is used:
export LLM_API_KEY=your-key
```

Environment settings override YAML; `--model` overrides both. Without `--config`,
built-in local defaults apply (no glossary). Credentials are accepted only from
`LLM_API_KEY`, not YAML. YAML loading uses safe parsing. `structured_output` can be
`auto` (try JSON schema, fall back to validated plain text for unsupported servers),
`on` (require structured output), or `off` (plain text). Auto mode remembers the
fallback for subsequent segments. Authentication, rate limits and server failures
do not trigger a second request through the fallback.

## Tests

```bash
uv run pytest -m 'not integration'
uv run pytest
# Explicit live test, after starting your server and configuring the model:
RUN_LLM_INTEGRATION=1 uv run pytest -m integration
```

The default suite uses mocked HTTP and LLM responses. The live test is skipped
unless explicitly enabled. Set `LLM_CONFIG` to select a different YAML file for it.

The package separates configuration, LLM client/translator/health, segmentation,
glossary loading, document parsers and atomic exporters. Structured output follows
the [LangChain ChatOpenAI API](https://reference.langchain.com/python/langchain-openai/chat_models/base/ChatOpenAI/with_structured_output).
