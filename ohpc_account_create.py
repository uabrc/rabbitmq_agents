#!/usr/bin/env python
import subprocess
import json
from pwd import getpwnam
from rc_rmq import RCRMQ

task = 'ohpc_account'

# Instantiate rabbitmq object
rc_rmq = RCRMQ({'exchange': 'Register'})
confirm_rmq = RCRMQ({'exchange': 'Confirm'})
fanout_rmq = RCRMQ({'exchange': 'Create', 'exchange_type': 'fanout'})

def ohpc_account_create(ch, method, properties, body):
    msg = json.loads(body)
    print("Message received {}".format(msg))
    username = msg['username']
    success = False
    try:
        subprocess.call(["sudo", "useradd", "-M", username])
        print("User {} has been added".format(username))
        success = True
    except:
        e = sys.exc_info()[0]
        print("Error: {}".format(e))

    ch.basic_ack(delivery_tag=method.delivery_tag)
    msg['uid'] = getpwnam(username).pw_uid
    msg['gid'] = getpwnam(username).pw_gid

    fanout_rmq.publish_msg({ 'routing_key': 'ohpc_create', 'msg': msg })
    confirm_rmq.publish_msg({ 'routing_key': username, 'msg': { 'task': task, 'success': success }})

print("Start listening to queue '{}' in exchange 'Register'.".format(task))
rc_rmq.start_consume({
    'queue': task,
    'cb': ohpc_account_create
})
