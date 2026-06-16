import pandas as pd
import json
import ollama
import ast
import time 

def generate_attack_logs(total=500,batch = 50) :
    all_logs = []
    num_batches = total // batch
    for i in range(num_batches) :
        print(f"Generating batch {i+1} of {num_batches}...")
        start = time.time()
        prompt = f"""
            Generate {batch} cybersecurity attack logs in JSON format.

            Each log must contain these exact fields:
            - timestamp in the format YYYY-MM-DD HH:MM:SS
            - source_ip (realistic IPv4 address)
            - event_type (one of: brute_force, port_scan, data_exfiltration)
            - login_attempts (integer)
            - bytes_transferred (integer)
            - label with value "attack"

            Rules:
            - timestamps must be different
            - timestamps should be randomly distributed over the last 2 years
            - Values must appear random and realistic. 
            - Avoid repeating patterns in timestamps, IP addresses, or bytes_transferred.
            
            Return ONLY a valid JSON array.
            Do not include markdown, explanations, comments, or text before or after the JSON.
            """

        response = ollama.chat(
            model = "llama3.1",
            messages = [{"role":"user","content":prompt}]
        )

        response_text = response['message']['content'].strip()
        start_idx = response_text.find('[')
        end_idx = response_text.rfind(']') + 1

        if start_idx == -1 or end_idx == -1 :
            raise ValueError(f"No JSON array found in the LLM output {response_text[:100]}.....")
        json_text = response_text[start_idx:end_idx]

        try :
            batch_logs = json.loads(json_text)
        except :
            batch_logs = ast.literal_eval(json_text)

        if isinstance(batch_logs,dict) :
            batch_logs=[batch_logs]
        
        all_logs.extend(batch_logs)
        end = time.time()
        print(f"Batch {i+1} finished in {end-start:.2f} seconds")
        
    df = pd.DataFrame(all_logs)
    return df

if __name__ == "__main__" :
    df = generate_attack_logs(total=500,batch=25)
    df.to_csv("data/attack_logs.csv",index=False)
    print(f"Attack logs generated:{df.shape[0]} logs saved to data/attack_logs.csv")
