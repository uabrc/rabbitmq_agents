#!/usr/bin/env python3
import argparse
import dataset
import sys
import subprocess
import rabbit_config as rcfg
from datetime import datetime

parser = argparse.ArgumentParser()
parser.add_argument("-f", "--force", action="store_true", help="force update")
parser.add_argument(
    "--dry-run", action="store_true", help="enable dry run mode"
)
args = parser.parse_args()

default_state = "ok"

db = dataset.connect(f"sqlite:///prod_rmq_agents/{rcfg.db_path}/user_reg.db")
table = db["user_state"]

if table.__len__() > 0 and not args.force:
    print("table user_state not empty, abort.")
    sys.exit()

# Getting user list
users = subprocess.run(
    ["ls", "/data/user"], stdout=subprocess.PIPE, encoding="UTF-8"
).stdout.split()

# Update user_state table
for user in users:
    if args.dry_run:
        print(f"Table insert user: {user}, state: {default_state}")
    else:
        table.insert(
            {"username": user, "state": default_state, "date": datetime.now()}
        )
