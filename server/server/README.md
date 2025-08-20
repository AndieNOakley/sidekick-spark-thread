# Sidekick Spark — Server

## Quickstart (for when someone runs it on a laptop)
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
