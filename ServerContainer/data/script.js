//
const up = document.getElementById("up");
const left = document.getElementById("left");
const right = document.getElementById("right");
const down = document.getElementById("down");
//
var gateway = `ws://192.168.4.1/ws`;
var websocket;
window.addEventListener('load', onLoad);

function onLoad() {
    websocket = new WebSocket(gateway);

    websocket.onopen = function() {
        document.getElementById("connectionStatus").innerHTML = "Connected";
    };
    websocket.onmessage = function(event) {
        document.getElementById("status").innerHTML = event.data;

        const parts = event.data.split(",");

        if (parts.length === 2) {
            const distance = Number(parts[0].trim());
            const angle = Number(parts[1].trim());

            if (!isNaN(distance) && !isNaN(angle)) {
                draw(distance, angle);
            }
        }
    };
    websocket.onclose = function() {
        document.getElementById("connectionStatus").innerHTML = "Disconnected";
        setTimeout(onLoad, 1000);
    };
}
function sendCommand(command) {
    websocket.send(command);
}
//Listen for any key being pressed down
document.addEventListener("keydown", downkey);
document.addEventListener("keyup", upkey);


function downkey(e) {
    if (e.repeat) return; //Don't trigger more then once

    // Reset all colors first (UI)
    up.style.backgroundColor = left.style.backgroundColor = right.style.backgroundColor = down.style.backgroundColor = "black";

    switch(e.key) {
        case "ArrowUp":
            up.style.backgroundColor = "darkgreen";
            sendCommand("forward");
            break;
        case "ArrowLeft":
            left.style.backgroundColor = "darkgreen";
            sendCommand("nothing");
            break;
        case "ArrowRight":
            right.style.backgroundColor = "darkgreen";
            sendCommand("nothing");
            break;
        case "ArrowDown":
            down.style.backgroundColor = "darkgreen";
            sendCommand("forward");
            break;
    }
}
function upkey(e) {
    if (e.repeat) return;

    // Reset all colors on key release
    up.style.backgroundColor = left.style.backgroundColor = right.style.backgroundColor = down.style.backgroundColor = "black";

    sendCommand("reverse");
}

function draw(distance, angle) {
    const canvas = document.getElementById("canvas");
    const ctx = canvas.getContext("2d");

    if(Number(distance) == 0) distance = '50';

    let r = Math.min(Number(distance), 50) * 6;

    let x1 = r * Math.cos(angle * Math.PI / 180);
    let y1 = r * Math.sin(angle * Math.PI / 180);

    let x2 = r * Math.cos((angle - 1.5) * Math.PI / 180);
    let y2 = r * Math.sin((angle - 1.5) * Math.PI / 180);

    if(angle == 180 || angle == 0){
        ctx.clearRect(0, 0, canvas.width, canvas.height); // Clear old drawing
    }
    /*
    ctx.fillStyle = `rgb(0 0 0 / ${distance}%)`;
    ctx.fillRect(canvas.width/2, 0, 5, canvas.height);
    */

    ctx.beginPath();
    ctx.moveTo(canvas.width / 2, canvas.height / 2);//middle
    ctx.lineTo(canvas.width / 2 +x1, canvas.height / 2 -y1);
    ctx.lineTo(canvas.width / 2 +x2, canvas.height / 2 -y2);
    ctx.moveTo(canvas.width / 2 , canvas.height / 2);
    ctx.closePath();
    ctx.fillStyle = "green";
    ctx.fill();


    let x3 = (1000 - r) * Math.cos((angle - 1.5) * Math.PI / 180);
    let y3 = (1000 - r) * Math.sin((angle - 1.5) * Math.PI / 180);
    let x4 = (1000 - r) * Math.cos((angle) * Math.PI / 180);
    let y4 = (1000 - r) * Math.sin((angle) * Math.PI / 180);
    ctx.beginPath();
    ctx.moveTo(canvas.width / 2 +x1, canvas.height / 2 -y1);
    ctx.lineTo(canvas.width / 2 +x2, canvas.height / 2 -y2);
    ctx.lineTo(canvas.width / 2 +x3, canvas.height / 2 -y3);
    ctx.lineTo(canvas.width / 2 +x4, canvas.height / 2 -y4);
    ctx.moveTo(canvas.width / 2 +x1, canvas.height / 2 -y1);
    ctx.closePath();
    ctx.fillStyle = "red";
    ctx.fill();
}