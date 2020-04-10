#!/usr/bin/env python
import sys
import json
from os import popen
from rc_rmq import RCRMQ

task = 'bright_account'

# Instantiate rabbitmq object
rc_rmq = RCRMQ({'exchange': 'RegUsr', 'exchange_type': 'topic'})

# Define your callback function
def bright_account_create(ch, method, properties, body):
    # Retrieve message
    msg = json.loads(body)
    print("Received msg{}".format(msg))
    username = msg['username']
    uid = msg['uid']
    email = msg['email']
    fullname = msg['fullname']
    success = False
    try:
        # Bright command to create user
        cmd = '/cm/local/apps/cmd/bin/cmsh -c '
        cmd += f'"user; add {username}; set userid {uid}; set email {email}; set commonname \\"{fullname}\\"; '
        cmd += 'commit;"'

        #popen(cmd)
        print(cmd)
        success = True
    except:
        e = sys.exc_info()[0]
        print("[{}]: Error: {}".format(task, e))

    # Acknowledge message
    ch.basic_ack(delivery_tag=method.delivery_tag)

    # send confirm message
    rc_rmq.publish_msg({
        'routing_key': 'confirm.' + username,
        'msg': {
            'task': task,
            'success': success
        }
    })

    if success:
        # send create message to verify dir permissions agent
        rc_rmq.publish_msg({
            'routing_key': 'verify.' + username,
            'msg': msg
        })

print("Start listening to queue: {}".format(task))
rc_rmq.start_consume({
    'queue': task,
    'routing_key': "create.*",
    'cb': bright_account_create
})

rc_rmq.disconnect()
