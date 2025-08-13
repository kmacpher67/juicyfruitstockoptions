#!/bin/bash

echo "docker build run script"
# run it danno, @TO-DO add prod vs dev stsart modes. 

pip install -r requirements.txt

now="$(date)"
echo "docker build run script for smstext maps $now"
# npm run start

## check of OS keys are published for usage (not using GOOGLE maps just for reference )
echo "must have export GOOGLE_MAP_KEY = $GOOGLE_MAP_KEY"
if [ -z ${GOOGLE_MAP_KEY} ]; 
    then 
    echo "GOOGLE_MAP_KEY is unset, export GOOGLE_MAP_KEY= "
    exit 1;
fi

# root@kubnodejs:/votersmap# 
docker container ls 
# CONTAINER ID        IMAGE                   COMMAND                  CREATED             STATUS              PORTS                      NAMES
# 55e4c87446ca        votersmap_vuejswebapp   "docker-entrypoint.s…"   27 hours ago        Up 27 hours         0.0.0.0:8080->8080/tcp     votersmap_vuejswebapp_1
# b9b8b241fefc        votersmap_smstest       "docker-entrypoint.s…"   27 hours ago        Up 23 hours         0.0.0.0:3000->3000/tcp     votersmap_smstest_1
# 60b77ab92e50        mongo:4.4.3             "docker-entrypoint.s…"   27 hours ago        Up 27 hours         0.0.0.0:27017->27017/tcp   mongo

sleep 2

export b=$(basename "$PWD")"stocklive_app"
echo $b
export containerid=$(docker inspect --format="{{.Id}}" $b)
echo $containerid
# Check to see if the app is already running if so, try restarting it
if [ -z "$containerid" ]; 
    then 
    echo "container $vm_container doesn't exist starting ....:   docker-compose up --build -d  ";
    docker-compose up --build -d 
fi



# sleep 1
# start or build a js app (future TODO)
# echo "cd usermap npm run build vuejs app"
# cd usermap
# npm run build:dev
# cd ..
# sed -i "s/GOOGLE_MAPS_API_KEY_REPLACE/$GOOGLE_MAPS_API_KEY/g" usermap/dist/js/*
# sed -i "s/GOOGLE_MAPS_API_KEY_REPLACE/$GOOGLE_MAPS_API_KEY/g" usermap/dist/*
# sleep 1

echo "starting docker container restart"
export b=$(basename "$PWD")"stocklive_app"
echo $b
export containerid=$(docker inspect --format="{{.Id}}" $b)
echo $containerid
docker container restart $containerid
sleep 1
docker logs $containerid
docker container ls
sleep 16
docker logs $containerid
docker