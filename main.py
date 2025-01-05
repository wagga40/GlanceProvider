from fastapi import FastAPI
from fastapi.responses import HTMLResponse, Response

import requests
import jinja2
from datetime import datetime
import yaml

# Load configuration
def load_config():
    with open("config.yaml", "r") as file:
        return yaml.safe_load(file)

config = load_config()

app = FastAPI()

@app.get("/")
async def read_root():
    return {"message": "Take me home, country roads... to the place I belong..."}

# PiAlert for Glance 
# - type: extension
#   url: http://localhost:8000/pialert
#   cache: 1s
#   allow-potentially-dangerous-html: true

# PiAlert Parameters
PIALERT_PROTOCOL = config['pialert']['protocol']
PIALERT_HOST = config['pialert']['host']
PIALERT_PORT = config['pialert']['port']
PIALERT_API = config['pialert']['api_path']
PIALERT_URL = f"{PIALERT_PROTOCOL}://{PIALERT_HOST}:{PIALERT_PORT}{PIALERT_API}"
PIALERT_API_KEY = config['pialert']['api_key']
PIALERT_API_ENDPOINTS = config['pialert']['endpoints']

def get_pialert_api(PIALERT_URL, PIALERT_API_KEY, PIALERT_API_ENDPOINT):
    PIALERT_POST_DATA = {"api-key": PIALERT_API_KEY, "get": PIALERT_API_ENDPOINT}
    response = requests.post(PIALERT_URL, data=PIALERT_POST_DATA)
    return response.json()

def render_pialert_template(PIALERT_TEMPLATE_FILE, data):
    with open(PIALERT_TEMPLATE_FILE, "r") as file:
        template = jinja2.Template(file.read())
    return template.render(data=data)

@app.get("/pialert", response_class=HTMLResponse)
async def read_pialert(response: Response):
    response.headers["Widget-Title"] = "PiAlert"
    response.headers["Widget-Content-Type"] = "html"
    data = get_pialert_api(PIALERT_URL, PIALERT_API_KEY, PIALERT_API_ENDPOINTS[0])
    return render_pialert_template(config['pialert']['template_file'], data)

# Cronicle for Glance
# - type: extension
#   url: http://localhost:8000/cronicle
#   cache: 1s
#   allow-potentially-dangerous-html: true

# Cronicle Parameters
CRONICLE_PROTOCOL = config['cronicle']['protocol']
CRONICLE_HOST = config['cronicle']['host']
CRONICLE_PORT = config['cronicle']['port']
CRONICLE_API = config['cronicle']['api_path']
CRONICLE_API_VERSION = config['cronicle']['api_version']
CRONICLE_QUERY_LIMIT = config['cronicle']['query_limit']
CRONICLE_API_KEY = config['cronicle']['api_key']
CRONICLE_API_ENDPOINTS = config['cronicle']['endpoints']
CRONICLE_URL = f"{CRONICLE_PROTOCOL}://{CRONICLE_HOST}:{CRONICLE_PORT}{CRONICLE_API}<<endpoint>>/{CRONICLE_API_VERSION}?limit={CRONICLE_QUERY_LIMIT}"

def stats_from_cronicle_history(history):
    """
    Get stats from cronicle history
    Sample Event : 
        {'code': 0, 'rows': [{'id': 'xxxxx', 'code': 0, 'event': 'xxxxx', 'category': 'general', 'plugin': 'shellplug', 'hostname': 'XXXXX', 'time_start': 1735977600.065, 'elapsed': 0.6050000190734863, 'perf': '', 'cpu': {}, 'mem': {}, 'log_file_size': 635, 'action': 'job_complete', 'epoch': 1735977600, 'event_title': 'XXXXX', 'category_title': 'General', 'plugin_title': 'Shell Script'}]}
    """
    stats = {}
    for item in history["rows"]:
        event_title = item["event_title"]
        item_epoch = item["epoch"]

        if event_title not in stats:
            stats[event_title] = {
                "count": 1,
                "epoch": item_epoch,
                "last_run": datetime.fromtimestamp(item_epoch).strftime(config['cronicle']['date_format']),
                "error": 1 if "description" in item else 0,
            }
        else:
            stats[event_title]["count"] += 1
            if item_epoch > stats[event_title]["epoch"]:
                stats[event_title]["epoch"] = item_epoch
                stats[event_title]["last_run"] = datetime.fromtimestamp(item_epoch).strftime(config['cronicle']['date_format'])
            if "description" in item:
                stats[event_title]["error"] += 1

    return stats

def get_cronicle_api(CRONICLE_URL, CRONICLE_API_KEY, CRONICLE_API_ENDPOINT):
    url = CRONICLE_URL.replace("<<endpoint>>", CRONICLE_API_ENDPOINT)
    response = requests.post(url, headers={"X-API-KEY": CRONICLE_API_KEY})
    return response.json()

def render_cronicle_template(CRONICLE_TEMPLATE_FILE, data):
    with open(CRONICLE_TEMPLATE_FILE, "r") as file:
        template = jinja2.Template(file.read())
    return template.render(data=data)

@app.get("/cronicle", response_class=HTMLResponse)
async def read_cronicle(response: Response):
    response.headers["Widget-Title"] = "Cronicle"
    response.headers["Widget-Content-Type"] = "html"
    data = get_cronicle_api(CRONICLE_URL, CRONICLE_API_KEY, CRONICLE_API_ENDPOINTS[0])
    stats = stats_from_cronicle_history(data)
    return render_cronicle_template(config['cronicle']['template_file'], stats)