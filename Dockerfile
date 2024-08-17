# 阶段1: 构建应用程序
FROM python:3.12 AS base

# 1.1 复制必要文件
WORKDIR /app
# 复制当前文件到容器的/app目录下
COPY . .

# 1.2 安装python依赖
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install gunicorn \
    && pip install requests \
    && pip install pyjwt \
    && playwright install-deps \
    && playwright install 

EXPOSE 8080

CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8080", "main:app"]
