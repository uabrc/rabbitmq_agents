#!/usr/bin/env python
import sys
import json
import smtplib
from email.message import EmailMessage
from rc_rmq import RCRMQ

task = 'subscribe_mail_list'

# Instantiate rabbitmq object
rc_rmq = RCRMQ({'exchange': 'RegUsr', 'exchange_type': 'topic'})

# Define your callback function
def mail_list_subscription(ch, method, properties, body):

    # Retrieve message
    msg = json.loads(body)
    print("Received msg {}".format(msg))
    username = msg['username']
    fullname = msg['fullname']
    email = msg['email']

    mail_list_admin = 'admin@uab.edu' #change this during deploy
    mail_list = 'LISTSERV@LISTSERV.UAB.EDU'

    listserv_cmd = {}
    listserv_cmd['hpc_announce'] = f'QUIET ADD hpc-announce {email} {fullname}'
    listserv_cmd['hpc_users'] = f'QUIET ADD hpc-users {email} {fullname}'

    print("Adding user{} to mail list".format(username))
    success = False
    try:
        # Create a text/plain message
        email_msg = EmailMessage()

        email_msg['From'] = mail_list_admin
        email_msg['To'] = mail_list
        email_msg['Subject'] = ''

        # Create an smtp object and send email
        s = smtplib.SMTP('localhost')

        for each_cmd in listserv_cmd:
            email_msg.set_content(listserv_cmd[each_cmd])
            #s.send_message(email_msg)
            print(email_msg)

        s.quit()
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

print("Start listening to queue: {}".format(task))
rc_rmq.start_consume({
    'queue': task,      # Define your Queue name
    'routing_key': "create.*", # Define your routing key
    'cb': mail_list_subscription # Pass in callback function you just define
})

rc_rmq.disconnect()
