# Script to launch the server, webserver and all 4 clients to test

python server/server.py &
python -m http.server 8081 --directory server/website &
start http://localhost:8081/ &

python clients/bastiaan/client.py 1 &
python clients/bastiaan/client.py 2 &
python clients/bastiaan/client.py 3 &
python clients/bastiaan/client.py 4

wait < <(jobs -p)
