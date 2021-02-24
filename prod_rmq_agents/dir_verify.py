#!/usr/bin/env python
import sys
import json
import shutil
import rc_util
from pathlib import Path
from rc_rmq import RCRMQ

task = 'dir_verify'
dirs = ['/home', '/data/user', '/data/scratch']

args = rc_util.get_args()
logger = rc_util.get_logger(args)

# Instantiate rabbitmq object
rc_rmq = RCRMQ({'exchange': 'RegUsr', 'exchange_type': 'topic'})

def dir_verify(ch, method, properties, body):
    msg = json.loads(body)
    username = msg['username']
    msg['task'] = task
    msg['success'] = False

    try:
        for d in dirs:
            path = Path(d) / msg['username']

            if args.dry_run:
                logger.info(f'Checking dirs: {path}')

            else:
                if not path.exists():
                    # Make sure folder exists and with right permission
                    path.mkdir(mode=0o700, parents=True, exist_ok=True)

                    # Make sure ownership is correct
                    shutil.chown(path, int(msg['uid']), int(msg['gid']))

                    logger.debug(f'{path} created')

        msg['success'] = True

    except Exception as exception:
        logger.error('', exc_info=True)

    # send confirm message
    rc_rmq.publish_msg({
        'routing_key': 'confirm.' + username,
        'msg': msg
    })

    logger.debug(f'User {username} confirmation sent')

    ch.basic_ack(delivery_tag=method.delivery_tag)


logger.info(f'Start listening to queue: {task}')
rc_rmq.start_consume({
    'queue': task,
    'routing_key': "verify.*",
    'cb': dir_verify
})

logger.info('Disconnected')
rc_rmq.disconnect()
