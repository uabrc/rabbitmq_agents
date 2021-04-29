#!/usr/bin/env python
import os
import sys
import json
import shutil
import rc_util
from pathlib import Path
from rc_rmq import RCRMQ
import rabbit_config as rcfg

task = 'dir_verify'
dirs = rcfg.User_dirs

args = rc_util.get_args()
logger = rc_util.get_logger(args)

# Instantiate rabbitmq object
rc_rmq = RCRMQ({'exchange': 'RegUsr', 'exchange_type': 'topic'})

def dir_verify(ch, method, properties, body):
    msg = json.loads(body)
    username = msg['username']
    msg['task'] = task
    msg['success'] = True

    missing_dirs = []

    try:
        for d in dirs:
            path = Path(d) / msg['username']

            if args.dry_run:
                logger.info(f'Checking dirs: {path}')

            else:
                if not path.exists():
                    # check if dirs exist and record any missing dirs
                    missing_dirs.append(path)
                    msg['success'] = False
                    msg['errmsg'] = f"Error: missing dirs {missing_dirs}"
                    logger.info(f'{path} does not exist')
                else:
                    # check existing dirs for correct ownership and permissions
                    status = os.stat(path)
                    mask = oct(status.st_mode)[-3:]
                    uid = str(status.st_uid)
                    gid = str(status.st_gid)
                    if mask!='700' or uid!=msg['uid'] or gid!=msg['gid']:
                        msg['success'] = False
                        msg['errmsg'] = f"Error: dir {path} permissions or ownership are wrong"

    except Exception as exception:
        msg['success'] = False
        msg['errmsg'] = "Exception raised, check the logs for stack trace"
        logger.error('', exc_info=True)

    # send confirm message
    rc_rmq.publish_msg(
        {"routing_key": "confirm." + msg["queuename"], "msg": msg}
    )

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
