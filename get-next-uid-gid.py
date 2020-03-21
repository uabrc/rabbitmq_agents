#!/usr/bin/env python
import sys
import json
import ldap
from os import popen
from rc_rmq import RCRMQ

task = 'get_next_uid_gid'

# Instantiate rabbitmq object
rc_rmq = RCRMQ({'exchange': 'RegUsr', 'exchange_type': 'topic'})

#Check if the username already exists via LDAP
def user_exists(username):
    try:
        con = ldap.initialize('ldap://ldapserver')
        ldap_base = "dc=cm,dc=cluster"
        query = "(uid={})".format(username)
        result = con.search_s(ldap_base, ldap.SCOPE_SUBTREE, query)
        return result
    except:
        e = sys.exc_info()[0]
        print("[{}]: Error: {}".format(task, e))

# Define your callback function
def get_next_uid_gid(ch, method, properties, body):

    # Retrieve message
    msg = json.loads(body)
    print("Message received {}".format(msg))
    username = msg['username']
    success = False

    # Determine next available UID
    try:
        if user_exists(username):
            print("The user, {} already exists".format(username))
            sys.exit(1)

        cmd_uid = "/usr/bin/getent passwd | \
            awk -F: '($3>10000) && ($3<20000) && ($3>maxuid) { maxuid=$3; } END { print maxuid+1; }'"

        msg['uid'] = popen(cmd_uid).read().rstrip()

        cmd_gid = "/usr/bin/getent group | \
            awk -F: '($3>10000) && ($3<20000) && ($3>maxgid) { maxgid=$3; } END { print maxgid+1; }'"

        msg['gid'] = popen(cmd_gid).read().rstrip()
        success = True
    except:
        e = sys.exc_info()[0]
        print("[{}]: Error: {}".format(task, e))

    # Acknowledge message
    ch.basic_ack(delivery_tag=method.delivery_tag)

    # Send confirm message
    rc_rmq.publish_msg({
        'routing_key': 'confirm.' + username,
        'msg': {
            'task': task,
            'success': success
        }
    })

    if success:
        # Send create message to BrightCM agent
        rc_rmq.publish_msg({
            'routing_key': 'create.' + username,
            'msg': msg
        })

print("Start listening to queue: {}".format(task))
rc_rmq.start_consume({
    'queue': task,
    'routing_key': "request.*",
    'cb': get_next_uid_gid
})

rc_rmq.disconnect()
