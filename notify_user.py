#!/usr/bin/env python
import sys
import json
import smtplib
from rc_rmq import RCRMQ

task = 'notify_user'

# Some variable for email
DEBUG = False
passwd_str = '<Your BlazerID/XIAS Password>'
hpcsrv = 'cheaha.rc.uab.edu'
# idmap_srv = 'cheaha.rc.uab.edu'
# idmap = '/home/useradmin/.useridmap'
signature = 'UAB IT Research Computing'
my_email = 'mhanby@uab.edu'
info_url = 'http://docs.uabgrid.uab.edu/wiki/Cheaha'
quickstart_url = 'https://docs.uabgrid.uab.edu/wiki/Cheaha_Quick_Start'
# matlab_url = 'http://docs.uabgrid.uab.edu/wiki/MatLab_DCS'
helpdesk_url = 'https://uabprod.service-now.com/ess_portal/' # Once we get a real helpdesk, change to URL instead of email
support_email = 'askit@uab.edu'
loginwiki_url = 'http://docs.uabgrid.uab.edu/wiki/Cheaha_GettingStarted#Login'
queuewiki_url = 'https://docs.uabgrid.uab.edu/wiki/Slurm'
# Old Mailman HPC mailing list
# hpclist_url = 'http://lists.it.uab.edu/mailman/listinfo/hpcusers'
# hpclist_email = 'hpcusers-subscribe@lists.it.uab.edu'
# New Sympa based mailing lists
mailinglist_admin = 'mhanby@uab.edu'
mailinglist_email = 'LISTSERV@LISTSERV.UAB.EDU'
#mailinglist_email = 'sympa@vo.uabgrid.uab.edu'
#hpcannounce_url = 'http://vo.uabgrid.uab.edu/sympa/info/hpc-announce'
hpcannounce_email = 'HPC-ANNOUNCE@LISTSERV.UAB.EDU'
#hpcusers_url = 'http://vo.uabgrid.uab.edu/sympa/info/hpc-users'
hpcusers_email = 'HPC-USERS@LISTSERV.UAB.EDU'
ticket_url = 'https://gitlab.rc.uab.edu/mhanby/rc-users/issues'


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

    email_body = f"""
Your account has been set up on {hpcsrv}

====================================
User ID:  {username}
Password: {passwd_str}
====================================

Important: You are responsible for backing up your files on Cheaha! The following storage locations are available:
* $HOME - /home/$USER - 20G quota per user
* $USER_DATA - /data/user/$USER - 5TB quota per user
* $USER_SCRATCH - /data/scratch/$USER - 500TB shared amongst ALL users

DO NOT compute out of $HOME, all computation must be done on the fast storage that is $USER_DATA and $USER_SCRATCH

Please read the information available on our Wiki pages, especially the Cheaha Quick Start:

Cheaha Quick Start
 {quickstart_url}
Additional Cluster Login Instructions
 {loginwiki_url}
Job Queuing information and examples
 {queuewiki_url}
General information about Cheaha
 {info_url}

If you encounter a problem or have any questions, please send a detailed email to: {support_email}

You have been subscribed to two important email lists:
 * hpc-announce : Important HPC related announcements are sent via this list, please read
     all emails from {hpcannounce_email}
 * hpc-users : This email list can be used by all HPC users to discuss anything
     related to our HPC environment by sending email to {hpcusers_email}

 Regards,

{signature}
{helpdesk_url}
"""

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
