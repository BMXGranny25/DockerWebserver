import os
import argparse
from typing import Dict, List, Tuple

import torch
import timm
from torch.utils.data import DataLoader
from torchvision import datasets, transforms
#python eval_resnet50.py --checkpoint "W:\Downloads\Ai\Resnet50\Resnet50\resnet50\src\training\models\checkpoint_hp_2_final.pth" --data "W:/Downloads/Ai/testresnetImage" --batch-size 16 --num-workers 0 --save-misclassified "misclassified.txt"
import torch.nn as nn
import timm

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
                    x, weight_svt, self.conv.bias,
                    stride=self.conv.stride, padding=self.conv.padding
                )
        return self.conv(x)

def modify_resnet50_for_svt(resnet_model, svt_enabled=True):
    resnet_model.conv1 = CustomConvLayer(3, 64, kernel_size=7, stride=2, padding=3, svt_enabled=svt_enabled)
    for layer in resnet_model.layer1:
        layer.conv2 = CustomConvLayer(64, 64, kernel_size=3, stride=1, padding=1, svt_enabled=svt_enabled)
    return resnet_model

def build_transform():
    # match your validation/test transforms (no random augmentations)
    return transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406],
                             [0.229, 0.224, 0.225]),
    ])


def load_model(checkpoint_path: str, num_classes: int, device: torch.device):
    # Build the same architecture your training script saved
    model = timm.create_model("resnet50", pretrained=False)
    model.fc = nn.Linear(model.fc.in_features, num_classes)

    # You did NOT use --svt, so keep it disabled
    model = modify_resnet50_for_svt(model, svt_enabled=False)

    ckpt = torch.load(checkpoint_path, map_location=device)
    model.load_state_dict(ckpt["model_state_dict"])  # should now match

    model.to(device)
    model.eval()
    return model


@torch.no_grad()
def evaluate(
    model,
    dataset: datasets.ImageFolder,
    device: torch.device,
    batch_size: int = 32,
    num_workers: int = 0,
) -> Tuple[float, List[List[int]], Dict[str, float], List[Tuple[str, int, int, float]]]:
    """
    Returns:
      - accuracy
      - confusion matrix [[tn, fp],[fn,tp]] generalized to NxN
      - per-class accuracy dict
      - misclassified list: (filepath, true_idx, pred_idx, confidence)
    """
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=False,
                        num_workers=num_workers, pin_memory=torch.cuda.is_available())

    n = len(dataset.classes)
    cm = [[0 for _ in range(n)] for _ in range(n)]
    correct = 0
    total = 0

    misclassified = []

    # dataset.imgs is list of (path, class_idx) in same order as loader when shuffle=False
    # We'll track global index to map batch items back to file paths
    global_i = 0

    for x, y in loader:
        x = x.to(device)
        y = y.to(device)

        logits = model(x)
        probs = torch.softmax(logits, dim=1)
        conf, pred = torch.max(probs, dim=1)

        for j in range(len(y)):
            t = int(y[j].item())
            p = int(pred[j].item())
            cm[t][p] += 1
            total += 1
            if t == p:
                correct += 1
            else:
                path, _ = dataset.imgs[global_i + j]
                misclassified.append((path, t, p, float(conf[j].item())))

        global_i += len(y)

    acc = correct / total if total else 0.0

    per_class_acc = {}
    for i, name in enumerate(dataset.classes):
        row_sum = sum(cm[i])
        per_class_acc[name] = (cm[i][i] / row_sum) if row_sum else 0.0

    return acc, cm, per_class_acc, misclassified


def print_confusion_matrix(cm: List[List[int]], class_names: List[str]):
    # simple pretty print
    header = "true\\pred".ljust(12) + "".join(name.rjust(10) for name in class_names)
    print(header)
    for i, row in enumerate(cm):
        line = class_names[i].ljust(12) + "".join(str(v).rjust(10) for v in row)
        print(line)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoint", required=True, help="Path to checkpoint .pth")
    ap.add_argument("--data", required=True, help="Path to test folder (ImageFolder structure)")
    ap.add_argument("--batch-size", type=int, default=32)
    ap.add_argument("--num-workers", type=int, default=0, help="Use 0 on Windows for clean behavior")
    ap.add_argument("--cpu", action="store_true")
    ap.add_argument("--save-misclassified", default=None,
                    help="Optional path to save a text file listing misclassified images")
    args = ap.parse_args()

    device = torch.device("cpu" if args.cpu or not torch.cuda.is_available() else "cuda:0")

    tfm = build_transform()
    dataset = datasets.ImageFolder(args.data, transform=tfm)

    num_classes = len(dataset.classes)
    print(f"Found classes: {dataset.classes}")
    print(f"Class -> index mapping: {dataset.class_to_idx}")

    model = load_model(args.checkpoint, num_classes=num_classes, device=device)

    acc, cm, per_class_acc, misclassified = evaluate(
        model, dataset, device,
        batch_size=args.batch_size,
        num_workers=args.num_workers,
    )

    print("\nResults")
    print(f"Accuracy: {acc*100:.2f}%")
    print("Per-class accuracy:")
    for k, v in per_class_acc.items():
        print(f"  {k}: {v*100:.2f}%")

    print("\nConfusion matrix (rows=true, cols=pred):")
    print_confusion_matrix(cm, dataset.classes)

    print(f"\nMisclassified: {len(misclassified)}")
    if args.save_misclassified:
        with open(args.save_misclassified, "w", encoding="utf-8") as f:
            for path, t, p, conf in misclassified:
                f.write(f"{path}\ttrue={dataset.classes[t]}\tpred={dataset.classes[p]}\tconf={conf:.4f}\n")
        print(f"Saved misclassified list to: {args.save_misclassified}")


if __name__ == "__main__":
    main()