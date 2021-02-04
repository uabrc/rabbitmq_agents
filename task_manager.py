#!/usr/bin/env python
import sys
import json
import rc_util
import smtplib
from rc_rmq import RCRMQ
from datetime import datetime
import mail_config as mail_cfg

task = 'task_manager'

args = rc_util.get_args()
logger = rc_util.get_logger(args)

record = {
    'uid': -1,
    'gid': -1,
    'email': '',
    'reason': '',
    'fullname': '',
    'last_update': datetime.now(),
    'errmsg': [],
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

def notify_admin(username, user_record):
    message = mail_cfg.UserReportHead
    message += f"""
        User Creation Report for user {username}
        uid: {user_record["uid"]}, gid: {user_record["gid"]}
        Tasks:
            'create_account':      {user_record["request"]["create_account"]}
            'git_commit':          {user_record["verify"]["git_commit"]}
            'dir_verify':          {user_record["verify"]["dir_verify"]}
            'subscribe_mail_list': {user_record["verify"]["subscribe_mail_list"]}
            'notify_user':         {user_record["notify"]["notify_user"]}
    """
    if user_record['errmsg']:
        message += """

        Error(s):
        """
        for msg in user_record['errmsg']:
            message += msg + "\n"

    if args.dry_run:
        logger.info(f'smtp = smtplib.SMTP({mail_cfg.Server})')
        logger.info(f'smtp.sendmail({mail_cfg.Sender}, {mail_cfg.Admin_email}, message)')
        logger.info(message)

    else:
        smtp = smtplib.SMTP(mail_cfg.Server)
        smtp.sendmail(mail_cfg.Sender, receivers, message)

        logger.debug(f'User report sent to: {mail_cfg.Admin_email}')


def task_manager(ch, method, properties, body):
    msg = json.loads(body)
    username = method.routing_key.split('.')[1]
    task_name = msg['task']
    success = msg['success']
    send = completed = terminated = False
    routing_key = ""

    if username not in tracking:
        current = tracking[username] = record.copy()
        current['delivery_tags'] = []
        current['uid'] = msg.get('uid', -1)
        current['gid'] = msg.get('gid', -1)
        current['email'] = msg.get('email', '')
        current['reason'] = msg.get('reason', '')
        current['fullname'] = msg.get('fullname', '')

        logger.debug(f'Tracking user {username}')
    else:
        current = tracking[username]

    # Save the delivery tags for future use
    current['delivery_tags'].append(method.delivery_tag)

    # Save error message if the task was failed
    if not success:
        errmsg = msg.get('errmsg', '')
        if errmsg:
            current['errmsg'].append(f"{task_name}: {errmsg}")

    try:
        if task_name in current['request']:
            current['request'][task_name] = success
            routing_key = 'verify.' + username

            # Terminate the process if failed
            if not success:
                terminated = True

            send = True
            logger.debug(f'Request level {task_name}? {success}')

        elif task_name in current['verify']:
            current['verify'][task_name] = success
            routing_key = 'notify.' + username
            send = True
            for status in current['verify'].values():
                if status is not True:
                    send = False

            # Terminate the process if dir_verify failed
            if task_name == "dir_verify":
                if not success:
                    terminated = True

            logger.debug(f'Verify level {task_name}? {success}')

        elif task_name in current['notify']:
            current['notify'][task_name] = success
            routing_key = 'complete.' + username
            send = True

            # The whole creation process has completed
            completed = True

            logger.debug(f'Notify level {task_name}? {success}')

    except Exception as exception:
        logger.error('', exc_info=True)

    if send:
        # Send trigger message
        rc_rmq.publish_msg({
            'routing_key': routing_key,
            'msg': {
                'username': username,
                'fullname': current['fullname'],
                'email': current['email'],
                'uid': current['uid'],
                'gid': current['gid'],
                'reason': current['reason']
            }
        })

        logger.debug(f"Trigger message '{routing_key}' sent")

        # Acknowledge all message from last level
        for tag in current['delivery_tags']:
            ch.basic_ack(tag)
        current['delivery_tags'] = []

        logger.debug('Previous level messages acknowledged')

    # Send report to admin after all tasks confirmed or terminated
    if completed or terminated:
        notify_admin(username, current)


logger.info(f'Start listening to queue: {task}')
rc_rmq.start_consume({
    'queue': task,
    'routing_key': "confirm.*",
    'cb': task_manager
})

logger.info('Disconnected')
rc_rmq.disconnect()
