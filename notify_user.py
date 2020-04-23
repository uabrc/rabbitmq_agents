#!/usr/bin/env python
import sys
import json
import rc_util
import smtplib
from rc_rmq import RCRMQ
from jinja2 import Template
import mail

task = 'notify_user'

args = rc_util.get_args()
logger = rc_util.get_logger(args)

# Instantiate rabbitmq object
rc_rmq = RCRMQ({'exchange': 'RegUsr', 'exchange_type': 'topic'})

def send_email(to, opts=None):
    opts['server'] = opts.get('server', 'localhost')
    opts['from'] = opts.get('from', 'SUPPORT@LISTSERV.UAB.EDU')
    opts['from_alias'] = opts.get('from_alias', 'Research Computing Services')
    opts['subject'] = opts.get('subject', 'HPC New User Account')

    msg = f"""From: {opts['from_alias']} <{opts['from']}>
To: <{to}>
Subject: {opts['subject']}
{opts['body']}
"""
    if args.dry_run:
        print(msg)
        return

    smtp = smtplib.SMTP(opts['server'])
    if 'bcc' in opts:
        smtp.sendmail(opts['from'], [to, opts['bcc']], msg)
    else:
        smtp.sendmail(opts['from'], [to], msg)


# Email instruction to user
def notify_user(ch, method, properties, body):
    msg = json.loads(body)
    username = msg['username']
    user_email = msg['email']
    msg['task'] = task
    msg['success'] = False

    email_body = Template(mail.body).render(username=username)

    try:
        #Send email to user
        if args.dry_run:
            send_email('louistw@uab.edu', {
                'from': support_email,
                'from_alias': 'Research Computing Services',
                'subject': f'[TEST] New User Account on {hpcsrv}',
                'body': email_body
            })

        else:
            send_email(user_email, {
                'from': support_email,
                'from_alias': 'Research Computing Services',
                'subject': f'New User Account on {hpcsrv}',
                'body': email_body
            })

        msg['success'] = True
    except Exception as exception:
        logger.error('', exc_info=True)

    if not args.dry_run:
        # acknowledge the message
        ch.basic_ack(delivery_tag=method.delivery_tag)

        # send confirm message
        rc_rmq.publish_msg({
            'routing_key': 'confirm.' + username,
            'msg': msg
        })


if __name__ == "__main__":
    logger.info(f'Start listening to queue: {task}')
    rc_rmq.start_consume({
        'queue': task,
        'routing_key': "notify.*",
        'cb': notify_user
    })

    logger.info('Disconnected')
    rc_rmq.disconnect()
