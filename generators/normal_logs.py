import pandas as pd
import random
from faker import Faker
from datetime import datetime

fake = Faker()

EVENT_TYPES = [
    "login_success",
    "file_download",
    "api_request",
    "logout"
]

def generate_normal_logs(num=500) :
    logs = []
    for _ in range(num) :
        log = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "source_ip" : fake.ipv4(),
            "event_type" : random.choice(EVENT_TYPES),
            "login_attempts" : random.randint(1,3),
            "bytes_transferred" : random.randint(100,5000),
            "label" : "normal"
        }

        logs.append(log)
    return pd.DataFrame(logs)

if __name__ == "__main__" :
    df = generate_normal_logs(3000)
    df.to_csv("c:\\Users\\18Shr\\Desktop\\Security System\\data\\normal_logs.csv",index=False)
    print("Normal logs generated and saved to ../data/normal_logs.csv")