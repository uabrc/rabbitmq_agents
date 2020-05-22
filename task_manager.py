#!/usr/bin/env python
import sys
import json
import rc_util
from rc_rmq import RCRMQ
from datetime import datetime

task = 'task_manager'

args = rc_util.get_args()
logger = rc_util.get_logger(args)

record = {
    'uid': -1,
    'gid': -1,
    'email': '',
    'fullname': '',
    'last_update': datetime.now(),
    'request': {
        'create_account': None
    },
    'verify': {
        'git_commit': None,
        'dir_verify': None,
        'subscribe_mail_list': None
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
    done = success = msg['success']
    routing_key = ""

    if username not in tracking:
        current = tracking[username] = record.copy()
        current['delivery_tags'] = []
        current['uid'] = msg.get('uid', -1)
        current['gid'] = msg.get('gid', -1)
        current['email'] = msg.get('email', '')
        current['fullname'] = msg.get('fullname', '')

        logger.debug(f'Tracking user {username}')
    else:
        current = tracking[username]

    # Save the delivery tags for future use
    current['delivery_tags'].append(method.delivery_tag)

    try:
        if task_name in current['request']:
            current['request'][task_name] = success
            routing_key = 'verify.' + username
            done = success

            logger.debug(f'Request level task(s) done?{done}')

        elif task_name in current['verify']:
            current['verify'][task_name] = success
            routing_key = 'notify.' + username
            done = True
            for status in current['verify'].values():
                if status is not True:
                    done = False

            logger.debug(f'Verify level task(s) done?{done}')

        elif task_name in current['notify']:
            current['verify'][task_name] = success
            routing_key = 'complete.' + username
            done = success

            logger.debug(f'Notify level task(s) done?{done}')

    except Exception as exception:
        logger.error('', exc_info=True)

    if done:
        # Send trigger message
        rc_rmq.publish_msg({
            'routing_key': routing_key,
            'msg': {
                'username': username,
                'fullname': current['fullname'],
                'email': current['email'],
                'uid': current['uid'],
                'gid': current['gid'],
                'fullname': current['fullname']
            }
        })

        logger.debug(f"Trigger message '{routing_key}' sent")

        # Acknowledge all message from last level
        for tag in current['delivery_tags']:
            ch.basic_ack(tag)
        current['delivery_tags'] = []

        logger.debug('Previous level messages acknowledged')


logger.info(f'Start listening to queue: {task}')
rc_rmq.start_consume({
    'queue': task,
    'routing_key': "confirm.*",
    'cb': task_manager
})

logger.info('Disconnected')
rc_rmq.disconnect()
