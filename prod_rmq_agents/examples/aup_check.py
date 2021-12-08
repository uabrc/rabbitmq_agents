#!/usr/bin/env python
# An example cron job script that checks aup table daily
import dataset
import rc_util
from rc_rmq import RCRMQ
import rabbit_config as rcfg
from datetime import date, timedelta

# Instantiate rabbitmq object
rc_rmq = RCRMQ({"exchange": "RegUsr", "exchange_type": "topic"})

today = date.now()
expiration = today + timedelta(days=30)

args = rc_util.get_args()
logger = rc_util.get_logger(args)

db = dataset.connect(f"sqlite:///{rcfg.db_path}/user_reg.db")
table = db["user_policy"]

# Get all active entries
users = table.find(active=True)

# Check all entries
# Send renew reminder, with maybe a link to renewal page
for user in users:

    # Expires in 30 days
    if user["date"] == expiration:
        print(f'Email to user {user["username"]} sent.')

    # Expires today
    if user["date"] == today:
        print("Message to aup agent to deactivate the user")
        queuename = rc_util.encode_name(user["username"])
        message = dict(username=user["username"], aup=False)
        rc_rmq.publish_msg({"routing_key": "aup." + queuename, "msg": message})
