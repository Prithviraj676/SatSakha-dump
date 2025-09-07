# from neo4j import GraphDatabase
#
# uri = "neo4j+ssc://29b1ed5d.databases.neo4j.io"
# username = "neo4j"
# password = "4XE9segNmzkPSutRz9-KETa6AIvx4oGc3J_Zn-MfUC8"
#
# driver = GraphDatabase.driver(uri, auth=(username, password))
#
# with driver.session(database="neo4j") as session:
#     print(session.run("RETURN 1 AS ok").single())




# from transformers import pipeline
#
# generator = pipeline("text-generation", model="distilgpt2")
# resp = generator("Hello, how are you?", max_new_tokens=50)
# print(resp[0]["generated_text"])



import requests

API_URL = "https://api-inference.huggingface.co/models/distilgpt2"
headers = {"Authorization": f"Bearer {HF_TOKEN}"}

data = {"inputs": "Hello, how are you?"}
response = requests.post(API_URL, headers=headers, json=data)

print(response.json())
