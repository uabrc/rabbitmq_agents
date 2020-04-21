#!/usr/bin/env python
import sys
import json
import smtplib
from rc_rmq import RCRMQ
from jinja2 import Template
import mail

task = 'notify_user'

DEBUG = False

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
    if DEBUG:
        print(msg)
        return

    smtp = smtplib.SMTP(opts['server'])
    if 'bcc' in opts:
        smtp.sendmail(opts['from'], [to, opts['bcc']], messagge)
    else:
        smtp.sendmail(opts['from'], [to], messagge)


# Email instruction to user
def notify_user(ch, method, properties, body):
    msg = json.loads(body)
    username = msg['username']
    user_email = msg['email']
    success = False

    email_body = Template(mail.body).render(username=username)

    try:
        #Send email to user
        if DEBUG:
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

        success = True
    except:
        e = sys.exc_info()[0]
        print("[{}]: Error: {}".format(task, e))

    if not DEBUG:
        # acknowledge the message
        ch.basic_ack(delivery_tag=method.delivery_tag)

        # send confirm message
        rc_rmq.publish_msg({
            'routing_key': 'confirm.' + username,
            'msg': {
                'task': task,
                'success': success
            }
        })


if __name__ == "__main__":
    print("Start listening to queue: {}".format(task))
    rc_rmq.start_consume({
        'queue': task,
        'routing_key': "notify.*",
        'cb': notify_user
    })

    rc_rmq.disconnect()
