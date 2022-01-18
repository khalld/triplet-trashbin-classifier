from torch.utils import data # necessary to create a map-style dataset https://pytorch.org/docs/stable/data.html
from os.path import splitext, join
from PIL import Image
import numpy as np
import pandas as pd
from torchvision import transforms
import matplotlib.pyplot as plt
from torch.utils.data import DataLoader
import torch

def reverse_norm(image):
    """Allow to show a normalized image"""
    
    image = image-image.min()
    return image/image.max()

class TrashbinDataset(data.Dataset): # data.Dataset https://pytorch.org/docs/stable/_modules/torch/utils/data/dataset.html#Dataset
    """ A map-style dataset class used to manipulate a dataset composed by:
        image path of trashbin and associated label that describe the available capacity of the trashbin
            0 : empty trashbin
            1 : half trashbin
            2 : full trashbin

        Attributes
        ----------
        data : str
            path of csv file
        transform : torchvision.transforms

        Methods
        -------
        __len__()
            Return the length of the dataset

        __getitem__(i)
            Return image, label of i element of dataset  
    """

    def __init__(self, csv: str=None, transform: transforms=None, path_gdrive: str=''):
        """ Constructor of the dataset
            Parameters
            ----------
            csv : str
            path of the dataset

            transform : torchvision.transforms
            apply transform to the dataset

            path_gdrive: str
            necessary to apply the prepath in gdrive witouth changing csv

            Raises
            ------
            NotImplementedError
                If no path is passed is not provided a default dataset, default to load the image use only the csv file
        """
        
        if csv is None:
            raise NotImplementedError("No default dataset is provided")
        if splitext(csv)[1] != '.csv':
            raise NotImplementedError("Only .csv files are supported")
        
        self.data = pd.read_csv(csv)        # import from csv using pandas
        self.data = self.data.iloc[np.random.permutation(len(self.data))]       # random auto-permutation of the data
        self.transform = transform
        self.path_gdrive = path_gdrive

    def __len__(self):
        """ Return length of dataset """
        return len(self.data)

    def __getitem__(self, i=None):
        """ Return the i-th item of dataset

            Parameters
            ----------
            i : int
            i-th item of dataset

            Raises
            ------
            NotImplementedError
            If i is not a int
        """
        if i is None:
            raise NotImplementedError("Only int type is supported for get the item. None is not allowed")
        
        im_path, im_label = self.data.iloc[i]['image'], self.data.iloc[i].label
        im = Image.open(join(self.path_gdrive,im_path))        # Handle image with Image module from Pillow https://pillow.readthedocs.io/en/stable/reference/Image.html
        if self.transform is not None:
            im = self.transform(im)
        return im, im_label

if __name__ == "__main__":

    PATH_DST = join('dataset', 'all_labels.csv')
    PATH_GDRIVE = ''
    NUM_WORKERS = 8
    BATCH_SIZE = 1024

    dataset_df = pd.read_csv(PATH_DST)

    dic_dst = {
        0: 'empty',
        1: 'half',
        2: 'full'
    }

    # ***** Show some part of dataframe *****
    # plt.figure(figsize=(15,8))
    # for ii, i in enumerate(np.random.choice(range(len(dataset_df)), 10)):
    #     plt.subplot(2,5,ii+1)
    #     plt.title("Class: %s" % dic_dst[dataset_df['label'][i]])
    #     plt.imshow(plt.imread(dataset_df['image'][i]),cmap='gray')
    # plt.show()


    # ***** Calculate mean and std *****
    # means = np.zeros(3)
    # stdevs = np.zeros(3)

    # for data in dataset_df:
    #     img = data[0]
    #     for i in range(3):
    #         img = np.asarray(img)
    #         means[i] += img[i, :, :].mean()
    #         stdevs[i] += img[i, :, :].std()

    # means = np.asarray(means) / dataset_df.__len__()
    # stdevs = np.asarray(stdevs) / dataset_df.__len__()
    # print("{} : normMean = {}".format(type, means))
    # print("{} : normstdevs = {}".format(type, stdevs))

    dataset = TrashbinDataset('dataset/all_labels.csv')

    print("dataset len: %i" % len(dataset))
    # print(dataset.data)   # verifico la permutazione su tutte le label già implementata con il resto della classe

    # splitto il dataset in training e test senza considerare il validaiton
    train_size = int(0.8 * len(dataset))
    test_size = len(dataset) - train_size
    #validation_size =
    dataset_train, dataset_test = torch.utils.data.random_split(dataset, [train_size, test_size])

    print("train_size: %i" % (len(dataset_train)))
    print("test_size: %i" % (len(dataset_test)))

    # dataset_loader = DataLoader(dataset, batch_size=32)

    dataset_train_loader = DataLoader(dataset_train, batch_size=BATCH_SIZE, num_workers=NUM_WORKERS, shuffle=True)
    dataset_test_loader = DataLoader(dataset_test, batch_size=BATCH_SIZE, num_workers=NUM_WORKERS)

    # print(len(dataset_loader))
