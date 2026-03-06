# script that will classify image and send results back to esp32 client
# script will receive one image and needs to return if its good or bad
# script needs model path, folder path, later needs to send resulst back to esp32 websocket
import argparse
import torch
import torch.nn as nn
import timm
from PIL import Image
from torchvision import transforms


def is_svt_feasible(filter_matrix, threshold=0.1):
    u, s, v = torch.svd(filter_matrix)
    return torch.min(s) > threshold


class CustomConvLayer(nn.Module):
    def __init__(self, in_channels, out_channels, kernel_size, stride=1, padding=0, bias=True, svt_enabled=True):
        super().__init__()
        self.conv = nn.Conv2d(in_channels, out_channels, kernel_size, stride, padding, bias=bias)
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

    # IMPORTANT: must match training architecture
    model = modify_resnet50_for_svt(model, svt_enabled=False)

    ckpt = torch.load(checkpoint_path, map_location=device)
    state_dict = ckpt["model_state_dict"] if "model_state_dict" in ckpt else ckpt
    model.load_state_dict(state_dict)

    model.to(device)
    model.eval()
    return model


def build_transform():
    return transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(
            [0.485, 0.456, 0.406],
            [0.229, 0.224, 0.225]
        ),
    ])


@torch.no_grad()
def predict_image(model, image_path: str, device: torch.device, class_names=None):
    if class_names is None:
        class_names = ["bad", "good"]  # change if your training folder order was different

    image = Image.open(image_path).convert("RGB")
    transform = build_transform()
    x = transform(image).unsqueeze(0).to(device)

    logits = model(x)
    probs = torch.softmax(logits, dim=1)
    conf, pred = torch.max(probs, dim=1)

    pred_idx = int(pred.item())
    confidence = float(conf.item())
    label = class_names[pred_idx]

    return label, confidence


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", required=True, help="Path to model checkpoint")
    parser.add_argument("--image", required=True, help="Path to one image")
    parser.add_argument("--cpu", action="store_true")
    args = parser.parse_args()

    device = torch.device("cpu" if args.cpu or not torch.cuda.is_available() else "cuda:0")

    model = load_model(args.checkpoint, device=device, num_classes=2)
    label, confidence = predict_image(model, args.image, device)

    print(f"prediction: {label}")
    print(f"confidence: {confidence:.4f}")


if __name__ == "__main__":
    main()