"""Backward-compatibility shim.

The legacy polling worker has been replaced by `converter_service.py`. This
file is kept so existing Dockerfiles / process supervisors that invoke
`python3 converter.py` continue to work — it now simply starts the FastAPI
service defined in converter_service.py.
"""

import uvicorn

if __name__ == "__main__":
    uvicorn.run("converter_service:app", host="0.0.0.0", port=8080)
