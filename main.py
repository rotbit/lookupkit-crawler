from multiprocessing import Process
import uvicorn
from routers.routers import app
import sys
import os

from utils.schedule import start_sync_scheduler

sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))


if __name__ == '__main__':
    # 启动定时任务
    Process(target=start_sync_scheduler).start()
    
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="debug")