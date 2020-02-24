#!/usr/bin/env python
import subprocess
import json
import sys
from rc_rmq import RCRMQ

task = 'ood_account'

# Instantiate rabbitmq object
confirm_rmq = RCRMQ({'exchange': 'Confirm'})
fanout_rmq = RCRMQ({'exchange': 'Create', 'exchange_type': 'fanout'})

def ood_account_create(ch, method, properties, body):
    msg = json.loads(body)
    print("Message received {}".format(msg))
    username = msg['username']
    user_uid = str(msg['uid'])
    user_gid = str(msg['gid'])
    success = False
    try:
        subprocess.call(["sudo", "groupadd", "-r", "-g", user_gid, username])
        subprocess.call(["sudo", "useradd", "-M", "-u", user_uid, "-g", user_gid, username])
        print("User {} has been added".format(username))
        success = True

    except:
        e = sys.exc_info()[0]
        print("Error: {}".format(e))
        print("Failed to create user")

    ch.basic_ack(delivery_tag=method.delivery_tag)
    confirm_rmq.publish_msg({ 'routing_key': username, 'msg': { 'task': task, 'success': success }})

print("Start listening to queue '{}' in exchange 'Create'.".format(task))
fanout_rmq.start_consume({
    'queue': task,
    'cb': ood_account_create
})
