# Script to launch the server, webserver and all 4 clients to test

./server/server.py &
python -m http.server 8081 --directory server/website &
start http://localhost:8081/ &

./clients/bastiaan/client.py 1 &
./clients/bastiaan/client.py 2 &
./clients/bastiaan/client.py 3 &
./clients/bastiaan/client.py 4

wait < <(jobs -p)
