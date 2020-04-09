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
cheaha_ldif = repo_location + '/users/cheaha-openldap.ldif'
cheaha_ldapsearch_ldif = repo_location + '/users/cheaha-openldap-ldapsearch.ldif'
slapcat_bin = '/cm/local/apps/openldap/sbin/slapcat'
slapd_conf = '/cm/local/apps/openldap/etc/slapd.conf'

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
    slapcat = sh.Command(slapcat_bin)
    ldapsearch = sh.Command('ldapsearch')
else:
    logger_lvl = logging.INFO
    git = sh.echo.bake('git', '-C', repo_location)
    slapcat = sh.echo.bake(slapcat_bin)
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

        logger.debug("open(%s, 'w'), open(%s, 'w')", cheaha_ldif, cheaha_ldapsearch_ldif)
        with open(cheaha_ldif, 'w') as ldif_f,\
            open(cheaha_ldapsearch_ldif, 'w') as ldapsearch_ldif_f:
            logger.debug("%s -f %s -b 'dc=cm,dc=cluster' > %s", slapcat_bin, slapcat_config, cheaha_ldif)
            slapcat('-f', slapd_conf, '-b', "'dc=cm,dc=cluster'", _out=ldif_f)
            logger.debug("ldapsearch -LLL -x -h ldapserver -b 'dc=cm,dc=cluster' > %s", ldapsearch_ldif)
            ldapsearch('-LLL', '-x', '-h', 'ldapserver', '-b', "'dc=cm,dc=cluster'", _out=ldapsearch_ldif_f)
        logger.info('ldif files generated.')

        logger.debug('git diff')
        git.diff()
        logger.debug('git add %s', cheaha_ldif)
        git.add(cheaha_ldif)
        logger.debug('git add %s', cheaha_ldapsearch_ldif)
        git.add(cheaha_ldapsearch_ldif)
        logger.debug("git commit -m 'Added new cheaha user: %s'", branch_name)
        git.commit(m="Added new cheaha user: " + username)
        logger.debug('git checkout master')
        git.checkout('master')

        logger.debug('git merge %s --no-ff --no-edit', branch_name)
        git.merge(branch_name, '--no-ff', '--no-edit')
        logger.debug('git push origin master')
        git.push('origin', 'master')
        # merge with gitlab api

        logger.info('updated ldif files and committed to git repo')

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
