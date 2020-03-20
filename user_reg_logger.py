#!/usr/bin/env python
import json
import sys
import dataset
import logging
from rc_rmq import RCRMQ

# Define queue name 
task = 'reg_logger'

# Instantiate logging object 
logging.basicConfig(format='%(asctime)s[%(levelname)s] - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Instantiate rabbitmq object
reg_logger = RCRMQ({'exchange': 'RegUsr', 'exchange_type': 'topic'})

# Open registry table in DB
db = dataset.connect('sqlite:///reg_logger.db')
table = db['registry']

# Define registration logger callback
def log_registration(ch, method, properties, body):

    account_req = json.loads(body)
    table.insert(account_req)
    logger.info("logged account request for %s", account_req['username'])

    ch.basic_ack(delivery_tag=method.delivery_tag)

logger.info("Start listening to queue: {}".format(task))

# Start consuming messages from queue with callback function
reg_logger.start_consume({
  'queue': task,
  'routing_key': "create.*",
  'cb': log_registration
})

