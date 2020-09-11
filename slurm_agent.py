#!/usr/bin/env python
import sys
import json
import subprocess
from rc_rmq import RCRMQ

task = 'slurm_account'

# Instantiate rabbitmq object
rc_rmq = RCRMQ({'exchange': 'RegUsr', 'exchange_type': 'topic'})

def slurm_account_create(ch, method, properties, body):
    msg = json.loads(body)
    print("Message received {}".format(msg))
    username = msg['username']
    success = False
    try:
        subprocess.call(["sudo", "sacctmgr", "add", "account", username, "-i",  "Descripition: Add user"])
        subprocess.call(["sudo", "sacctmgr", "add", "user", username, "account=" + username, "-i"])
        print("SLURM account for user {} has been added".format(username))
        success = True
    except:
        e = sys.exc_info()[0]
        print("[{}]: Error: {}".format(task, e))

    ch.basic_ack(delivery_tag=method.delivery_tag)

    # send confirm message
    rc_rmq.publish_msg({
        'routing_key': 'confirm.' + username,
        'msg': {
            'task': task,
            'success': success
        }
    })

print("Start listening to queue: {}".format(task))
rc_rmq.start_consume({
    'queue': task,
    'routing_key': "create.*",
    'cb': slurm_account_create
})
