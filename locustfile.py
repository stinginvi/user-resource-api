"""压测脚本。

用法：
    locust -f locustfile.py --host http://127.0.0.1:8000 \
        --headless -u 50 -r 10 -t 30s --only-summary

流量模型：
    70% 查用户详情（走缓存）
    20% 用户列表
    10% 健康检查
"""

from locust import HttpUser, between, task


class ApiUser(HttpUser):
    wait_time = between(0.05, 0.2)

    @task(7)
    def get_user(self):
        self.client.get("/users/1", name="/users/{id}")

    @task(2)
    def list_users(self):
        self.client.get("/users?limit=10", name="/users?limit=10")

    @task(1)
    def health(self):
        self.client.get("/health", name="/health")
