# Script to launch the server, webserver and all 4 clients to test

if [ "$(uname -s)" == "Darwin" ]; then
    alias python = python3
fi

python map-generator.py 16 16

python server/server.py &
python -m http.server 8081 --directory server/website &

if [ "$(uname -s)" == "Linux" ]; then
    xdg-open http://localhost:8081/ &
    disown
elif [ "$(uname -s)" == "Darwin" ]; then
    open http://localhost:8081/
else
    start http://localhost:8081/
fi

sleep 0.5

python clients/bastiaan/client.py 1 &
python clients/bastiaan/client.py 2 &
python clients/bastiaan/client.py 3 &
python clients/bastiaan/client.py 4

wait < <(jobs -p)
