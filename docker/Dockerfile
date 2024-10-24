FROM python:3.10-bullseye

# install zbar dependencyy
RUN apt-get -qq update
RUN apt-get -y -qq install zbar-tools

# temp copy requirements files to local repo to do pip3 install
COPY ../requirements.txt /requirements.txt
COPY ../tests/requirements.txt /tests-requirements.txt

WORKDIR /
RUN pip3 install -r requirements.txt
RUN pip3 install -r tests-requirements.txt

# clean up copied files
RUN rm /requirements.txt
RUN rm /tests-requirements.txt

# set working dir
WORKDIR /seedsigner