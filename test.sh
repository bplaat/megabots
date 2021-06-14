# Script to launch the server, webserver and all 4 clients to test

# For macOS alias python to Python 3
if [ "$(uname -s)" == "Darwin" ]; then
    alias python=python3
fi

if [[ $1 == "webots" ]]; then
    python map-generator.py 16 16 webots

    python server/server.py &

    sleep 0.25

    if [ "$(uname -s)" == "Linux" ]; then
        webots webots/worlds/world.wbt & disown
    # elif [ "$(uname -s)" == "Darwin" ]; then
        # TODO
    else
        start webots/worlds/world.wbt
    fi
else
    python map-generator.py 24 24

    python server/server.py &

    sleep 0.25

    python webots/supervisor.py &
fi

sleep 0.25

python -m http.server 8081 --directory server/website > /dev/null 2> /dev/null &
if [ "$(uname -s)" == "Linux" ]; then
    xdg-open http://localhost:8081/ & disown
elif [ "$(uname -s)" == "Darwin" ]; then
    open http://localhost:8081/
else
    start http://localhost:8081/
fi

sleep 0.25

python clients/bastiaan/client.py 1 &
python clients/bastiaan/client.py 2 &
python clients/bastiaan/client.py 3 &
python clients/bastiaan/client.py 4

wait < <(jobs -p)
