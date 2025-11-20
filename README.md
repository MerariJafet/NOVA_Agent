# NOVA Agent - Sprint1 MVP

Run the server:

```bash
pip install -r requirements.txt
python nova.py start
```

Endpoints:
- `GET /status`
- `POST /chat` with JSON `{ "message": "hola", "session_id": "abc" }`
