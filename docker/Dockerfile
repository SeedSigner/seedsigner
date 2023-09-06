FROM python:3.10-bullseye

# install zbar dependencyy
RUN apt-get -qq update
RUN apt-get -y -qq install zbar-tools

# temp add/copy seedsigner local repo to do pip3 install
ADD . /seedsigner
WORKDIR /seedsigner

#COPY ../requirements.txt /requirements.txt
#COPY ../tests/requirements.txt /tests-requirements.txt

RUN pip3 install -r requirements.txt
RUN pip3 install -r tests/requirements.txt
RUN pip3 install -e .

# clean up copied files
WORKDIR /
RUN rm -r /seedsigner

# set working dir
WORKDIR /seedsigner