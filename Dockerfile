FROM python:3.12-slim

# 容器内不生成 .pyc，输出不缓冲（日志能实时看到）
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# 先拷依赖清单并安装：requirements.txt 没变时这一层走缓存，构建很快
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 再拷代码：改代码只会重建这一层
COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
