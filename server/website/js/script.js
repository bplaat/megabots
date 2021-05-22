// Constants
const DEBUG = false;

const WEBSOCKETS_PORT = 8080;

const TICK_MANUAL = 0;
const TICK_AUTO = 1;

const TILE_UNKOWN = 0;
const TILE_FLOOR = 1;
const TILE_CHEST = 2;
const TILE_WALL = 3;

// App
let websocket, mapMeshesGroup, floorGeometry, cubeGeometry, wallGeometry,
    unkownMaterial, floorMaterial, chestMaterial, wallMaterial;
const ledOffColor = 0x000000, mapMeshes = [], robotGroups = [];

function rand (min, max) {
    return Math.floor(Math.random() * (max - min + 1)) + min;
}

const app = new Vue({
    el: '#app',

    data: {
        tickManual: TICK_MANUAL,
        tickAuto: TICK_AUTO,

        id: Date.now(),
        connected: false,
        tickType: undefined,
        tickSpeed: undefined,

        mapWidth: undefined,
        mapHeight: undefined,
        mapData: [],

        robots: [
            { id: 1, color: 0xff0000, x: undefined, y: undefined, lift: undefined, directions: [], connected: false },
            { id: 2, color: 0x00ff00, x: undefined, y: undefined, lift: undefined, directions: [], connected: false },
            { id: 3, color: 0xffff00, x: undefined, y: undefined, lift: undefined, directions: [], connected: false },
            { id: 4, color: 0x0000ff, x: undefined, y: undefined, lift: undefined, directions: [], connected: false }
        ],

        sendForm: {
            robot_id: 1,
            robot_x: 1,
            robot_y: 1
        },

        pickupForm: {
            weight: 250,
            robot_x1: 1,
            robot_y1: 1,
            robot_x2: 10,
            robot_y2: 1
        },

        activeProgram: 'Discover',
        programs: {
            Nothing() {},
            Discover() {
                // Check if there are unkown tiles
                let isDiscovered = true;
                for (let i = 0; i < this.mapHeight * this.mapWidth; i++) {
                    if (this.mapData[i] == TILE_UNKOWN) {
                        isDiscovered = false;
                        break;
                    }
                }

                if (!isDiscovered) {
                    // Get list off all unkown tiles that are not arounded with chests
                    let unkownTiles = [];
                    const unkownMap = [];
                    for (let y = 1; y < this.mapHeight - 1; y++) {
                        for (let x = 1; x < this.mapWidth - 1; x++) {
                            if (
                                this.mapData[y * this.mapWidth + x] == TILE_UNKOWN
                            ) {
                                if (
                                    this.mapData[y * this.mapWidth + (x - 1)] == TILE_CHEST &&
                                    this.mapData[(y - 1) * this.mapWidth + x] == TILE_CHEST &&
                                    this.mapData[y * this.mapWidth + (x + 1)] == TILE_CHEST &&
                                    this.mapData[(y + 1) * this.mapWidth + x] == TILE_CHEST
                                ) {
                                    continue;
                                }

                                unkownTiles.push({ x: x, y: y });
                                unkownMap[y * this.mapWidth + x] = true;
                            } else {
                                unkownMap[y * this.mapWidth + x] = false;
                            }
                        }
                    }

                    for (const robot of this.robots) {
                        if (robot.directions.length == 0 && unkownTiles.length > 0) {
                            // A even simpeler version off the path finding
                            // algorithm to search for the clossed unkown tile
                            const tileNeighbors = point => {
                                const neighbors = [];
                                if (point.x > 0)
                                    neighbors.push({ "x": point.x - 1, "y": point.y });
                                if (point.y > 0)
                                    neighbors.push({ "x": point.x, "y": point.y - 1 });
                                if (point.x < this.mapWidth - 1)
                                    neighbors.push({ "x": point.x + 1, "y": point.y });
                                if (point.y < this.mapHeight - 1)
                                    neighbors.push({ "x": point.x, "y": point.y + 1 });
                                neighbors.sort(() => (Math.random() >= 0.5) ? 1 : -1);
                                return neighbors;
                            };

                            const frontier = [ { x: robot.x, y: robot.y } ];
                            const cameFrom = [];
                            while (frontier.length > 0) {
                                let current = frontier.shift();

                                if (unkownMap[current.y * this.mapWidth + current.x]) {
                                    // Drive robot to closest unkown tile
                                    websocket.send(JSON.stringify({
                                        type: 'new_direction',
                                        data: {
                                            robot_id: robot.id,
                                            direction: {
                                                id: Date.now(),
                                                x: current.x,
                                                y: current.y
                                            }
                                        }
                                    }));

                                    // Remove tile from list
                                    unkownTiles = unkownTiles.filter(tile => !(tile.x == current.x && tile.y == current.y));
                                    unkownMap[current.y * this.mapWidth + current.x] = false;

                                    break;
                                }

                                for (const neighbor of tileNeighbors(current)) {
                                    let colliding = false;
                                    for (otherRobot of this.robots) {
                                        if (otherRobot.x == neighbor.x && otherRobot.y == neighbor.y) {
                                            colliding = true;
                                            break;
                                        }
                                    }

                                    const tileType = this.mapData[neighbor.y * this.mapWidth + neighbor.x];
                                    if (!colliding && (tileType == TILE_FLOOR || tileType == TILE_UNKOWN)) {
                                        if (cameFrom[neighbor.y * this.mapWidth + neighbor.x] == undefined) {
                                            frontier.push(neighbor);
                                            cameFrom[neighbor.y * this.mapWidth + neighbor.x] = current;
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            },
            Random() {
                for (const robot of this.robots) {
                    if (robot.directions.length == 0) {
                        // Drive robot to a random floor tile
                        let x, y;
                        do {
                            x = rand(1, this.mapWidth - 2);
                            y = rand(1, this.mapHeight - 2);
                        } while (this.mapData[y * this.mapWidth + x] != TILE_FLOOR);

                        websocket.send(JSON.stringify({
                            type: 'new_direction',
                            data: {
                                robot_id: robot.id,
                                direction: {
                                    id: Date.now(),
                                    x: x,
                                    y: y
                                }
                            }
                        }));
                    }
                }
            }
        }
    },

    watch: {
        tickType(tickType, oldTickType) {
            if (this.connected && tickType != oldTickType) {
                websocket.send(JSON.stringify({
                    type: 'update_world_info',
                    data: {
                        tick_type: tickType
                    }
                }));
            }
        },

        tickSpeed(tickSpeed, oldTickSpeed) {
            if (this.connected && tickSpeed != oldTickSpeed) {
                websocket.send(JSON.stringify({
                    type: 'update_world_info',
                    data: {
                        tick_speed: tickSpeed
                    }
                }));
            }
        }
    },

    methods: {
        websocketsConnect() {
            websocket = new WebSocket('ws://127.0.0.1:' + WEBSOCKETS_PORT + '/');

            websocket.onopen = () => {
                websocket.send(JSON.stringify({
                    type: 'website_connect',
                    data: {
                        website_id: this.id
                    }
                }));
                this.connected = true;
            };

            websocket.onmessage = event => {
                if (DEBUG) {
                    console.log('Server message: ' + event.data);
                }
                const message = JSON.parse(event.data);

                // Connect message
                if (message.type == 'robot_connect') {
                    const robot = this.robots.find(robot => robot.id == message.data.robot_id);
                    this.worldUpdateTile(message.data.robot_x, message.data.robot_y, TILE_FLOOR);
                    this.worldMoveRobot(robot.id, message.data.robot_x, message.data.robot_y);
                    robot.lift = message.data.robot_lift;

                    robot.directions = [];
                    for (const direction of message.data.directions) {
                        robot.directions.push({
                            id: direction.id,
                            x: direction.x,
                            y: direction.y
                        })
                    }
                    this.worldUpdateRobotDestination(robot.id);

                    robot.connected = true;
                }

                // Disconnect message
                if (message.type == 'robot_disconnect') {
                    const robot = this.robots.find(robot => robot.id == message.data.robot_id);
                    robot.connected = false;

                    if (robotGroups.length > 0) {
                        const robotGroup = robotGroups[robot.id - 1];
                        robotGroup.visible = false;
                        robotGroup.destinationGroup.visible = false;
                    }
                }

                // World info message
                if (message.type == 'world_info') {
                    this.tickType = message.data.tick_type;
                    this.tickSpeed = message.data.tick_speed;

                    this.mapWidth = message.data.map.width;
                    this.mapHeight = message.data.map.height;
                    for (let y = 0; y < this.mapHeight; y++) {
                        for (let x = 0; x < this.mapWidth; x++) {
                            this.mapData[y * this.mapWidth + x] = message.data.map.data[y * this.mapWidth + x];
                        }
                    }

                    this.startWorldSimulation();
                }

                // Update world info message
                if (message.type == 'update_world_info') {
                    if (message.data.tick_type != undefined) {
                        this.tickType = message.data.tick_type;
                    }
                    if (message.data.tick_speed != undefined) {
                        this.tickSpeed = message.data.tick_speed;
                    }
                }

                // New direction message
                if (message.type == 'new_direction') {
                    const robot = this.robots.find(robot => robot.id == message.data.robot_id);
                    robot.directions.push({
                        id: message.data.direction.id,
                        x: message.data.direction.x,
                        y: message.data.direction.y
                    });
                    this.worldUpdateRobotDestination(robot.id);
                }

                // Cancel direction message
                if (message.type == 'cancel_direction') {
                    const robot = this.robots.find(robot => robot.id == message.data.robot_id);
                    robot.directions = robot.directions.filter(direction => direction.id != message.data.direction.id);
                    this.worldUpdateRobotDestination(robot.id);
                }

                // Tick done message
                if (message.type == 'robot_tick_done') {
                    for (const mapUpdate of message.data.map) {
                        this.worldUpdateTile(mapUpdate.x, mapUpdate.y, mapUpdate.type);
                    }

                    this.worldMoveRobot(message.data.robot_id, message.data.robot_x, message.data.robot_y);
                }

                // Website tick message
                if (message.type == 'website_tick') {
                    this.programs[this.activeProgram].bind(this)();
                }
            };

            websocket.onclose = () => {
                this.connected = false;
            };
        },

        cancelDirection(robotId, directionId) {
            if (websocket != undefined) {
                websocket.send(JSON.stringify({
                    type: 'cancel_direction',
                    data: {
                        robot_id: robotId,
                        direction: {
                            id: directionId
                        }
                    }
                }));
            }
        },

        tick() {
            if (this.tickType == TICK_MANUAL) {
                websocket.send(JSON.stringify({
                    type: 'world_tick',
                    data: {}
                }));
            }
        },

        sendFormSubmit() {
            if (websocket != undefined) {
                websocket.send(JSON.stringify({
                    type: 'new_direction',
                    data: {
                        robot_id: this.sendForm.robot_id,
                        direction: {
                            id: Date.now(),
                            x: this.sendForm.robot_x,
                            y: this.sendForm.robot_y
                        }
                    }
                }));
            }
        },

        pickupFormSubmit() {
            if (websocket != undefined) {
                // Check if there is a robot with the lift that is waiting
                const randomRobots = this.robots.slice().sort(() => (Math.random() >= 0.5) ? 1 : -1);
                for (const robot of randomRobots) {
                    if (robot.directions.length == 0 && robot.lift >= this.pickupForm.weight) {
                        const directionId = Date.now();

                        websocket.send(JSON.stringify({
                            type: 'new_direction',
                            data: {
                                robot_id: robot.id,
                                direction: {
                                    id: directionId,
                                    x: this.pickupForm.robot_x1,
                                    y: this.pickupForm.robot_y1
                                }
                            }
                        }));

                        websocket.send(JSON.stringify({
                            type: 'new_direction',
                            data: {
                                robot_id: robot.id,
                                direction: {
                                    id: directionId + 1,
                                    x: this.pickupForm.robot_x2,
                                    y: this.pickupForm.robot_y2
                                }
                            }
                        }));

                        return;
                    }
                }

                // Else queue order for the first robot with the lift
                for (const robot of randomRobots) {
                    if (robot.lift >= this.pickupForm.weight) {
                        const directionId = Date.now();

                        websocket.send(JSON.stringify({
                            type: 'new_direction',
                            data: {
                                robot_id: robot.id,
                                direction: {
                                    id: directionId,
                                    x: this.pickupForm.robot_x1,
                                    y: this.pickupForm.robot_y1
                                }
                            }
                        }));

                        websocket.send(JSON.stringify({
                            type: 'new_direction',
                            data: {
                                robot_id: robot.id,
                                direction: {
                                    id: directionId + 1,
                                    x: this.pickupForm.robot_x2,
                                    y: this.pickupForm.robot_y2
                                }
                            }
                        }));

                        return;
                    }
                }
            }
        },

        worldUpdateTile(x, y, type) {
            if (type != this.mapData[y * this.mapWidth + x]) {
                this.mapData[y * this.mapWidth + x] = type;

                if (mapMeshes.length > 0) {
                    mapMeshesGroup.remove(mapMeshes[y * this.mapWidth + x]);

                    let geometry
                    if (type == TILE_UNKOWN || type == TILE_CHEST) geometry = cubeGeometry;
                    if (type == TILE_FLOOR) geometry = floorGeometry;
                    if (type == TILE_WALL) geometry = wallGeometry;

                    let material;
                    if (type == TILE_UNKOWN) material = unkownMaterial;
                    if (type == TILE_FLOOR) material = floorMaterial;
                    if (type == TILE_CHEST) material = chestMaterial;
                    if (type == TILE_WALL) material = wallMaterial;

                    const tileMesh = new THREE.Mesh(geometry, material);
                    tileMesh.position.x = x - this.mapWidth / 2;
                    tileMesh.position.z = y - this.mapHeight / 2;
                    if (type == TILE_FLOOR) tileMesh.position.y = -0.5;
                    if (type == TILE_FLOOR) tileMesh.rotation.x = -Math.PI / 2;
                    if (type == TILE_WALL) tileMesh.position.y = 0.25;

                    mapMeshes[y * this.mapWidth + x] = tileMesh;
                    mapMeshesGroup.add(tileMesh);
                }
            }
        },

        worldMoveRobot(robotId, x, y) {
            const robot = this.robots.find(robot => robot.id == robotId);
            const old_robot_x = robot.x;
            const old_robot_y = robot.y;
            robot.x = x;
            robot.y = y;

            if (robotGroups.length > 0) {
                const robotsGroup = robotGroups[robot.id - 1];

                robotsGroup.upLedMesh.material.color.setHex(robot.y - old_robot_y < 0 ? robot.color : ledOffColor);
                robotsGroup.leftLedMesh.material.color.setHex(robot.x - old_robot_x < 0 ? robot.color : ledOffColor);
                robotsGroup.rightLedMesh.material.color.setHex(robot.x - old_robot_x > 0 ? robot.color : ledOffColor);
                robotsGroup.downLedMesh.material.color.setHex(robot.y - old_robot_y > 0 ? robot.color : ledOffColor);

                if (robotsGroup.visible) {
                    const coords = { x: robotsGroup.position.x, y: robotsGroup.position.z };
                    const tween = new TWEEN.Tween(coords)
                        .to({
                            x: robot.x - this.mapWidth / 2,
                            y: robot.y - this.mapHeight / 2
                        }, this.tickSpeed)
                        .easing(TWEEN.Easing.Quadratic.Out)
                        .onUpdate(() => {
                            robotsGroup.position.x = coords.x;
                            robotsGroup.position.z = coords.y;
                        })
                        .start();
                } else {
                    robotsGroup.position.x = x - this.mapWidth / 2;
                    robotsGroup.position.z = y - this.mapHeight / 2;
                    robotsGroup.visible = true;
                }
            }
        },

        worldUpdateRobotDestination(robotId) {
            if (robotGroups.length > 0) {
                const robot = this.robots.find(robot => robot.id == robotId);
                const robotDestinationGroup = robotGroups[robot.id - 1].destinationGroup;
                if (robot.directions.length > 0) {
                    robotDestinationGroup.visible = true;
                    if (robotDestinationGroup.position.x != 0 && robotDestinationGroup.position.z != 0) {
                        const coords = { x: robotDestinationGroup.position.x, y: robotDestinationGroup.position.z };
                        const tween = new TWEEN.Tween(coords)
                            .to({
                                x: robot.directions[0].x - this.mapWidth / 2,
                                y: robot.directions[0].y - this.mapHeight / 2
                            }, this.tickSpeed)
                            .easing(TWEEN.Easing.Quadratic.Out)
                            .onUpdate(() => {
                                robotDestinationGroup.position.x = coords.x;
                                robotDestinationGroup.position.z = coords.y;
                            })
                            .start();
                    } else {
                        robotDestinationGroup.position.x = robot.directions[0].x - this.mapWidth / 2;
                        robotDestinationGroup.position.z = robot.directions[0].y - this.mapHeight / 2;
                    }
                }
            }
        },

        startWorldSimulation() {
            // 3D Map Simulation
            const scene = new THREE.Scene();

            const camera = new THREE.PerspectiveCamera( 75, window.innerWidth / window.innerHeight, 0.1, 1000 );
            camera.position.y = this.mapWidth;

            const renderer = new THREE.WebGLRenderer({ canvas: document.getElementById('canvas') });
            renderer.setClearColor(0x87ceeb);
            renderer.setSize(window.innerWidth, window.innerHeight);

            window.addEventListener('resize', function () {
                camera.aspect = window.innerWidth / window.innerHeight;
                camera.updateProjectionMatrix();

                renderer.setSize(window.innerWidth, window.innerHeight);
            });

            const controls = new THREE.OrbitControls(camera, renderer.domElement);

            const stats = new Stats();
            stats.dom.style.top = '';
            stats.dom.style.left = '';
            stats.dom.style.right = '8px';
            stats.dom.style.bottom = '8px';
            document.body.appendChild(stats.dom);

            // Create map meshes
            mapMeshesGroup = new THREE.Group();
            scene.add(mapMeshesGroup);

            floorGeometry = new THREE.PlaneGeometry(1, 1);
            cubeGeometry = new THREE.BoxGeometry(1, 1, 1);
            wallGeometry = new THREE.BoxGeometry(1, 1.5, 1);
            unkownMaterial = new THREE.MeshBasicMaterial({ color: 0x222222, map: new THREE.TextureLoader().load('/images/unkown.jpg') });
            floorMaterial = new THREE.MeshBasicMaterial({ map: new THREE.TextureLoader().load('/images/floor.jpg'), side: THREE.DoubleSide });
            chestMaterial = new THREE.MeshBasicMaterial({ map: new THREE.TextureLoader().load('/images/chest.jpg') });
            wallMaterial = new THREE.MeshBasicMaterial({ map: new THREE.TextureLoader().load('/images/wall.jpg') });

            for (let y = 0; y < this.mapHeight; y++) {
                for (let x = 0; x < this.mapWidth; x++) {
                    const type = this.mapData[y * this.mapWidth + x];

                    let geometry
                    if (type == TILE_UNKOWN || type == TILE_CHEST) geometry = cubeGeometry;
                    if (type == TILE_FLOOR) geometry = floorGeometry;
                    if (type == TILE_WALL) geometry = wallGeometry;

                    let material;
                    if (type == TILE_UNKOWN) material = unkownMaterial;
                    if (type == TILE_FLOOR) material = floorMaterial;
                    if (type == TILE_CHEST) material = chestMaterial;
                    if (type == TILE_WALL) material = wallMaterial;

                    const tileMesh = new THREE.Mesh(geometry, material);
                    tileMesh.position.x = x - this.mapWidth / 2;
                    tileMesh.position.z = y - this.mapHeight / 2;
                    if (type == TILE_FLOOR) tileMesh.position.y = -0.5;
                    if (type == TILE_FLOOR) tileMesh.rotation.x = -Math.PI / 2;
                    if (type == TILE_WALL) tileMesh.position.y = 0.25;

                    mapMeshes[y * this.mapWidth + x] = tileMesh;
                    mapMeshesGroup.add(tileMesh);
                }
            }

            // Create robot meshes
            const robotGeometry = new THREE.CylinderGeometry(0.3, 0.3, 0.99, 32);
            const robotTexure = new THREE.TextureLoader().load('/images/robot.jpg');
            const ledGeometry = new THREE.SphereGeometry(0.05, 32, 32);
            const destinationArrowGeometry = new THREE.ConeGeometry(0.3, 0.5, 32);

            for (const robot of this.robots) {
                // Robot group
                const robotGroup = new THREE.Group();
                if (robot.x != undefined && robot.y != undefined) {
                    robotGroup.position.x = robot.x - this.mapWidth / 2;
                    robotGroup.position.z = robot.y - this.mapHeight / 2;
                } else {
                    robotGroup.visible = false;
                }
                scene.add(robotGroup);
                robotGroups[robot.id - 1] = robotGroup;

                robotGroup.add(new THREE.Mesh(robotGeometry, new THREE.MeshBasicMaterial({ color: robot.color, map: robotTexure })));

                robotGroup.upLedMesh = new THREE.Mesh(ledGeometry, new THREE.MeshBasicMaterial({ color: ledOffColor }));
                robotGroup.upLedMesh.position.y = 0.5;
                robotGroup.upLedMesh.position.z = -0.3;
                robotGroup.add(robotGroup.upLedMesh);

                robotGroup.leftLedMesh = new THREE.Mesh(ledGeometry, new THREE.MeshBasicMaterial({ color: ledOffColor }));
                robotGroup.leftLedMesh.position.x = -0.3;
                robotGroup.leftLedMesh.position.y = 0.5;
                robotGroup.add(robotGroup.leftLedMesh);

                robotGroup.rightLedMesh = new THREE.Mesh(ledGeometry, new THREE.MeshBasicMaterial({ color: ledOffColor }));
                robotGroup.rightLedMesh.position.x = 0.3;
                robotGroup.rightLedMesh.position.y = 0.5;
                robotGroup.add(robotGroup.rightLedMesh);

                robotGroup.downLedMesh = new THREE.Mesh(ledGeometry, new THREE.MeshBasicMaterial({ color: ledOffColor }));
                robotGroup.downLedMesh.position.y = 0.5;
                robotGroup.downLedMesh.position.z = 0.3;
                robotGroup.add(robotGroup.downLedMesh);

                // Robot destination group
                robotGroup.destinationGroup = new THREE.Group();
                if (robot.directions.length > 0) {
                    robotGroup.destinationGroup.position.x = robot.directions[0].x - this.mapWidth / 2;
                    robotGroup.destinationGroup.position.z = robot.directions[0].y - this.mapHeight / 2;
                } else {
                    robotGroup.destinationGroup.visible = false;
                }
                scene.add(robotGroup.destinationGroup);

                const destinationArrowMesh = new THREE.Mesh(destinationArrowGeometry, new THREE.MeshBasicMaterial({ color: robot.color }));
                destinationArrowMesh.rotation.x = Math.PI;
                destinationArrowMesh.position.y = 1.5;
                robotGroup.destinationGroup.add(destinationArrowMesh);
            }

            // Map renderer loop
            function loop(delta) {
                stats.begin();
                controls.update();
                TWEEN.update(delta)
                renderer.render(scene, camera);
                stats.end();
                window.requestAnimationFrame(loop);
            }
            window.requestAnimationFrame(loop);
        }
    },

    created() {
        this.websocketsConnect();
    }
});
