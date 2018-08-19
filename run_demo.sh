#!/bin/bash

clear
printf "\nStarting Sensu clientless demo...\n\n"
docker-compose up -d 2>&1 >/dev/null
printf "\nContainers are starting up. Point a browser at http://localhost:3000/clients and wait for the three clients to show up.\n\n"
read -p "Hit enter once you see them..."
clear
printf "\nAlso, head over to http://localhost:8500/ui/sensu-clientless-test/services/web-hello-world to see the three nodes."
printf "\n\nThe list of nodes in Sensu is fed from the list of nodes you see in Consul (we will prove that in a bit).\n\n"
read -p "Hit enter once you have checked out the list of hosts in Sensu and Consul..."
clear
printf "In Uchiwa (http://localhost:3000), \n\n"
printf "    --> click on the web-node-03 client\n"
printf "    --> click on the http_check check\n"
printf "    --> view the check results...\n"
printf "        including the environment, handler, and pdkey k/v pairs.\n\n"
read -p "Hit enter to see how they got there..."
clear
printf "\nHere is the Consul service config - which lives on the webservers themselves, not anywhere in Sensu - from which"
printf "\nthose k/v pairs originated:\n\n"
echo "$(cat web/consul-services.json)"
printf "\n\nCheck out the Meta section of the service config above."
printf "\n\nOur monitoring script is gathering those k/v pairs and adding them to the check result sent to Sensu."
printf "\n\nThis enables Service Owners to freely specify any extra k/v pairs they want and they will come along for the ride."
printf "\n\nExamples of where this can be useful is in specifying what environment this client/check lives in, what handler to use for this check, or what team to route notifications to.\n\n"
read -p "Hit enter to continue..."
clear
printf "\n\nOK, now we will break some stuff!"
printf "\n\nIf we kill a container, it prevents the Consul agent on that node node from deregistering from Consul,"
printf "\nwhich means the node still exists in Consul, thus Sensu will still keep monitoring it."
read -p "Hit enter to kill the web-node-03 container..." 
docker rm -f $(docker ps -aqf "name=web-node-03") 2>&1 >/dev/null
clear
printf "\nGive it about 15-30 seconds, then you should see the check_http check for web-node-03 go critical.\n\n"
read -p "Hit enter when you have surveyed the carnage and want to continue..."
clear
printf "\nOK, we are re-launching web-node-03 now. Give it another 15-30 seconds and it should go green again.\n\n"
docker-compose up -d web-node-03 2>&1 >/dev/null
printf "\n"
read -p "Hit enter once everything is green..."
clear
printf "\n\nNow, we will see what happens when a web server stops gracefully which allows the Consul client to deregister itself."
printf "\n\nThis means the node will be removed from Consul altogether.\n\n"
read -p "Hit enter to stop the web-node-03 container..."
docker-compose stop web-node-03 2>&1 >/dev/null
clear
printf "\n\nSoon, you will see that the web-node-03 client will disappear from Uchiwa entirely."
printf "\nSince the node deregistered from Consul, and our monitor is keeping Sensu in sync with Consul, the monitor deleted the web-node-03 client from Sensu."
printf "\n\nGo ahead. Take a look at http://localhost:8500 and see if you can find web-node-03 anymore.\n\n"
read -p "I will wait here until you hit enter..."
clear
printf "\n\nTo wrap things up, we will re-launch web-node-03, which will re-add it to Sensu... again, keeping in sync with Consul.\n\n"
read -p "Hit enter when you are ready to re-launch web-node-03..."
docker-compose up -d web-node-03 2>&1 >/dev/null
clear
printf "\n\nBy now, I am sure you know the drill. Wait 15-30 seconds and you will see web-node-03 and its check_http check back and running clean."
printf "\n\nNow that you have seen the concepts, feel free to take a look at the code that drives all of this."
printf "\n\nIt lives in ./endpoint-monitor/endpoint-monitor.py."
printf "\n\nI would open it for you, but do not want to invoke any vi vs emacs wars :)"
printf "\n\nThanks for checking out the demo!"
printf "\n\n#monitoringlove"
printf "\n"
