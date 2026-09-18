# Third-Party Notices

EVIE's MIT License applies to project-owned code and documentation in the clean Commons release.

Third-party libraries and services remain under their own licenses and terms.

## Declared Python dependencies

The current runtime requirements include projects such as:

- FastAPI and Uvicorn
- Pydantic / pydantic-settings
- python-multipart
- aiofiles
- APScheduler
- pypdf
- NumPy
- Rich
- orjson
- cryptography
- Requests
- Streamlit
- Pillow
- ReportLab
- python-docx
- pandas
- Jinja2

Optional integrations may add FAISS, LanceDB, PyArrow, Tesseract/pytesseract, Whisper, or faster-whisper.

The clean EVIE release does not relicense those projects. Before redistributing a vendored or bundled environment, verify the exact versions being shipped and preserve all notices required by those upstream licenses.

## External services and runtimes

EVIE can integrate with external systems including:

- Ollama
- OpenAI APIs
- Anthropic APIs
- ElevenLabs
- ComfyUI
- Gumroad
- YouTube
- ffmpeg
- Node.js-based rendering paths
- optional local desktop EXE tools

Those systems remain governed by their own licenses or service terms.

## No blanket relicensing

The presence of a dependency, service adapter, API client, workflow template, or configuration file in EVIE does not place the upstream project under EVIE's MIT License.
