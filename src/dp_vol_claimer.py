import torch
import os
from torch.utils.data import DataLoader, TensorDataset, Dataset # Helps to create minibatches
from functools import partial
import matplotlib.pyplot as plt
import time
import argparse
from diffprivlib.mechanisms import Laplace , LaplaceBoundedDomain
from tqdm import tqdm
from dataset_utils import CustomImageDataset, load_cifar_dataset
import multiprocessing

DATA_DP_ROOT = "data/dp/"
batch_size = 32

def load_dp_data(epsilon, datapath,dataset_type):
    #Images size 32 by 32
    train_dataset = CustomImageDataset(path = datapath+f'/normal/train/{dataset_type}_train.pt')
    print(len(train_dataset))
    #plot(train_dataset)
    #noisy_dataset = dp_data_loader(train_dataset, epsilon)
    #train_dataset = noisy_dataset
    dp_data_loader_itemwise(train_dataset, epsilon)
    test_dataset = CustomImageDataset(path = datapath+f'/normal/test/{dataset_type}_test.pt')
    num_examples = {"trainset": len(train_dataset), "testset": len(test_dataset)}
    directory = os.path.dirname(datapath+"/dp/")
    print(directory)
    if not os.path.exists(directory):
        os.makedirs(directory+"/test/")
        os.makedirs(directory+"/train/")
    # Save dp_dataset using torch.save
    torch.save(test_dataset, datapath+'/dp/test/cifar_test.pt')
    #torch.save(train_dataset, datapath+'/dp/train/cifar_train.pt')
    print(num_examples)
    return num_examples, train_dataset


def dp_loader_pixel(dataset, epsilon, delta = 0, sensitivity = 0):
    # Create lists to hold noisy images and labels
    noisy_images = []
    labels = []
    l = Laplace(epsilon=epsilon, delta= delta, sensitivity=sensitivity)
    for i in tqdm(range(len(dataset))):
        image, label = dataset[i]
        image_with_noise = torch.empty_like(image)
        # Add Laplace noise to each pixel individually
        for i in range(image.size(1)):
            for j in range(image.size(2)):
                pixel = image[0, i, j]
                noisy_pixel = pixel + l.randomise(pixel.item())
                image_with_noise[0, i, j] = noisy_pixel
        dp_image = torch.clamp(image_with_noise, 0, 1)
        # Append noisy image and label to their respective lists
        noisy_images.append(dp_image)
        labels.append(label)
    # Create the TensorDataset from noisy_images and labels
    dp_dataset = TensorDataset(torch.stack(noisy_images), torch.tensor(labels))
    return dp_dataset


def dp_loader_vectorised(dataset, epsilon, delta = 0, sensitivity = 0):
    print("Creating DP data..")
    # Create lists to hold noisy images and labels
    noisy_images = []
    labels = []
    l = Laplace(epsilon=epsilon, delta= delta, sensitivity=sensitivity)
    for i in tqdm(range(len(dataset))):
        image, label = dataset[i]
        mean = torch.mean(image)
        noise = l.randomise(mean.item())
        #image_shape = image.shape[-2:]
        #laplace_noise = noise * torch.eye(image_shape[0], image_shape[1])
        #laplace_noise = noise * torch.zeros_like(image)
        #laplace_noise = noise * torch.ones_like(image)
        laplace_noise = noise * torch.randn_like(image)
        image_with_noise = image + laplace_noise
        dp_image = torch.clamp(image_with_noise, 0, 1)
        # Append noisy image and label to their respective lists
        noisy_images.append(dp_image)
        labels.append(label)
    # Create the TensorDataset from noisy_images and labels
    dp_dataset = TensorDataset(torch.stack(noisy_images), torch.tensor(labels))
    return dp_dataset


def dp_loader_worker(item, epsilon, delta, sensitivity):
    image, label = item
    mean = torch.mean(image)
    l = Laplace(epsilon=epsilon, delta=delta, sensitivity=sensitivity)
    noise = l.randomise(mean.item())
    laplace_noise = noise * torch.randn_like(image)
    image_with_noise = image + laplace_noise
    dp_image = torch.clamp(image_with_noise, 0, 1)
    return dp_image, label


