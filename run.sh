#!/bin/sh
url="http://www.hackndo.com:5667/mongo/users/"
RESPONSE=$(curl -sL $url -w "%{http_code}" -o /dev/null)
if [ $RESPONSE -eq "200" ]
then
    echo $RESPONSE
else
    screen -X -S tweets quit
    screen -S tweets -d -m /usr/bin/python /home/betezed/tweetsapi/microTweet.py
    date +"%y-%m-%d %T Restart" >> /home/betezed/tweetsapi/log.txt
fi
