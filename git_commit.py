#!/usr/bin/env python
import os
import sh
import sys
import json
import ldap
import rc_util
from rc_rmq import RCRMQ

task = 'git_commit'

# Instantiate rabbitmq object
rc_rmq = RCRMQ({'exchange': 'RegUsr', 'exchange_type': 'topic'})

# Define some location
repo_location = os.path.expanduser('~/git/rc-users')
users_dir = repo_location + '/users'
groups_dir = repo_location + '/groups'

args = rc_util.get_args()
logger = rc_util.get_logger(args)

if not args.dry_run:
    git = sh.git.bake('--git-dir', repo_location+'/.git', '--work-tree', repo_location)
    ldapsearch = sh.Command('ldapsearch')
else:
    git = sh.echo.bake('--git-dir', repo_location+'/.git', '--work-tree', repo_location)
    ldapsearch = sh.echo.bake('ldapsearch')

def git_commit(ch, method, properties, body):
    msg = json.loads(body)
    username = msg['username']
    msg['task'] = task
    msg['success'] = False
    branch_name = 'issue-add-users-' + username.lower() 
    user_ldif = users_dir + f'/{username}.ldif'
    group_ldif = groups_dir + f'/{username}.ldif'

    logger.info("Received: %s", msg)
    logger.debug("ticketnum: %s", ticketnum)
    logger.debug("branch_name: %s", branch_name)

    try:

        logger.debug('git checkout master')
        git.checkout('master')
        logger.debug('git pull')
        git.pull()
        logger.debug('git checkout -b %s', branch_name)
        git.checkout('-b', branch_name)

        logger.debug("open(%s, 'w'), open(%s, 'w')", user_ldif, group_ldif)
        with open(user_ldif, 'w') as ldif_u,\
            open(group_ldif, 'w') as ldif_g:
            logger.debug(f"ldapsearch -LLL -x -H ldaps://ldapserver -b 'dc=cm,dc=cluster' uid={username} > {user_ldif}")
            ldapsearch('-LLL', '-x', '-H', 'ldaps://ldapserver', '-b', "dc=cm,dc=cluster", f"uid={username}", _out=ldif_u)
            logger.debug(f"ldapsearch -LLL -x -H ldapserver -b 'ou=Group,dc=cm,dc=cluster' cn={username} > {group_ldif}")
            ldapsearch('-LLL', '-x', '-H', 'ldaps://ldapserver', '-b', "ou=Group,dc=cm,dc=cluster", f"cn={username}", _out=ldif_g)
        logger.info('user ldif files generated.')

        logger.debug('git add %s', user_ldif)
        git.add(user_ldif)
        logger.debug('git add %s', group_ldif)
        git.add(group_ldif)
        logger.debug("git commit -m 'Added new cheaha user: %s'", username)
        git.commit(m="Added new cheaha user: " + username)
        logger.debug('git checkout master')
        git.checkout('master')

        logger.debug('git merge %s --no-ff --no-edit', branch_name)
        git.merge(branch_name, '--no-ff', '--no-edit')
        logger.debug('git push origin master')
        git.push('origin', 'master')
        # merge with gitlab api

        logger.info('Added ldif files and committed to git repo')

        msg['success'] = True
    except Exception as exception:
        logger.error('', exc_info=True)

    # Send confirm message
    logger.debug('rc_rmq.publish_msge()')
    rc_rmq.publish_msg({
        'routing_key': 'confirm.' + username,
        'msg': msg
    })
    logger.info('confirmation sent')

    # Acknowledge message
    logger.debug('ch.basic_ack()')
    ch.basic_ack(delivery_tag=method.delivery_tag)


logger.info("Start listening to queue: %s", task)
rc_rmq.start_consume({
    'queue': task,
    'routing_key': "verify.*",
    'cb': git_commit
})

logger.info("Disconnected")
rc_rmq.disconnect()
