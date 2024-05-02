import torch
from pathlib import Path
import os
from torch.utils.data import DataLoader, TensorDataset, Dataset # Helps to create minibatches
import torchvision.datasets as datasets
import torchvision.transforms as transforms
import matplotlib.pyplot as plt
import time
import argparse


class CustomImageDataset(Dataset):
    def __init__(self, path, transform=None, target_transform=None):
        self.load_dir = Path(path)
        print(self.load_dir)
        # Load your data from the specified file or source
        self.data = torch.load(self.load_dir)

    def __len__(self):
        # Return the total number of samples in your data
        return len(self.data)

    def __getitem__(self, idx):
        # Return a single data sample at the given index
        return self.data[idx]


class CustomImageLabelDataset(Dataset):
    def __init__(self, path):
        self.data_dir = path
        self.file_list = [f for f in os.listdir(path) if f.endswith('.pt')]

    def __len__(self):
        return len(self.file_list)

    def __getitem__(self, idx):
        file_path = os.path.join(self.data_dir, self.file_list[idx])
        data_dict = torch.load(file_path)
        image = data_dict['image']
        label = data_dict['label']
        return image, label


def get_train_loader(batch, path):
    dataset_train = CustomImageDataset(path= path)
    print(f'Train data len {len(dataset_train)}')
    trainloader = torch.utils.data.DataLoader(dataset=dataset_train, batch_size=batch, shuffle=False)
    return trainloader


def get_train_loader_itemwise(batch, path):
    dataset_train = CustomImageLabelDataset(path= path)
    print(f'Train data len {len(dataset_train)}')
    trainloader = torch.utils.data.DataLoader(dataset=dataset_train, batch_size=batch, shuffle=False)
    return trainloader


def get_test_loader(batch, path):
    dataset_test = CustomImageDataset(path=path)
    print(f'Test data len {len(dataset_test)}')
    testloader = torch.utils.data.DataLoader(dataset=dataset_test, batch_size=batch, shuffle=False)
    return testloader


def load_cifar_dataset():
    print("Loading data")
    transform = transforms.Compose(
        [transforms.ToTensor(), transforms.Normalize(mean=(0.4914, 0.4822, 0.4465),std=(0.2023, 0.1994, 0.2010))] # When normalizing you target mean = 0 and std = 1
    )
    #Images size 32 by 32
    train_dataset = datasets.CIFAR10(root='data/', transform=transform, download=True, train=True)
    test_dataset = datasets.CIFAR10(root='data/', transform=transform, download=True, train=False)
    torch.save(test_dataset, 'data/normal/test/cifar_test.pt')
    torch.save(train_dataset, 'data/normal/train/cifar_train.pt')