#!/usr/bin/env python
import shutil
import json
import sys
import os
from rc_rmq import RCRMQ

task = 'ohpc_homedir'

# Instantiate rabbitmq object
confirm_rmq = RCRMQ({'exchange': 'Confirm'})
fanout_rmq = RCRMQ({'exchange': 'Create', 'exchange_type': 'fanout'})

def dir_walk(path):
    ''' Get All Directories & Files'''
    yield path
    for dir_path, dir_names, file_names in os.walk(path):

        # Directories
        for dir_name in dir_names:
            yield os.path.join(dir_path, dir_name)

        # Files
        for file_name in file_names:
            yield os.path.join(dir_path, file_name)

def ohpc_dir_create(ch, method, properties, body):
    msg = json.loads(body)
    print("Message received {}".format(msg))
    username = msg['username']
    success = False
    try:
        exist = os.path.isdir(msg['destination'])
        if not exist:
            if('template' in msg):
                shutil.copytree(msg['template'], msg['destination'])
            else:
                os.mkdir(msg['destination'])
            #os.chown(msg['destination'], msg['uid'], msg['gid'])
            for recursive_path in dir_walk(msg['destination']):
                os.chown(recursive_path , msg['uid'], msg['gid'])
        else:
            print("Home directory already exists, skip")
        success = True
    except:
        e = sys.exc_info()[0]
        print("Error: {}".format(e))

    ch.basic_ack(delivery_tag=method.delivery_tag)

    confirm_rmq.publish_msg({ 'routing_key': username, 'msg': { 'task': task, 'success': success }})

print("Start listening to queue '{}' in exchange 'Create'.".format(task))
fanout_rmq.start_consume({
    'queue': task,
    'cb': ohpc_dir_create
})
