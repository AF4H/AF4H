#!/bin/bash

#TODO: Documentation / Comments in-line
#TODO: Error Handling

apt -y update --fix-missing
apt -y upgrade

apt -y install sudo vim less gpg fping dnsutils

mkdir /root/Downloads
