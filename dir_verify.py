#!/usr/bin/env python
import sys
import json
import shutil
from pathlib import Path
from rc_rmq import RCRMQ

task = 'dir_verify'
dirs = ['/home', '/data/user', '/data/scratch']

# Instantiate rabbitmq object
rc_rmq = RCRMQ({'exchange': 'RegUsr', 'exchange_type': 'topic'})

def dir_verify(ch, method, properties, body):
    msg = json.loads(body)
    username = msg['username']
    success = False

    try:
        for d in dirs:
            path = Path(d) / msg['username']

            if not path.exists():
                # Make sure folder exists and with right permission
                path.mkdir(mode=0o700)

                # Make sure ownership is correct
                shutil.chown(path, msg['uid'], msg['gid'])
        success = True
    except:
        e = sys.exc_info()[0]
        print("[{}]: Error: {}".format(task, e))

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
    'routing_key': "verify.*",
    'cb': dir_verify
})

rc_rmq.disconnect()
