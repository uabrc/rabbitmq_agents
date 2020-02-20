# rabbitmq_agents

This repo keeps different rabbitmq agents that help in account creation on OHPC system.

It has 2 branches ```develop``` and ```production``` , that house agents based on where they are launched

## Using RCRMQ class

- First, rename `rabbitmq_config.py.example` to `rabbitmq_config.py`

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
```
