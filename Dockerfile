FROM ghcr.io/anthropics/anthropic-quickstarts:computer-use-demo-latest

ENV ANTHROPIC_API_KEY=
ENV YOUR_API_KEY_HERE=
ENV DEBCONF_NOWARNINGS="yes"
ARG DEBIAN_FRONTEND=noninteractive

RUN sudo apt-get update && sudo apt-get install -y poppler-utils python3-pip vim && pip3 install openpyxl PyPDF2 pdfplumber yfinance pandas numpy pdf2image pytesseract 

COPY --chown=$USERNAME:$USERNAME index2.html $HOME/static_content/
# COPY --chown=$USERNAME:$USERNAME computer_use_demo/requirements.txt $HOME/computer_use_demo/requirements.txt

# docker build -t “webdev_rockylinux:Dockerfile” 
# Input: {'command': 'sudo apt-get install -y python3-pip && pip3 install openpyxl'}

# Input: {'command': 'view', 'path': '/tmp/statement.txt'}
# Input: {'command': 'pdftotext "/home/computeruse/t/JPM-2021/9771/20210127-statements-9771-.pdf" "/tmp/statement.txt"'}
# Tool Use: bash
#Input: {'command': 'python3 /tmp/update_excel.py'}
#Tool Use: bash
# Input: {'command': 'sudo apt-get update && sudo apt-get install -y poppler-utils'}