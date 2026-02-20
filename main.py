import os

import uvicorn

from application.app import app

port = os.getenv("API_PORT", 8000)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=port)
