# rabbitmq_agents

This repo keeps different rabbitmq agents that help in account creation on OHPC system.

It has 2 branches ```develop``` and ```production``` , that houses agents based on where they are launched

## Using RCRMQ class

- First, rename `rabbit_config.py.example` to `rabbit_config.py`

- Modify config file, at least the `Password` needs to be your own passwod

- In your code:

```
# import the class
from rc_rmq import RCRMQ

# instantiate an instance
rc_rmq = RCRMQ({'exchange': 'RegUsr'})

# publish a message to message queue
rc_rmq.publish_msg({
  'routing_key': 'your_key',
  'msg': {
    'type': 'warning',
    'content': 'this is warning'
  }
})

# to consume message from a queue
# you have to first define callback function
# with parameters: channel, method, properties, body
def callback_function(ch, method, properties, body):
  msg = json.loads(body)
  print("get msg: {}".format(msg['username')

  # this will stop the consumer
  rc_rmq.stop_consumer()

# start consume messagre from queue with callback function
rc_rmq.start_consume({
  'queue': 'queue_name',
  'cb': callback_function
})

```
