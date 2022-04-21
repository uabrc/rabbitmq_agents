#!/bin/sh

username="$1"
path_to_db="/cm/shared/rabbitmq_agents/prod_rmq_agents/.agent_db/user_reg.db"

usage() {
  echo "Usage: $0 USERNAME"
}

if [[ "$EUID" -ne 0 ]]; then
  echo "This script must be run as root!"
  exit 1
fi

if [ -z "$username" ]; then
  usage
  exit 1
fi

if id "$username" &>/dev/null; then
  echo "Deleting user: ${username}"

  echo "Clean PUN process on loginnode"
  ssh login001 "/opt/ood/nginx_stage/sbin/nginx_stage nginx_clean --force --user $username"

  echo "Remove user via cmsh"
  cmsh -c "user use ${username}; remove -d; commit;"

  echo "Remove user from sqlite db users table"
  sqlite3 $path_to_db "delete from users where username=\"$username\""

  echo "Remove user from sqlite db user_state table"
  sqlite3 $path_to_db "delete from user_state where username=\"$username\""

  echo "Remove /data/user"
  rm -rf "/data/user/${username}"

  echo "Remove /data/scratch"
  rm -rf "/data/scratch/${username}"

else
  echo "user: ${username} not found."
  exit 1
fi
