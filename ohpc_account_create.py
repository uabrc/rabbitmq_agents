#!/usr/bin/env python
import pika # python client
import sys
import rabbit_config as rcfg
import socket
import subprocess
import time
import json
from pwd import getpwnam
from rc_rmq import RCRMQ

task = "ohpc_account"

# Instantiate rabbitmq object
rc_rmq = RCRMQ({'exchange': 'RegUsr', 'exchange_type': 'topic'})

def ohpc_account_create(ch, method, properties, body):
    msg = json.loads(body)
    print("Message received {}".format(msg))
    username = msg['username']
    success = False
    try:
        subprocess.call(["sudo", "useradd", username])
        print("[{}]: User {} has been added".format(task, username))
        success = True
    except:
        print("Failed to create user")

    ch.basic_ack(delivery_tag=method.delivery_tag)
    msg['uid'] = getpwnam(username).pw_uid
    msg['gid'] = getpwnam(username).pw_gid

    # send confirm message
    rc_rmq.publish_msg({
        'routing_key': 'confirm.' + username,
        'msg': {
            'task': task,
            'success': success
        }
    })

    if success:
        # send create message to other agent
        rc_rmq.publish_msg({
            'routing_key': 'create.' + username,
            'msg': msg
        })

print("Start Listening to queue: {}".format(task))
rc_rmq.start_consume({
    'queue': task,
    'routing_key': 'request.*',
    'cb': ohpc_account_create
})
