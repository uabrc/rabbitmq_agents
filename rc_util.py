from rc_rmq import RCRMQ
import json

rc_rmq = RCRMQ({'exchange': 'RegUsr'})
tasks = {'ohpc_account': False, 'ohpc_homedir': False, 'ood_account': False, 'slurm_account': False}

def add_account(username, full='', reason=''):
  rc_rmq.publish_msg({
    'routing_key': 'ohpc',
    'msg': {
      "username": username,
      "fullname": full,
      "reason": reason
    }
  })

def worker(ch, method, properties, body):
    msg = json.loads(body)
    task = msg['username']
    print("get msg: {}".format(task))

    tasks[task] = True
    ch.basic_ack(delivery_tag=method.delivery_tag)

    # Check if all tasks are done
    done = True
    for key, status in tasks.items():
        if not status:
            done = False 
    if done:
        rc_rmq.stop_consume()
  
def consume(username, worker, debug=False):
    if debug:
        sleep(5)
    else:
        rc_rmq.start_consume({
            'queue': username,
            'cb': worker
        })
  
    return { 'success' : True }
