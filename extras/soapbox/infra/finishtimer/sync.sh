#!/bin/bash

rsync -avz --delete rsync://192.168.100.10/derbynet/finishtimer/ /opt/derbynet/

systemctl restart finishtimer.service

