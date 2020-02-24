#!/usr/bin/env python
import subprocess
import json
import sys
import os
from rc_rmq import RCRMQ

task = 'ohpc_homedir'

# Instantiate rabbitmq object
confirm_rmq = RCRMQ({'exchange': 'Confirm'})
fanout_rmq = RCRMQ({'exchange': 'Create', 'exchange_type': 'fanout'})


def ohpc_homedir_create(ch, method, properties, body):
    msg = json.loads(body)
    print("Message received {}".format(msg))
    username = msg['username']
    success = False
    try:
        exist = os.path.isdir("/home/" + username)
        if not exist:
            subprocess.call(["sudo", "cp", "-r", "/etc/skel", "/home/" + username])
            print("Home directory for {} has been created".format(username))
        else:
            print("Home directory already exists, skip")
        success = True
    except:
        e = sys.exc_info()[0]
        print("Error: {}".format(e))

    ch.basic_ack(delivery_tag=method.delivery_tag)

    confirm_rmq.publish_msg({ 'routing_key': username, 'msg': { 'task': task, 'success': success }})

print("Start listening to queue '{}' in exchange 'Create'.".format(task))
fanout_rmq.start_consume({
    'queue': task,
    'cb': ohpc_homedir_create
})
