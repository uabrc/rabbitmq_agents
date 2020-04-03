#!/usr/bin/env python
import sh
import sys
import json
from rc_rmq import RCRMQ

task = 'git_commit'

# Instantiate rabbitmq object
rc_rmq = RCRMQ({'exchange': 'RegUsr', 'exchange_type': 'topic'})

repo_location = '~/git/rc-users'
cheaha_ldif = repo_location + '/users/cheaha-openldap.ldif'
cheaha_ldapsearch_ldif = repo_location + '/users/cheaha-openldap-ldapsearch.ldif'

git = sh.git.bake(repo_location)
slapcat = sh.Command('/cm/local/apps/openldap/sbin/slapcat')
ldapsearch = sh.Command('ldapsearch')

def git_commit(ch, method, properties, body):
    msg = json.loads(body)
    username = msg['username']
    ticketnum = msg.get('ticketnum', 'add-users-' + username.lower())
    DEBUG = msg.get('debug', False)
    success = False
    branch_name = 'issue-' + ticketnum

    try:

        git.checkout('master')
        git.pull()
        git.checkout('-b', branch_name)

        with open(cheaha_ldif, 'w') as ldif_f,\
            open(cheaha_ldapsearch_ldif, 'w') as ldapsearch_ldif_f:
            slapcat('-f', '/cm/local/apps/openldap/etc/slapd.conf', '-b', "'dc=cm,dc=cluster'", _out=ldif_f)
            ldapsearch('-LLL', '-x', '-h', 'cheaha-master02', '-b', "'dc=cm,dc=cluster'", _out=ldapsearch_ldif_f)

        git.diff()
        git.add(cheaha_ldif)
        git.add(cheaha_ldapsearch_ldif)
        git.commit(m="Added new cheaha user: " + username)
        git.push('origin', branch_name)
        git.checkout('master')
        time.sleep(60)
        git.pull()

        success = True
    except:
        e = sys.exc_info()[0]
        print("[{}]: Error: {}".format(task, e))

    # send confirm message
    rc_rmq.publish_msg({
        'routing_key': 'confirm.' + username,
        'msg': {
            'debug': DEBUG,
            'task': task,
            'success': success
        }
    })

    # Acknowledge message
    ch.basic_ack(delivery_tag=method.delivery_tag)


print("Start listening to queue: {}".format(task))
rc_rmq.start_consume({
    'queue': task,
    'routing_key': "git.*",
    'cb': git_commit
})

rc_rmq.disconnect()
