from rc_rmq import RCRMQ
import json

rc_rmq = RCRMQ({'exchange': 'Register'})
confirm_rmq = RCRMQ({'exchange': 'Confirm'})
tasks = {'ohpc_account': False, 'ohpc_homedir': False, 'ood_account': False, 'slurm_account': False}

def add_account(username, full='', reason=''):
  rc_rmq.publish_msg({
    'routing_key': 'ohpc_account',
    'msg': {
      "username": username,
      "fullname": full,
      "reason": reason
    }
  })

def worker(ch, method, properties, body):
    msg = json.loads(body)
    task = msg['task']
    print("get msg: {}".format(task))
    tasks[task] = msg['success']

    # Check if all tasks are done
    done = True
    for key, status in tasks.items():
        if not status:
            print("{} is not done yet.".format(key))
            done = False 
    if done:
        confirm_rmq.stop_consume()
        confirm_rmq.delete_queue()
  
def consume(username, callback, debug=False):
    if debug:
        sleep(5)
    else:
        confirm_rmq.start_consume({
            'queue': username,
            'cb': callback
        })
  
    return { 'success' : True }
