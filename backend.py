import json
import os

DATA_FILE = 'tasks.json'

def save_tasks(tasks):
    with open(DATA_FILE, 'w') as file:
        json.dump(tasks, file)

def load_tasks():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as file:
            return json.load(file)
    return []
