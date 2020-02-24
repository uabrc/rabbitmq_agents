#!/usr/bin/env python
import subprocess
import json
import sys
from rc_rmq import RCRMQ

task = 'slurm_account'

# Instantiate rabbitmq object
confirm_rmq = RCRMQ({'exchange': 'Confirm'})
fanout_rmq = RCRMQ({'exchange': 'Create', 'exchange_type': 'fanout'})

def slurm_account_create(ch, method, properties, body):
    msg = json.loads(body)
    print("Message received {}".format(msg))
    username = msg['username']
    success = False
    try:
        subprocess.call(["sudo", "sacctmgr", "add", "account", username, "-i",  "Descripition: Add user"])
        subprocess.call(["sudo", "sacctmgr", "add", "user", username, "account="+username, "-i"])
        print("SLURM account for user {} has been added".format(username))
        success = True
    except:
        e = sys.exc_info()[0]
        print("Error: {}".format(e))

    ch.basic_ack(delivery_tag=method.delivery_tag)

    confirm_rmq.publish_msg({ 'routing_key': username, 'msg': { 'task': task, 'success': success }})

print("Start listening to queue '{}' in exchange 'Create'.".format(task))
fanout_rmq.start_consume({
    'queue': task,
    'cb': slurm_account_create
})
