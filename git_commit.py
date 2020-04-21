#!/usr/bin/env python
import os
import sh
import sys
import json
import argparse
import logging
from rc_rmq import RCRMQ

task = 'git_commit'

# Instantiate rabbitmq object
rc_rmq = RCRMQ({'exchange': 'RegUsr', 'exchange_type': 'topic'})

# Define some location
repo_location = os.path.expanduser('~/git/rc-users')
users_dir = repo_location + '/users'
groups_dir = repo_location + '/groups'

# Default logger level
logger_lvl = logging.WARNING

# Parse arguments
parser = argparse.ArgumentParser()
parser.add_argument('-v', '--verbose', action='store_true', help='verbose output')
parser.add_argument('-n', '--dry-run', action='store_true', help='enable dry run mode')
args = parser.parse_args()

if args.verbose:
    logger_lvl = logging.DEBUG

if not args.dry_run:
    git = sh.git.bake('-C', repo_location)
    ldapsearch = sh.Command('ldapsearch')
else:
    logger_lvl = logging.INFO
    git = sh.echo.bake('git', '-C', repo_location)
    ldapsearch = sh.echo.bake('ldapsearch')

# Logger
logging.basicConfig(format='%(asctime)s [%(module)s] - %(message)s', level=logger_lvl)
logger = logging.getLogger(__name__)


def git_commit(ch, method, properties, body):
    msg = json.loads(body)
    username = msg['username']
    ticketnum = msg.get('ticketnum', 'add-users-' + username.lower())
    success = False
    branch_name = 'issue-' + ticketnum
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
            logger.debug(f"ldapsearch -LLL -x -h ldapserver -b 'dc=cm,dc=cluster' uid={username} > {user_ldif}")
            ldapsearch('-LLL', '-x', '-h', 'ldapserver', '-b', "'dc=cm,dc=cluster'", f"uid={username}", _out=ldif_u)
            logger.debug(f"ldapsearch -LLL -x -h ldapserver -b 'ou=Group,dc=cm,dc=cluster' cn={username} > {group_ldif}")
            ldapsearch('-LLL', '-x', '-h', 'ldapserver', '-b', "'ou=Group,dc=cm,dc=cluster'", f"cn={username}", _out=ldif_g)
        logger.info('user ldif files generated.')

        logger.debug('git diff')
        git.diff()
        logger.debug('git add %s', user_ldif)
        git.add(user_ldif)
        logger.debug('git add %s', group_ldif)
        git.add(group_ldif)
        logger.debug("git commit -m 'Added new cheaha user: %s'", branch_name)
        git.commit(m="Added new cheaha user: " + username)
        logger.debug('git checkout master')
        git.checkout('master')

        logger.debug('git merge %s --no-ff --no-edit', branch_name)
        git.merge(branch_name, '--no-ff', '--no-edit')
        logger.debug('git push origin master')
        git.push('origin', 'master')
        # merge with gitlab api

        logger.info('Added ldif files and committed to git repo')

        success = True
    except Exception as exception:
        logger.error('', exc_info=True)

    # Send confirm message
    logger.debug('rc_rmq.publish_msge()')
    rc_rmq.publish_msg({
        'routing_key': 'confirm.' + username,
        'msg': {
            'task': task,
            'success': success
        }
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