def dp_loader_vectorised_parallelised(dataset, epsilon, delta=0, sensitivity=0):
    print("Creating DP data..")
    # Create a pool of worker processes (adjust the number of processes as needed)
    pool = multiprocessing.Pool(processes=multiprocessing.cpu_count())
    # Define a partial function for worker
    worker_func = partial(dp_loader_worker, epsilon=epsilon, delta=delta, sensitivity=sensitivity)
    # Use multiprocessing to parallelize the workload
    results = list(tqdm(pool.imap(worker_func, dataset), total=len(dataset)))
    pool.close()
    pool.join()
    noisy_images, labels = zip(*results)
    # Create the TensorDataset from noisy_images and labels
    dp_dataset = TensorDataset(torch.stack(noisy_images), torch.tensor(labels))
    return dp_dataset


def dp_data_loader(dataset, epsilon, delta = 0, sensitivity = 0, batch_size = 8):
    data_loader = DataLoader(dataset, batch_size=batch_size, shuffle=False)
    l = Laplace(epsilon=epsilon, delta=delta, sensitivity=sensitivity)
    noisy_images = []
    labels = []
    # Iterate over the DataLoader
    for batch in tqdm(data_loader):
        images, batch_labels = batch
        # Calculate noisy images for this batch
        batch_mean = torch.mean(images, dim=(1, 2, 3))
        batch_noise = l.randomise(torch.mean(batch_mean).item())
        laplace_noise = batch_noise * torch.randn_like(images)
        images_with_noise = images + laplace_noise
        dp_images = torch.clamp(images_with_noise, 0, 1)
        # Append noisy images and labels to their respective lists
        noisy_images.append(dp_images)
        labels.append(batch_labels)

    # Create the TensorDataset from noisy_images and labels
    noisy_images = torch.cat(noisy_images, dim=0)
    labels = torch.cat(labels, dim=0)
    dp_dataset = TensorDataset(noisy_images, labels)
    return dp_dataset


def dp_data_loader_itemwise(dataset, epsilon, delta = 0, sensitivity = 0, batch_size = 4, path ='data/dp_iterate/trian/'):
    print('processing per batch and itemwise')
    data_loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)
    l = Laplace(epsilon=epsilon, delta=delta, sensitivity=sensitivity)
    os.makedirs(path, exist_ok=True)
    # Iterate over the DataLoader
    for batch_idx, batch in enumerate(tqdm(data_loader)):
        images, labels = batch
        for i in range(len(images)):
            image = images[i]
            label = labels[i]
            mean = torch.mean(image)
            noise = l.randomise(mean.item())
            laplace_noise = noise * torch.randn_like(image)
            image_with_noise = image + laplace_noise
            dp_image = torch.clamp(image_with_noise, 0, 1)
            data_dict = {
                "image": dp_image,
                "label": label
            }
            data_filename = os.path.join(path, f"data_{batch_idx * batch_size + i}.pt")
            torch.save(data_dict, data_filename)

def plot(dataset):
    figure = plt.figure(figsize=(8, 8))
    cols, rows = 3, 3
    for i in range(1, cols * rows + 1):
        #sample_idx = torch.randint(len(data), size=(1,)).item()
        sample_idx = i
        img, label = dataset[sample_idx]
        figure.add_subplot(rows, cols, i)
        #plt.title(label.item())
        plt.axis("off")
        plt.imshow(img.permute(1, 2, 0))
    plt.show()


def main():
    parser = argparse.ArgumentParser(description="Launches DP claimers.")
    parser.add_argument("--cid", type=int, default=0, help="Define Client_ID",)
    parser.add_argument("--dp", type=float, default=0.5, help="Server Address",)
    parser.add_argument("--data", default="./data", help="Dataset source path")
    parser.add_argument("--dataset", default="cifar", help="Describe the dataset")
    args = parser.parse_args()
    dp_ep= args.dp
    datapath = args.data
    dataset = args.dataset
    _, dp_dataset = load_dp_data(dp_ep, datapath, dataset)
    #plot(dp_dataset)


if __name__ == '__main__':
    start_time = time.time()
    main()
    print(time.strftime('%H:%M:%S', time.gmtime(time.time() - start_time)))