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

  echo "cmsh -c 'user use ${username}; remove -d; commit;'"
  cmsh -c "user use ${username}; remove -d; commit;"

  echo "sqlite3  $path_to_db \"delete from users where username=\"$username\""
  sqlite3 $path_to_db "delete from users where username=\"$username\""

  echo "rm -r /data/user/${username}"
  rm -rf "/data/user/${username}"

  echo "rm -r /data/scratch/${username}"
  rm -rf "/data/scratch/${username}"

else
  echo "user: ${username} not found."
  exit 1
fi
