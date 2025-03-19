#!/bin/bash

export ANTHROPIC_API_KEY=
export YOUR_API_KEY_HERE=

docker build -t kensclaude . 

docker run -it  \
     -e ANTHROPIC_API_KEY=$YOUR_API_KEY_HERE \
  -v $HOME/.anthropic:/home/computeruse/.anthropic \
  -v $HOME/personal/juicyfruitstockoptions/output:/home/computeruse/output/ \
    -p 5900:5900 \
    -p 8501:8501 \
    -p 6080:6080 \
    -p 8080:8080 \
    -it kensclaude:latest


docker container ls 