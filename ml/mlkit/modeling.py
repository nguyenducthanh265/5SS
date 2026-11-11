"""Mô hình, dataset và transform dùng chung cho train / evaluate / export (cần torch + torchvision)."""
from __future__ import annotations

from pathlib import Path

import torch
import torch.nn as nn
from PIL import Image
from torch.utils.data import Dataset
from torchvision import models
from torchvision import transforms as T

NORM = {"mean": [0.485, 0.456, 0.406], "std": [0.229, 0.224, 0.225]}


def build_model(backbone, n_classes, pretrained):
    """Trả về (model, head): head là phần được huấn luyện ở giai đoạn đóng băng backbone."""
    w = "DEFAULT" if pretrained else None
    if backbone in ("mobilenet_v3_small", "mobilenet_v3_large"):
        m = getattr(models, backbone)(weights=w)
        m.classifier[-1] = nn.Linear(m.classifier[-1].in_features, n_classes)
        return m, m.classifier
    if backbone == "efficientnet_b0":
        m = models.efficientnet_b0(weights=w)
        m.classifier[-1] = nn.Linear(m.classifier[-1].in_features, n_classes)
        return m, m.classifier
    if backbone == "resnet18":
        m = models.resnet18(weights=w)
        m.fc = nn.Linear(m.fc.in_features, n_classes)
        return m, m.fc
    raise ValueError(f"Backbone không hỗ trợ: {backbone}")


def make_transform(img_size, augment="none", hflip=True, train=False):
    norm = [T.ToTensor(), T.Normalize(NORM["mean"], NORM["std"])]
    if not train or augment == "none":
        return T.Compose([T.Resize((img_size, img_size)), *norm])
    ops = [T.RandomResizedCrop(img_size, scale=(0.7, 1.0))]
    if hflip:
        ops.append(T.RandomHorizontalFlip())
    if augment == "strong":
        ops += [T.ColorJitter(0.3, 0.3, 0.3), T.RandomRotation(15)]
    return T.Compose([*ops, *norm])


class ImageSet(Dataset):
    def __init__(self, root, paths, labels, transform):
        self.root, self.paths, self.labels, self.transform = Path(root), paths, labels, transform

    def __len__(self):
        return len(self.paths)

    def __getitem__(self, i):
        img = Image.open(self.root / self.paths[i]).convert("RGB")
        return self.transform(img), self.labels[i]


def labels_for(paths, classes):
    """Nhãn lấy từ tên thư mục lớp (phần đầu của đường dẫn tương đối)."""
    idx = {c: i for i, c in enumerate(classes)}
    return [idx[p.split("/")[0]] for p in paths]


def pick_device():
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


@torch.no_grad()
def predict_probs(model, loader, device):
    model.eval()
    out = []
    for x, _ in loader:
        out.append(torch.softmax(model(x.to(device)), dim=1).cpu())
    return torch.cat(out).numpy()
