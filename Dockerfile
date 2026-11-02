# 演示用镜像：单进程 runserver + SQLite。
# 生产部署请换成 gunicorn/uwsgi + PostgreSQL + 独立静态文件服务。
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# 先装依赖，利用镜像层缓存
COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

# 收集静态文件（Django admin 等）
RUN python manage.py collectstatic --noinput --verbosity 0 || true

EXPOSE 8000

# .env 中的 DJANGO_SECRET_KEY / 各类 API Key 通过 compose 的 env_file 注入
CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py runserver 0.0.0.0:8000"]
