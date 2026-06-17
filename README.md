# Legal Avatar Assistant

Linebot backend for the "法務分身" contract review flow.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Fill in `LINE_CHANNEL_ACCESS_TOKEN` and `LINE_CHANNEL_SECRET` in `.env`.

For LLM contract analysis, also fill in:

```env
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4.1-mini
```

If `OPENAI_API_KEY` is empty, the backend falls back to the temporary fixed analysis response.

## Run

```powershell
cd app
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Line webhook URL:

```text
https://<ngrok-domain>/line/webhook
```

## Implemented Flow

- Text `合約審核` returns a carousel with:
  - 收文登記
  - 初審【業務/採購自審】
  - 法務審查
- Selecting one review type asks the user to upload a Word file.
- Uploaded files are downloaded to `storage/uploads`.
- The file path and review type are passed into `analyze_contract(file_path, review_type)`.
- `analyze_contract()` loads the matching md prompt, extracts `.docx/.docm` text with `python-docx`, and calls OpenAI.
- `.doc` is not parsed directly; save it as `.docx` before uploading.
