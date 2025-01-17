import warnings
from collections import OrderedDict
import flwr as fl
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader
from torchvision.datasets import CIFAR10
from torchvision.transforms import Compose, Normalize, ToTensor
from tqdm import tqdm
import argparse
from dataset_utils import get_train_loader,get_test_loader, get_train_loader_itemwise


# #############################################################################
# 1. Regular PyTorch pipeline: nn.Module, train, test, and DataLoader
# #############################################################################

warnings.filterwarnings("ignore", category=UserWarning)
DEVICE = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
print(DEVICE)


class Net(nn.Module):
    """Model (simple CNN adapted from 'PyTorch: A 60 Minute Blitz')"""

    def __init__(self) -> None:
        super(Net, self).__init__()
        self.conv1 = nn.Conv2d(3, 6, 5)
        self.pool = nn.MaxPool2d(2, 2)
        self.conv2 = nn.Conv2d(6, 16, 5)
        self.fc1 = nn.Linear(16 * 5 * 5, 120)
        self.fc2 = nn.Linear(120, 84)
        self.fc3 = nn.Linear(84, 10)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.pool(F.relu(self.conv1(x)))
        x = self.pool(F.relu(self.conv2(x)))
        x = x.view(-1, 16 * 5 * 5)
        x = F.relu(self.fc1(x))
        x = F.relu(self.fc2(x))
        return self.fc3(x)


def train(net, trainloader, epochs):
    """Train the model on the training set."""
    criterion = torch.nn.CrossEntropyLoss()
    optimizer = torch.optim.SGD(net.parameters(), lr=0.001, momentum=0.9)
    for _ in range(epochs):
        for images, labels in tqdm(trainloader):
            optimizer.zero_grad()
            criterion(net(images.to(DEVICE)), labels.to(DEVICE)).backward()
            optimizer.step()


def test(net, testloader):
    """Validate the model on the test set."""
    criterion = torch.nn.CrossEntropyLoss()
    correct, total, loss = 0, 0, 0.0
    with torch.no_grad():
        for images, labels in tqdm(testloader):
            outputs = net(images.to(DEVICE))
            labels = labels.to(DEVICE)
            loss += criterion(outputs, labels).item()
            total += labels.size(0)
            correct += (torch.max(outputs.data, 1)[1] == labels).sum().item()
    return loss / len(testloader.dataset), correct / total


def load_custom_dataset():
    #Images size 32 by 32
    batch_size = 32
    print(f'Loading data from {datapath}')
    if dp:
        print("Loading data with differential privacy..")
        train_loader = get_train_loader_itemwise(batch_size, './data/dp_iterate/trian/')
    else:
        train_loader = get_train_loader(batch_size, datapath + f'/train/cifar_train.pt')
    test_loader = get_test_loader(batch_size, datapath + f'/test/cifar_test.pt')
    return train_loader, test_loader


def load_dataset():
    """Load CIFAR-10 (training and test set)."""
    print(f'Loading data from {datapath}')
    trf = Compose([ToTensor(), Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5))])
    trainset = CIFAR10(datapath, train=True, download=download_flag , transform=trf)
    testset = CIFAR10(datapath, train=False, download=download_flag , transform=trf)
    return DataLoader(trainset, batch_size=32, shuffle=True), DataLoader(testset)


# #############################################################################
# 2. Federation of the pipeline with Flower
# #############################################################################

# Load model and data (simple CNN, CIFAR-10)
parser = argparse.ArgumentParser(description="Launches FL clients.")
parser.add_argument('-cid',"--cid", type=int, default=0, help="Define Client_ID",)
parser.add_argument('-server',"--server", default="0.0.0.0", help="Server Address",)
parser.add_argument('-port',"--port", default="8080", help="Server Port",)
parser.add_argument('-data', "--data", default="./data/normal/", help="Dataset source path")
parser.add_argument('-download', "--download", type=bool, default=True, help="Download the dataset or use it from path (-data)")
parser.add_argument('-custom', "--custom", type=bool, default=False, help="Custom dataset")
parser.add_argument('-dataset', "--dataset", default="cifar", help="Describe the dataset")
parser.add_argument('-dp', "--dp", type=bool, default=False, help="Using DP")
args = vars(parser.parse_args())
cid = args['cid']
server = args['server']
port = args['port']
datapath = args['data']
download_flag = args['download']
custom = args['custom']
dataset = args['dataset']
dp = args['dp']
net = Net().to(DEVICE)
if custom:
    trainloader, testloader = load_custom_dataset()
else:
    ttrainloader, testloader = load_dataset()


# Define Flower client
class FlowerClient(fl.client.NumPyClient):
    def get_parameters(self, config):
        return [val.cpu().numpy() for _, val in net.state_dict().items()]

    def set_parameters(self, parameters):
        params_dict = zip(net.state_dict().keys(), parameters)
        state_dict = OrderedDict({k: torch.tensor(v) for k, v in params_dict})
        net.load_state_dict(state_dict, strict=True)

    def fit(self, parameters, config):
        self.set_parameters(parameters)
        train(net, trainloader, epochs=1)
        return self.get_parameters(config={}), len(trainloader.dataset), {}

    def evaluate(self, parameters, config):
        self.set_parameters(parameters)
        loss, accuracy = test(net, testloader)
        return loss, len(testloader.dataset), {"accuracy": accuracy}

print(f"Subscribing to FL server {server} on port {port}...")
# Start Flower client
fl.client.start_numpy_client(
    server_address=f"{server}:{port}",
    client=FlowerClient(),
)
