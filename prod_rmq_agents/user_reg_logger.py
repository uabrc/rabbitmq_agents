#!/usr/bin/env python
import json
import sys
import dataset
import rc_util
from rc_rmq import RCRMQ
from datetime import datetime

# Define queue name
task = "reg_logger"

# Instantiate rabbitmq object
rc_rmq = RCRMQ({"exchange": "RegUsr", "exchange_type": "topic"})

# Parse arguments
args = rc_util.get_args()

# Logger
logger = rc_util.get_logger()

# Open registry table in DB
db = dataset.connect("sqlite:///.agent_db/reg_logger.db")
account_req_table = db["registry"]

# Define registration logger callback
def log_registration(ch, method, properties, body):

    account_req = json.loads(body)
    account_req["req_time"] = datetime.now()
    account_req_table.insert(account_req)
    logger.info("logged account request for %s", account_req["username"])

    ch.basic_ack(delivery_tag=method.delivery_tag)


logger.info("Start listening to queue: {}".format(task))

# Start consuming messages from queue with callback function
rc_rmq.start_consume(
    {"queue": task, "routing_key": "request.*", "cb": log_registration}
)
