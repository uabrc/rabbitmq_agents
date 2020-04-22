#!/usr/bin/env python
import sys
import json
from rc_rmq import RCRMQ
from datetime import datetime

task = 'task_manager'

record = {
    'uid': -1,
    'gid': -1,
    'email': '',
    'last_update': datetime.now(),
    'request': {
        'uid_resolve': None
    },
    'create': {
        'join_list': None,
        'create_account': None
    },
    'verify': {
        'git_commit': None,
        'dir_verify': None
    },
    'notify': {
        'notify_user': None
    },
    'delivery_tags': None
}

# Currently tracking users
tracking = {}

# Instantiate rabbitmq object
rc_rmq = RCRMQ({'exchange': 'RegUsr', 'exchange_type': 'topic'})

def task_manager(ch, method, properties, body):
    msg = json.loads(body)
    username = method.routing_key.split('.')[1]
    task_name = msg['task']
    success = msg['success']

    if username not in tracking:
        current = tracking[username] = record.copy()
        current['delivery_tags'] = []
        current['uid'] = msg.get('uid', -1)
        current['gid'] = msg.get('gid', -1)
        current['email'] = msg.get('email', '')
    else:
        current = tracking[username]

    # save the delivery tags for future use
    current['delivery_tags'].append(method.delivery_tag)

    try:
    # Check each level
    # task timeout
    # failure agent(?
        if task_name in current['request']:
            current['request'][task_name] = success
            routing_key = 'create.' + username
            done = success

        elif task_name in current['create']:
            current['create'][task_name] = success
            routing_key = 'verify.' + username
            done = True
            for status in current['create'].values():
                if status is not True:
                    done = False

        elif task_name in current['verify']:
            current['verify'][task_name] = success
            routing_key = 'notify.' + username
            done = True
            for status in current['verify'].values():
                if status is not True:
                    done = False

        elif task_name in current['notify']:
            current['verify'][task_name] = success
            routing_key = 'complete.' + username
            done = success

    except:
        e = sys.exc_info()[0]
        print("[{}]: Error: {}".format(task, e))

    if done:
        # acknowledge all message from last level
        for tag in current['delivery_tags']:
            ch.basic_ack(tag)
        current['delivery_tags'] = []

        # send trigger message
        rc_rmq.publish_msg({
            'routing_key': routing_key,
            'msg': {
                'username': username,
                'email': current['email'],
                'uid': current['uid'],
                'gid': current['gid']
            }
        })


print("Start listening to queue: {}".format(task))
rc_rmq.start_consume({
    'queue': task,
    'routing_key': "confirm.*",
    'cb': task_manager
})

print("Disconnected")
rc_rmq.disconnect()
