#!/usr/bin/env python
import json
import sys
import dataset
import logging
from rc_rmq import RCRMQ
from datetime import datetime

# Define queue name 
task = 'reg_logger'

# Instantiate rabbitmq object
reg_logger = RCRMQ({'exchange': 'RegUsr', 'exchange_type': 'topic'})

# Parse arguments
args = rc_util.get_args()

# Logger
logger = rc_util.get_logger()

# Open registry table in DB
db = dataset.connect('sqlite:///reg_logger.db')
table = db['registry']

# Define registration logger callback
def log_registration(ch, method, properties, body):

    account_req = json.loads(body)
    table.insert(account_req)
    account_req['req_time'] = datetime.now(),
    logger.info("logged account request for %s", account_req['username'])

    ch.basic_ack(delivery_tag=method.delivery_tag)

logger.info("Start listening to queue: {}".format(task))

# Start consuming messages from queue with callback function
reg_logger.start_consume({
  'queue': task,
  'routing_key': "create.*",
  'cb': log_registration
})

