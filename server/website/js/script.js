// Constants
const DEBUG = true;

const WEBSOCKETS_URL = 'ws://127.0.0.1:8080/';

const TICK_MANUAL = 0;
const TICK_AUTO = 1;

const TILE_UNKOWN = 0;
const TILE_FLOOR = 1;
const TILE_CHEST = 2;

// App
let websocket, mapMeshesGroup, floorGeometry, cubeGeometry,
    unkownMaterial, floorMaterial, chestMaterial;
const ledOffColor = { r: 0, g: 0, b: 0 }, mapMeshes = [], robotGroups = [];

const app = new Vue({
    el: '#app',

    data: {
        tickManual: TICK_MANUAL,
        tickAuto: TICK_AUTO,

        id: Date.now(),
        connected: false,
        tickType: undefined,
        tickSpeed: undefined,
        activeProgramId: undefined,
        programs: undefined,

        mapWidth: undefined,
        mapHeight: undefined,
        mapData: undefined,

        robots: [
            { id: 1, x: undefined, y: undefined, lift: undefined, color: { r: undefined, g: undefined, b: undefined }, directions: [], connected: false },
            { id: 2, x: undefined, y: undefined, lift: undefined, color: { r: undefined, g: undefined, b: undefined }, directions: [], connected: false },
            { id: 3, x: undefined, y: undefined, lift: undefined, color: { r: undefined, g: undefined, b: undefined }, directions: [], connected: false },
            { id: 4, x: undefined, y: undefined, lift: undefined, color: { r: undefined, g: undefined, b: undefined }, directions: [], connected: false }
        ],

        sendForm: {
            robot_id: 1,
            robot_x: 10,
            robot_y: 0
        },

        pickupForm: {
            weight: 250,
            robot_x1: 0,
            robot_y1: 0,
            robot_x2: 10,
            robot_y2: 0
        }
    },

    methods: {
        websocketsConnect() {
            websocket = new WebSocket(WEBSOCKETS_URL);

            websocket.onopen = () => {
                this.connected = true;
                this.sendMessage('website_connect', { website_id: this.id });
            };

            websocket.onmessage = event => {
                if (DEBUG) {
                    console.log('Server message: ' + event.data);
                }
                const message = JSON.parse(event.data);

                // World info message
                if (message.type == 'world_info') {
                    this.tickType = message.data.tick.type;
                    this.tickSpeed = message.data.tick.speed;

                    this.activeProgramId = message.data.active_program_id;
                    this.programs = [];
                    for (const program of message.data.programs) {
                        this.programs.push({
                            id: program.id,
                            name: program.name
                        });
                    }

                    this.mapWidth = message.data.map.width;
                    this.mapHeight = message.data.map.height;
                    this.mapData = [];
                    for (let y = 0; y < this.mapHeight; y++) {
                        this.mapData[y] = [];
                        for (let x = 0; x < this.mapWidth; x++) {
                            this.mapData[y][x] = message.data.map.data[y][x];
                        }
                    }

                    this.startWorldSimulation();
                }

                // Robot connect message
                if (message.type == 'robot_connect') {
                    const robot = this.robots.find(robot => robot.id == message.data.robot_id);
                    this.worldUpdateTile(message.data.robot.x, message.data.robot.y, TILE_FLOOR);
                    this.worldMoveRobot(robot.id, message.data.robot.x, message.data.robot.y);
                    robot.lift = message.data.robot.lift;

                    robot.color.r = message.data.robot.color.red;
                    robot.color.g = message.data.robot.color.green;
                    robot.color.b = message.data.robot.color.blue;

                    robot.directions = [];
                    for (const direction of message.data.robot.directions) {
                        robot.directions.push({
                            id: direction.id,
                            x: direction.x,
                            y: direction.y
                        })
                    }
                    this.worldUpdateRobotDestination(robot.id);

                    robot.connected = true;
                }

                // Robot disconnect message
                if (message.type == 'robot_disconnect') {
                    const robot = this.robots.find(robot => robot.id == message.data.robot_id);
                    robot.connected = false;

                    if (robotGroups.length > 0) {
                        const robotGroup = robotGroups[robot.id - 1];
                        robotGroup.visible = false;
                        robotGroup.destinationGroup.visible = false;
                    }
                }

                // Update world info message
                if (message.type == 'update_world_info') {
                    if (message.data.tick != undefined) {
                        if (message.data.tick.type != undefined) {
                            this.tickType = message.data.tick.type;
                        }

                        if (message.data.tick.speed != undefined) {
                            this.tickSpeed = message.data.tick.speed;
                        }
                    }

                    if (message.data.active_program_id != undefined) {
                        this.activeProgramId = message.data.active_program_id;
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
                    robot.directions = robot.directions.filter(direction => direction.id != message.data.direction_id);
                    this.worldUpdateRobotDestination(robot.id);
                }

                // Tick done message
                if (message.type == 'robot_tick_done') {
                    if (message.data.map != undefined) {
                        for (const mapUpdate of message.data.map) {
                            this.worldUpdateTile(mapUpdate.x, mapUpdate.y, mapUpdate.type);
                        }
                    }

                    if (message.data.robot != undefined) {
                        this.worldMoveRobot(message.data.robot_id, message.data.robot.x, message.data.robot.y);
                    }
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

        sendMessage(type, data = {}) {
            if (this.connected) {
                websocket.send(JSON.stringify({ type: type, data: data }));
            }
        },

        cancelDirection(robotId, directionId) {
            this.sendMessage('cancel_direction', {
                robot_id: robotId,
                direction_id: parseInt(directionId)
            });
        },

        tickStop() {
            this.tickType = TICK_MANUAL;
            this.changeTickType();
        },

        changeTickType() {
            this.sendMessage('update_world_info', {
                tick: {
                    type: parseInt(this.tickType)
                }
            });
        },

        changeTickSpeed() {
            this.sendMessage('update_world_info', {
                tick: {
                    speed: parseInt(this.tickSpeed)
                }
            });
        },

        changeActiveProgramId() {
            this.sendMessage('update_world_info', {
                active_program_id: parseInt(this.activeProgramId)
            });
        },

        tick() {
            if (this.tickType == TICK_MANUAL) {
                this.sendMessage('world_tick');
            }
        },

        sendFormSubmit() {
            this.sendMessage('new_direction', {
                robot_id: this.sendForm.robot_id,
                direction: {
                    id: Date.now(),
                    x: parseInt(this.sendForm.robot_x),
                    y: parseInt(this.sendForm.robot_y)
                }
            });
        },

        pickupFormSubmit() {
            if (this.connected) {
                // Check if there is a robot with the lift that is waiting
                const randomRobots = this.robots.slice().sort(() => (Math.random() >= 0.5) ? 1 : -1);
                for (const robot of randomRobots) {
                    if (robot.directions.length == 0 && robot.lift >= this.pickupForm.weight) {
                        const directionId = Date.now();

                        this.sendMessage('new_direction', {
                            robot_id: robot.id,
                            direction: {
                                id: directionId,
                                x: parseInt(this.pickupForm.robot_x1),
                                y: parseInt(this.pickupForm.robot_y1)
                            }
                        });

                        this.sendMessage('new_direction', {
                            robot_id: robot.id,
                            direction: {
                                id: directionId + 1,
                                x: parseInt(this.pickupForm.robot_x2),
                                y: parseInt(this.pickupForm.robot_y2)
                            }
                        });

                        return;
                    }
                }

                // Else queue order for the first robot with the lift
                for (const robot of randomRobots) {
                    if (robot.lift >= this.pickupForm.weight) {
                        const directionId = Date.now();

                        this.sendMessage('new_direction', {
                            robot_id: robot.id,
                            direction: {
                                id: directionId,
                                x: parseInt(this.pickupForm.robot_x1),
                                y: parseInt(this.pickupForm.robot_y1)
                            }
                        });

                        this.sendMessage('new_direction', {
                            robot_id: robot.id,
                            direction: {
                                id: directionId + 1,
                                x: parseInt(this.pickupForm.robot_x2),
                                y: parseInt(this.pickupForm.robot_y2)
                            }
                        });

                        return;
                    }
                }
            }
        },

        worldUpdateTile(x, y, type) {
            if (type != this.mapData[y][x]) {
                this.mapData[y][x] = type;

                if (mapMeshes.length > 0) {
                    mapMeshesGroup.remove(mapMeshes[y][x]);

                    let geometry
                    if (type == TILE_UNKOWN || type == TILE_CHEST) geometry = cubeGeometry;
                    if (type == TILE_FLOOR) geometry = floorGeometry;

                    let material;
                    if (type == TILE_UNKOWN) material = unkownMaterial;
                    if (type == TILE_FLOOR) material = floorMaterial;
                    if (type == TILE_CHEST) material = chestMaterial;

                    const tileMesh = new THREE.Mesh(geometry, material);
                    tileMesh.position.x = x - this.mapWidth / 2;
                    tileMesh.position.z = y - this.mapHeight / 2;
                    if (type == TILE_FLOOR) tileMesh.position.y = -0.5;
                    if (type == TILE_FLOOR) tileMesh.rotation.x = -Math.PI / 2;

                    mapMeshes[y][x] = tileMesh;
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

                robotsGroup.robotMesh.material.color = robot.color;
                robotsGroup.upLedMesh.material.color = robot.y - old_robot_y < 0 ? robot.color : ledOffColor;
                robotsGroup.leftLedMesh.material.color = robot.x - old_robot_x < 0 ? robot.color : ledOffColor;
                robotsGroup.rightLedMesh.material.color = robot.x - old_robot_x > 0 ? robot.color : ledOffColor;
                robotsGroup.downLedMesh.material.color = robot.y - old_robot_y > 0 ? robot.color : ledOffColor;

                if (robotsGroup.visible) {
                    const position = { x: robotsGroup.position.x, y: robotsGroup.position.z };
                    new TWEEN.Tween(position)
                        .to({
                            x: robot.x - this.mapWidth / 2,
                            y: robot.y - this.mapHeight / 2
                        }, this.tickSpeed)
                        .easing(TWEEN.Easing.Quadratic.Out)
                        .onUpdate(() => {
                            robotsGroup.position.x = position.x;
                            robotsGroup.position.z = position.y;
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
                    robotDestinationGroup.destinationArrowMesh.material.color = robot.color;
                    robotDestinationGroup.visible = true;
                    if (robotDestinationGroup.position.x != 0 && robotDestinationGroup.position.z != 0) {
                        const position = { x: robotDestinationGroup.position.x, y: robotDestinationGroup.position.z };
                        new TWEEN.Tween(position)
                            .to({
                                x: robot.directions[0].x - this.mapWidth / 2,
                                y: robot.directions[0].y - this.mapHeight / 2
                            }, this.tickSpeed)
                            .easing(TWEEN.Easing.Quadratic.Out)
                            .onUpdate(() => {
                                robotDestinationGroup.position.x = position.x;
                                robotDestinationGroup.position.z = position.y;
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
            unkownMaterial = new THREE.MeshBasicMaterial({ color: 0x222222, map: new THREE.TextureLoader().load('/images/unkown.jpg') });
            floorMaterial = new THREE.MeshBasicMaterial({ map: new THREE.TextureLoader().load('/images/floor.jpg'), side: THREE.DoubleSide });
            chestMaterial = new THREE.MeshBasicMaterial({ map: new THREE.TextureLoader().load('/images/chest.jpg') });

            for (let y = 0; y < this.mapHeight; y++) {
                mapMeshes[y] = [];
                for (let x = 0; x < this.mapWidth; x++) {
                    const type = this.mapData[y][x];

                    let geometry
                    if (type == TILE_UNKOWN || type == TILE_CHEST) geometry = cubeGeometry;
                    if (type == TILE_FLOOR) geometry = floorGeometry;

                    let material;
                    if (type == TILE_UNKOWN) material = unkownMaterial;
                    if (type == TILE_FLOOR) material = floorMaterial;
                    if (type == TILE_CHEST) material = chestMaterial;

                    const tileMesh = new THREE.Mesh(geometry, material);
                    tileMesh.position.x = x - this.mapWidth / 2;
                    tileMesh.position.z = y - this.mapHeight / 2;
                    if (type == TILE_FLOOR) tileMesh.position.y = -0.5;
                    if (type == TILE_FLOOR) tileMesh.rotation.x = -Math.PI / 2;

                    mapMeshes[y][x] = tileMesh;
                    mapMeshesGroup.add(tileMesh);
                }
            }

            // Create map wall
            const wallHeight = 0.5;
            const wallSize = 0.1;

            const wallWidthGeometry = new THREE.BoxGeometry(this.mapWidth + wallSize * 2, wallHeight, wallSize);
            const wallWidthTexture = new THREE.TextureLoader().load('/images/wall.jpg');
            wallWidthTexture.wrapS = THREE.RepeatWrapping;
            wallWidthTexture.wrapT = THREE.RepeatWrapping;
            wallWidthTexture.repeat.set(this.mapWidth * (1 / wallHeight), 1);
            const wallWidthMaterial = new THREE.MeshBasicMaterial({ map: wallWidthTexture });

            const wallHeightGeometry = new THREE.BoxGeometry(wallSize, wallHeight, this.mapHeight + wallSize);
            const wallHeightTexture = new THREE.TextureLoader().load('/images/wall.jpg');
            wallHeightTexture.wrapS = THREE.RepeatWrapping;
            wallHeightTexture.wrapT = THREE.RepeatWrapping;
            wallHeightTexture.repeat.set(this.mapHeight * (1 / wallHeight), 1);
            const wallHeightMaterial = new THREE.MeshBasicMaterial({ map: wallHeightTexture });

            const wallGroup = new THREE.Group();
            scene.add(wallGroup);

            const topWall = new THREE.Mesh(wallWidthGeometry, wallWidthMaterial);
            topWall.position.x = -0.5;
            topWall.position.y = -(1 - wallHeight) / 2;
            topWall.position.z = -this.mapWidth / 2 - (0.5 + wallSize / 2);
            wallGroup.add(topWall);

            const leftWall = new THREE.Mesh(wallHeightGeometry, wallHeightMaterial);
            leftWall.position.x = -this.mapWidth / 2 - (0.5 + wallSize / 2);
            leftWall.position.y = -(1 - wallHeight) / 2;
            leftWall.position.z = -0.5;
            wallGroup.add(leftWall);

            const rightWall = new THREE.Mesh(wallHeightGeometry, wallHeightMaterial);
            rightWall.position.x = this.mapWidth / 2 - (0.5 - wallSize / 2);
            rightWall.position.y = -(1 - wallHeight) / 2;
            rightWall.position.z = -0.5;
            wallGroup.add(rightWall);

            const bottomWall = new THREE.Mesh(wallWidthGeometry, wallWidthMaterial);
            bottomWall.position.x = -0.5;
            bottomWall.position.y = -(1 - wallHeight) / 2;
            bottomWall.position.z = this.mapWidth / 2 - (0.5  - wallSize / 2);
            wallGroup.add(bottomWall);

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

                const robotMesh = new THREE.Mesh(robotGeometry, new THREE.MeshBasicMaterial({ map: robotTexure }));
                if (robot.connected) {
                    robotMesh.material.color = robot.color;
                }
                robotGroup.robotMesh = robotMesh;
                robotGroup.add(robotMesh);

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

                const destinationArrowMesh = new THREE.Mesh(destinationArrowGeometry, new THREE.MeshBasicMaterial());
                destinationArrowMesh.rotation.x = Math.PI;
                destinationArrowMesh.position.y = 1.5;
                robotGroup.destinationGroup.destinationArrowMesh = destinationArrowMesh;
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
