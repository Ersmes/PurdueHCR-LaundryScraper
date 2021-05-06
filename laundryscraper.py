#!/usr/bin/python3
import requests
from requests.exceptions import Timeout
from bs4 import BeautifulSoup
import json
import time
import os
import logging
from datetime import datetime

building_endpoints = {
    "N": "https://wpvitassuds01.boilerad.purdue.edu/washalertweb/washalertweb.aspx?location=ae0282a0-3196-46db-b66c-9a36b2420557",
    "S": "https://wpvitassuds01.boilerad.purdue.edu/washalertweb/washalertweb.aspx?location=7984d891-101f-4230-b263-d6ce46423b49"
}

building_switch = {
    "N": "north",
    "S": "south"
}

post_endpoints = {
    "test": "https://us-central1-purdue-hcr-test.cloudfunctions.net/laundry",
    "prod": "https://us-central1-hcr-points.cloudfunctions.net/laundry"
}

TIMEOUT_LENGTH = 30 # seconds

# setup logging to use file based on current datetime and INFO level
logging.basicConfig(filename=os.path.expanduser(f"~/Laundry Scraper/logs/{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}.log"), level=logging.INFO)

# Requests laundry machine status from ITaP servers and PUTs the result to the laundry endpoint
def update_machines():

    logging.info("Updating machine!")
    buildings = {}
    for building, url in building_endpoints.items():
        try:
            response = requests.get(url, timeout=TIMEOUT_LENGTH)
            print(f"Laundry Scraper: received response from {building_switch[building]}")
        except Timeout:
            print(f"Laundry Scraper: timeout - failed to access ITaP server for {building_switch[building]}")
            return
        
        machines = parse_building_machines(response.content, building)
        buildings.update(machines) 


    for endpoint, url in post_endpoints.items():
        with open(os.path.expanduser(f"~/Laundry Scraper/keys/raspberry-key-{endpoint}.json")) as file:
            auth = json.load(file)

        headers = {
            "Content-Type": "application/json",
            "Authorization": auth["key"]
        }
        
        try:
            response = requests.put(url, data=json.dumps(buildings), timeout=TIMEOUT_LENGTH, headers=headers)
            print(f"Laundry Scraper: posted to {endpoint} with status code {response.status_code}")
        except Timeout:
            print(f"Laundry Scraper: timeout - failed to post to {endpoint}")
            return

    
# Return a dictionary of machines given content and a building suffix for the machine
def parse_building_machines(content, building_suffix):
    machines = {}

    doc = BeautifulSoup(content, "html.parser")
    
    for tr in doc.table.tbody.select(".machine-info"):
        building = building_switch[building_suffix]
        machineId = tr.select(".name")[0].text + building_suffix
        status = tr.select(".status")[0].text
        type = tr.select(".type")[0].text
        time = int(tr.select(".time")[0].text.split()[0]) if tr.select(".time")[0].text.split() else 0

        machine = {
            "building": building,
            "machineId": machineId,
            "status": status,
            "type": type,
            "time": time
        }
        
        machines[machineId] = machine

    return machines

if __name__ == "__main__":
    while True:
        try:
            update_machines()
        except:
            print("Laundry Scraper: failed to update")

        time.sleep(60)
