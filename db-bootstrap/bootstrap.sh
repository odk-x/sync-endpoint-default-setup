#!/bin/sh -u

set -o pipefail

echo "ODK-X Sync-Endpoint Database Bootstrap Script"

if [ ${DB_BOOTSTRAP} != true ]; then
    echo 'DB_BOOTSTRAP not set to true'
    echo 'Database bootstrap cancelled'
    exit 0
fi;

MAX_TRY=30

# sleep 10 seconds to wait for db service to be created
sleep 10

STACK_NAME=""
COUNTER=0
while [ -z "${STACK_NAME}" ]
do
	echo "Searching for Stack Name ..."
	sleep 5
	STACK_NAME=$(docker ps -f "ID=${HOSTNAME}" --format '{{ .Names }}' | grep -oE '^[^_]*')
	COUNTER=`expr $COUNTER + 1`
	if [ $COUNTER -gt $MAX_TRY ] ; then
	   break;
	fi
done
echo "Stack Name: ${STACK_NAME}"


DB_VAR=""
COUNTER=0
while [ -z "${DB_VAR}" ]
do
	echo "Searching for DB Type ..."
	sleep 5
	DB_VAR=$(docker service inspect -f "{{if eq \"${STACK_NAME}_db\" .Spec.Name}}{{.Spec.TaskTemplate.ContainerSpec.Image}}{{end}}" $(docker service ls -q) | grep -oE '^[^:]*')
	COUNTER=`expr $COUNTER + 1`
	if [ $COUNTER -gt $MAX_TRY ] ; then
	   break;
	fi
done
echo "DB Type: ${DB_VAR}"

DB_CONTAINER_ID=""
COUNTER=0
while [ -z "${DB_CONTAINER_ID}" ]
do
	echo "Searching for DB Container ID..."
	sleep 5
	DB_CONTAINER_ID=$(docker ps -f "volume=${STACK_NAME}_db-vol" --format '{{.ID}}')
	COUNTER=`expr $COUNTER + 1`
	if [ $COUNTER -gt $MAX_TRY ] ; then
	   break;
	fi
done
echo "Container ID: ${DB_CONTAINER_ID}"

# try to establish tcp connection with db, each connection timesout after 1 second 
WAIT_CMD="while ! nc -w 1 db \${DB_PORT} < /dev/null; do echo 'waiting'; sleep 1; done"

case ${DB_VAR} in
    postgres)
        echo "postgres db detected"
        DB_PORT=5432
        eval ${WAIT_CMD}
        docker exec ${DB_CONTAINER_ID} psql \
            -c 'CREATE USER odk WITH PASSWORD '\''odk'\'';' \
            -c 'CREATE SCHEMA odk_sync AUTHORIZATION odk;' \
            -c 'GRANT ALL PRIVILEGES ON SCHEMA odk_sync TO odk;' \
            -U ${POSTGRES_USER} -d ${POSTGRES_DB}
        ;;
    mysql)
        echo "mysql db detected"
        DB_PORT=3306
        eval ${WAIT_CMD}
        docker exec ${DB_CONTAINER_ID} mysql \
            -e 'CREATE DATABASE odk_sync;' \
            -e 'GRANT USAGE ON *.* TO odk@% IDENTIFIED BY '\''odk'\'';' \
            -e 'GRANT ALL PRIVILEGES ON odk_sync.* TO odk@%;' \
            -p"${MYSQL_ROOT_PASSWORD}"
        ;;
    sqlserver)
        echo "sqlserver db detected"
        ;;
    *)
        echo "Error"
        echo "${DB_VAR} not supported"
        ;;
esac

echo "Done"

echo "Checking Sync endpoint"

# Wait 5 seconds for a 200 from Sync
timeout 5 sh -c 'while ! echo -ne "GET / HTTP/1.1\nHost: sync\n\n" | nc -w 1 sync 8080 | grep -q "HTTP/1.1 200"; do echo '\''waiting for Sync'\''; sleep 1; done'

if [ $? -eq 143 ]; then
    echo "Timeout"
    echo "Killing Sync endpoint"
    # let Docker restart the container
    docker kill $(docker ps -f "label=com.docker.swarm.service.name=${STACK_NAME}_sync" --format '{{.ID}}')
fi;

echo "Exit"

exit 0
