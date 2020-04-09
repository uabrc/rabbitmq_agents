#!/usr/bin/env python
import os
import sh
import sys
import json
import argparse
from rc_rmq import RCRMQ

task = 'git_commit'

# Instantiate rabbitmq object
rc_rmq = RCRMQ({'exchange': 'RegUsr', 'exchange_type': 'topic'})

# Define some location
repo_location = os.path.expanduser('~/git/rc-users')
cheaha_ldif = repo_location + '/users/cheaha-openldap.ldif'
cheaha_ldapsearch_ldif = repo_location + '/users/cheaha-openldap-ldapsearch.ldif'
slapcat_bin = '/cm/local/apps/openldap/sbin/slapcat'
slapd_conf = '/cm/local/apps/openldap/etc/slapd.conf'

# Parse arguments
parser = argparse.ArgumentParser()
parser.add_argument('-v', '--verbose', action='store_true', help='verbose output')
parser.add_argument('-n', '--dry-run', action='store_true', help='enable dry run mode')
args = parser.parse_args()

git = sh.git.bake('-C', repo_location)
slapcat = sh.Command(slapcat_bin)
ldapsearch = sh.Command('ldapsearch')

def git_commit(ch, method, properties, body):
    msg = json.loads(body)
    username = msg['username']
    ticketnum = msg.get('ticketnum', 'add-users-' + username.lower())
    success = False
    branch_name = 'issue-' + ticketnum

    try:

        git.checkout('master')
        git.pull()
        git.checkout('-b', branch_name)

        with open(cheaha_ldif, 'w') as ldif_f,\
            open(cheaha_ldapsearch_ldif, 'w') as ldapsearch_ldif_f:
            slapcat('-f', slapd_conf, '-b', "'dc=cm,dc=cluster'", _out=ldif_f)
            ldapsearch('-LLL', '-x', '-h', 'ldapserver', '-b', "'dc=cm,dc=cluster'", _out=ldapsearch_ldif_f)

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

    # Send confirm message
    rc_rmq.publish_msg({
        'routing_key': 'confirm.' + username,
        'msg': {
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
