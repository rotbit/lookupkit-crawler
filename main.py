import uvicorn
from routers.routers import app
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))


if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="debug")