from locust import HttpUser, task, between
import random
import uuid
from datetime import datetime

class FraudDetectionUser(HttpUser):
    wait_time = between(0.001, 0.01)
    
    def on_start(self):
        self.client.post("/api/v1/auth/register", json={
            "email": f"load_{uuid.uuid4()}@test.com",
            "password": "testpass123",
            "country": "US"
        })
        
        response = self.client.post("/api/v1/auth/login", data={
            "username": f"load_{uuid.uuid4()}@test.com",
            "password": "testpass123"
        })
        self.token = response.json().get("access_token", "")
        self.user_id = str(uuid.uuid4())
    
    @task(10)
    def assess_transaction(self):
        headers = {"Authorization": f"Bearer {self.token}"}
        payload = {
            "transaction_id": f"TXN_{random.randint(1000000, 9999999)}",
            "user_id": self.user_id,
            "card_id": f"CARD_{random.randint(1000, 9999)}",
            "amount": random.uniform(10, 100000),
            "currency": "USD",
            "merchant_id": f"MERCH_{random.randint(1, 100)}",
            "merchant_category": random.choice(["grocery", "electronics", "travel"]),
            "country_code": random.choice(["US", "CA", "GB", "XX"]),
            "city": "Test City",
            "ip_address": f"192.168.{random.randint(1,255)}.{random.randint(1,255)}",
            "device_fingerprint": f"fp_{random.randint(1000,9999)}",
            "timestamp": datetime.now().isoformat()
        }
        
        with self.client.post(
            "/api/v1/transactions/assess",
            json=payload,
            headers=headers,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if data.get("processing_time_ms", 1000) > 100:
                    response.failure("Processing time > 100ms")
                else:
                    response.success()
            else:
                response.failure(f"Status code: {response.status_code}")
    
    @task(1)
    def get_transactions(self):
        headers = {"Authorization": f"Bearer {self.token}"}
        self.client.get("/api/v1/transactions/?page=1&limit=20", headers=headers)