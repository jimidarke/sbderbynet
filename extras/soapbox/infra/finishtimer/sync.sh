#!/bin/bash

sudo rsync -avz --delete rsync://192.168.100.10/derbynet/finishtimer/ /opt/derbynet/
sudo systemctl restart finishtimer.service