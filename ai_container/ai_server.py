import asyncio
import json
import logging
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path

import torch
import torch.nn as nn
import timm
import websockets
from fastapi import FastAPI, UploadFile, File
from PIL import Image
from torchvision import transforms

# -----------------------------
# Logging
# -----------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ai_server")

# -----------------------------
# Config
# -----------------------------
MODEL_PATH = os.environ.get("MODEL_PATH", "checkpoint_hp_1_epoch_10.pth")
CLASS_NAMES = ["bad", "good"]  # swap if needed
WS_URL = os.environ.get("WS_URL", "ws://192.168.4.1/ws")
TEMP_DIR = Path(os.environ.get("TEMP_DIR", "TempImage"))
RECONNECT_DELAY = float(os.environ.get("RECONNECT_DELAY", "2"))

device = torch.device("cpu")
TEMP_DIR.mkdir(parents=True, exist_ok=True)

# -----------------------------
# Model helpers
# -----------------------------
def is_svt_feasible(filter_matrix, threshold=0.1):
    _, s, _ = torch.svd(filter_matrix)
    return torch.min(s) > threshold


class CustomConvLayer(nn.Module):
    def __init__(
        self,
        in_channels,
        out_channels,
        kernel_size,
        stride=1,
        padding=0,
        bias=True,
        svt_enabled=True,
    ):
        super().__init__()
        self.conv = nn.Conv2d(
            in_channels, out_channels, kernel_size, stride, padding, bias=bias
        )
        self.svt_enabled = svt_enabled

    def forward(self, x):
        if self.svt_enabled:
            weight = self.conv.weight.data
            if is_svt_feasible(weight.view(weight.size(0), -1)):
                u, s, v = torch.svd(weight.view(weight.size(0), -1))
                weight_svt = torch.matmul(u, torch.diag(s)).matmul(v.t())
                weight_svt = weight_svt.view(weight.size())
                return nn.functional.conv2d(
                    x,
                    weight_svt,
                    self.conv.bias,
                    stride=self.conv.stride,
                    padding=self.conv.padding,
                )
        return self.conv(x)


def modify_resnet50_for_svt(resnet_model, svt_enabled=False):
    resnet_model.conv1 = CustomConvLayer(
        3, 64, kernel_size=7, stride=2, padding=3, svt_enabled=svt_enabled
    )

    for layer in resnet_model.layer1:
        layer.conv2 = CustomConvLayer(
            64, 64, kernel_size=3, stride=1, padding=1, svt_enabled=svt_enabled
        )

    return resnet_model


def load_model(checkpoint_path: str, device: torch.device, num_classes: int = 2):
    model = timm.create_model("resnet50", pretrained=False)
    model.fc = nn.Linear(model.fc.in_features, num_classes)
    model = modify_resnet50_for_svt(model, svt_enabled=False)

    ckpt = torch.load(checkpoint_path, map_location=device)
    state_dict = ckpt["model_state_dict"] if "model_state_dict" in ckpt else ckpt
    model.load_state_dict(state_dict)

    model.to(device)
    model.eval()
    return model


def build_transform():
    return transforms.Compose(
        [
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(
                [0.485, 0.456, 0.406],
                [0.229, 0.224, 0.225],
            ),
        ]
    )


model = load_model(MODEL_PATH, device=device, num_classes=2)
transform = build_transform()


@torch.no_grad()
def predict_pil_image(image: Image.Image):
    x = transform(image.convert("RGB")).unsqueeze(0).to(device)
    logits = model(x)
    probs = torch.softmax(logits, dim=1)
    conf, pred = torch.max(probs, dim=1)

    pred_idx = int(pred.item())
    confidence = float(conf.item())
    label = CLASS_NAMES[pred_idx]

    return label, confidence


def predict_file(image_path: Path):
    image = Image.open(image_path).convert("RGB")
    return predict_pil_image(image)


# -----------------------------
# WebSocket listener
# -----------------------------
async def handle_binary_image(websocket, image_bytes: bytes):
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    temp_file = TEMP_DIR / f"image_{int(time.time() * 1000)}.jpg"

    with open(temp_file, "wb") as f:
        f.write(image_bytes)

    logger.info("Saved image to %s (%d bytes)", temp_file, len(image_bytes))
    print("Image saved:", temp_file)

    try:
        label, confidence = predict_file(temp_file)
        logger.info("Prediction: %s (%.4f)", label, confidence)
        if (round(confidence,4)>.75):
            result_msg = label + "," + str(round(confidence),4)

            # changed to send oly if confidence is above 75%
            # changed message to send as result,confiedence
            # ex good,0.8753
            
        #result_msg = {
            #"type": "classification",
            #"prediction": label,
            #"confidence": round(confidence, 4),
        #}
        # if confiedence over 75% send yes or no
        await websocket.send(result_msg)#json.dumps(result_msg))
        logger.info("Sent result back: %s", result_msg)

    except Exception as e:
        logger.exception("Prediction failed: %s", e)

    finally:
        try:
            if temp_file.exists():
                temp_file.unlink()
                logger.info("Deleted temp file: %s", temp_file)
        except Exception as e:
            logger.warning("Could not delete temp file %s: %s", temp_file, e)


async def websocket_worker():
    while True:
        try:
            logger.info("Connecting to websocket: %s", WS_URL)

            async with websockets.connect(
                WS_URL,
                max_size=None,
                ping_interval=20,
                ping_timeout=20,
            ) as websocket:
                logger.info("Connected to websocket server")

                async for message in websocket:
                    if isinstance(message, bytes):
                        print("Received image bytes:", len(message))
                        await handle_binary_image(websocket, message)
                    else:
                        logger.info("Received non-binary message: %s", message)

        except Exception as e:
            logger.warning("Websocket connection lost or failed: %s", e)
            logger.info("Reconnecting in %s seconds...", RECONNECT_DELAY)
            await asyncio.sleep(RECONNECT_DELAY)


# -----------------------------
# FastAPI lifespan
# -----------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(websocket_worker())
    logger.info("Started websocket listener task")
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            logger.info("Websocket listener task cancelled")


app = FastAPI(lifespan=lifespan)


# -----------------------------
# Existing test endpoints
# -----------------------------
@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/predict")
async def predict(file: UploadFile = File(...)):
    suffix = os.path.splitext(file.filename)[1] if file.filename else ".jpg"
    temp_path = TEMP_DIR / f"manual_upload{suffix}"

    try:
        with open(temp_path, "wb") as f:
            f.write(await file.read())

        image = Image.open(temp_path).convert("RGB")
        label, confidence = predict_pil_image(image)

        return {
            "prediction": label,
            "confidence": confidence,
        }

    finally:
        if temp_path.exists():
            temp_path.unlink()