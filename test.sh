# Script to launch all 4 clients and server to test
python server/server.py &
python clients/bastiaan/client.py 1 &
python clients/bastiaan/client.py 2 &
python clients/bastiaan/client.py 3 &
python clients/bastiaan/client.py 4
wait < <(jobs -p)
