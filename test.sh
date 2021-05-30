# Script to launch the server, webserver and all 4 clients to test

# For MacOS alias python to Python 3
if [ "$(uname -s)" == "Darwin" ]; then
    alias python = python3
fi

if [[ $1 == "webots" ]]; then
    python map-generator.py 16 16 webots

    python server/server.py &
    python -m http.server 8081 --directory server/website &

    if [ "$(uname -s)" == "Linux" ]; then
        xdg-open http://localhost:8081/ &
        disown
        # Open webots manually
    elif [ "$(uname -s)" == "Darwin" ]; then
        open http://localhost:8081/
        # Open webots manually
    else
        start http://localhost:8081/
        start webots/worlds/world.wbt
    fi
else
    python map-generator.py 24 24

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
fi

wait < <(jobs -p)
