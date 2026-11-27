"""Start the app: `python run.py` (or the Run button in VS Code on this file).

Opens on http://localhost:8000. If frontend/dist exists (npm run build), the app is served
from here too. To open it from a phone on the same Wi-Fi: set STUDYBUDDY_HOST=0.0.0.0.
"""

import os
import sys

import uvicorn
from dotenv import load_dotenv

if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    load_dotenv(os.path.join(here, ".env"))
    os.chdir(here)
    sys.path.insert(0, here)
    host = os.getenv("STUDYBUDDY_HOST", "127.0.0.1")
    uvicorn.run("app.main:app", host=host, port=8000, reload=True)
