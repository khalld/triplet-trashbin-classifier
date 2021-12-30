import torch
import random
import numpy as np
from torch import nn
from torchvision.datasets import MNIST
from torchvision import transforms
from torch.utils.data import DataLoader
from os.path import join
from sklearn.metrics import accuracy_score
from torch.optim import SGD
import numpy as np
import pytorch_lightning as pl
from pytorch_lightning.loggers import TensorBoardLogger
from torchvision.utils import make_grid
from sklearn.manifold import TSNE
from matplotlib import pyplot as plt

class AutoencoderFC(pl.LightningModule):
    """Autoencoder Fully Connected
    
    """
    def __init__(self):
        super(AutoencoderFC, self).__init__()

        # l'encoder è un MLP che mappa l'input in un codice di 128 unità dato che l'ultimo livello
        # del MLP non è l'ultimo della rete, inseriamo la funzione di attivazione alla fine del MLP
        self.encoder = nn.Sequential(nn.Linear(784, 256),
                                        nn.ReLU(),
                                        nn.Linear(256, 128),
                                        nn.ReLU())
        
        # il decoder è un MLP che mappa il codice in un output di dimensione uguale all'input
        self.decoder = nn.Sequential(nn.Linear(128,256),
                                    nn.ReLU(),
                                    nn.Linear(256,784))

        self.criterion = nn.MSELoss()
    
    def forward(self, x):
        code = self.encoder(x)
        reconstructed = self.decoder(code)
        # restituisco sia il codice che l'output ricostruito
        return code, reconstructed

    def configure_optimizers(self):
        optimizer = SGD(self.parameters(), lr=0.01, momentum=0.99)
        return optimizer
    
    # questo metodo definisce come effettuare ogni singolo step di training
    def training_step(self, train_batch, batch_idx):
        x, _ = train_batch
        _, reconstructed = self.forward(x)
        loss = self.criterion(x, reconstructed)
        self.log('train/loss', loss)
        return loss
    
    # questo metodo definisce come effettuare ogni singolo step di validation
    def validation_step(self, val_batch, batch_idx):
        x, _ = val_batch
        _, reconstructed = self.forward(x)
        loss = self.criterion(x, reconstructed)
        self.log('val/loss', loss)
        if batch_idx==0:
            return {'inputs':x, 'outputs':reconstructed}

    def validation_epoch_end(self, results):
        images_in = results[0]['inputs'].view(-1,1,28,28)[:50,...]
        images_out = results[0]['outputs'].view(-1,1,28,28)[:50,...]
        self.logger.experiment.add_image('input_images', make_grid(images_in, nrow=10,normalize=True),self.global_step)
        self.logger.experiment.add_image('generated_images', make_grid(images_out, nrow=10, normalize=True),self.global_step)

class AutoencoderConv(pl.LightningModule):
    """Autoencoder basato su convoluzioni
        È tutto uguale ad un autoencoder FC eccetto il
        costruttore e validation_epoch_end
    
    """
    def __init__(self):
        super(AutoencoderConv, self).__init__()

        self.encoder = nn.Sequential(nn.Conv2d(1,16,3, padding=1),
                                        nn.AvgPool2d(2),
                                        nn.ReLU(),
                                        nn.Conv2d(16,8,3, padding=1),
                                        nn.AvgPool2d(2),
                                        nn.ReLU(),
                                        nn.Conv2d(8,4,3, padding=1),
                                        nn.ReLU())
        self.decoder = nn.Sequential(nn.Conv2d(4,8,3, padding=1),
                                        nn.Upsample(scale_factor=2),
                                        nn.ReLU(),
                                        nn.Conv2d(8,16,3, padding=1),
                                        nn.Upsample(scale_factor=2),
                                        nn.ReLU(),
                                        nn.Conv2d(16,1,3, padding=1))
        # loss utilizzata per il training
        self.criterion = nn.MSELoss()
    
    def forward(self, x):
        code = self.encoder(x)
        reconstructed = self.decoder(code)
        # restituisco sia il codice che l'output ricostruito
        return code, reconstructed

    def configure_optimizers(self):
        optimizer = SGD(self.parameters(), lr=0.01, momentum=0.99)
        return optimizer
    
    # questo metodo definisce come effettuare ogni singolo step di training
    def training_step(self, train_batch, batch_idx):
        x, _ = train_batch
        _, reconstructed = self.forward(x)
        loss = self.criterion(x, reconstructed)
        self.log('train/loss', loss)
        return loss
    
    # questo metodo definisce come effettuare ogni singolo step di validation
    def validation_step(self, val_batch, batch_idx):
        x, _ = val_batch
        _, reconstructed = self.forward(x)
        loss = self.criterion(x, reconstructed)
        self.log('val/loss', loss)
        if batch_idx==0:
            return {'inputs':x, 'outputs':reconstructed}

    def validation_epoch_end(self, results):
        images_in = results[0]['inputs'].view(-1,1,28,28)[:50,...]
        images_out = results[0]['outputs'].view(-1,1,28,28)[:50,...]
        self.logger.experiment.add_image('input_images', make_grid(images_in, nrow=10, normalize=True),self.global_step)
        self.logger.experiment.add_image('generated_images', make_grid(images_out, nrow=10, normalize=True),self.global_step)

class DenoisingConvAutoencoder(pl.LightningModule):
    def __init__(self):
        super(DenoisingConvAutoencoder, self).__init__()
        
        self.encoder = nn.Sequential(nn.Conv2d(1,16,3, padding=1),
                                        nn.AvgPool2d(2),
                                        nn.ReLU(),
                                        nn.Conv2d(16,8,3, padding=1),
                                        nn.AvgPool2d(2),
                                        nn.ReLU(),
                                        nn.Conv2d(8,4,3, padding=1),
                                        nn.ReLU())

        self.decoder = nn.Sequential(nn.Conv2d(4,8,3, padding=1),
                                        nn.Upsample(scale_factor=2),
                                        nn.ReLU(),
                                        nn.Conv2d(8,16,3, padding=1),
                                        nn.Upsample(scale_factor=2),
                                        nn.ReLU(),
                                        nn.Conv2d(16,1,3, padding=1))

        self.criterion = nn.MSELoss()

    def forward(self, x, perturb=False):
        # utilizziamo un parametro perturb per stabilire
        # se l'input va perturbato oppure no
        if perturb:
            #Aggiungiamo del rumore random compreso tra -0.5 e 0.5 #moltiplichiamo per un fattore di rumore che indica quanto #il rumore deve essere presente nell'immagine finale
            noise_factor = 0.5
            x = x + (torch.randn_like(x)-0.5) * noise_factor

        code = self.encoder(x)
        reconstructed = self.decoder(code) #restituiamo anche l'immagine perturbata #tornerà utile per le visualizzazioni
        return code, reconstructed, x
    
    # questo metodo definisce l'optimizer
    def configure_optimizers(self):
        optimizer = SGD(self.parameters(), lr=0.01, momentum=0.99)
        return optimizer
    
    # questo metodo definisce come effettuare ogni singolo step di training
    def training_step(self, train_batch, batch_idx):
        x, _ = train_batch
        _, reconstructed, perturbed = self.forward(x, perturb=True)
        loss = self.criterion(perturbed, reconstructed)
        self.log('train/loss', loss)
        return loss
    
    # questo metodo definisce come effettuare ogni singolo step di validation
    def validation_step(self, val_batch, batch_idx):
        x, _ = val_batch
        _, reconstructed, perturbed = self.forward(x, perturb=True)
        loss = self.criterion(perturbed, reconstructed)
        
        self.log('val/loss', loss)
        if batch_idx == 0:
            return {'inputs':x, 'perturbed': perturbed, 'outputs':reconstructed}
    
    def validation_epoch_end(self, results):
        images_in = results[0]['inputs'].view(-1,1,28,28)[:50,...]
        perturbed = results[0]['perturbed'].view(-1,1,28,28)[:50,...]
        images_out = results[0]['outputs'].view(-1,1,28,28)[:50,...]
        self.logger.experiment.add_image('original_images', make_grid(images_in, nrow=10, normalize=True),self.global_step)
        self.logger.experiment.add_image('perturbed_images', make_grid(perturbed, nrow=10, normalize=True),self.global_step)
        self.logger.experiment.add_image('generated_images', make_grid(images_out, nrow=10, normalize=True),self.global_step)


class SparseConvAutoencoder(pl.LightningModule):
    def __init__(self):
        super(SparseConvAutoencoder, self).__init__()
        self.encoder = nn.Sequential(nn.Conv2d(1,16,3, padding=1),
                                        nn.AvgPool2d(2),
                                        nn.ReLU(),
                                        nn.Conv2d(16,8,3, padding=1),
                                        nn.AvgPool2d(2),
                                        nn.ReLU(),
                                        nn.Conv2d(8,4,3, padding=1),
                                        nn.ReLU())
        self.decoder = nn.Sequential(nn.Conv2d(4,8,3, padding=1),
                                        nn.Upsample(scale_factor=2),
                                        nn.ReLU(),
                                        nn.Conv2d(8,16,3, padding=1),
                                        nn.Upsample(scale_factor=2),
                                        nn.ReLU(),
                                        nn.Conv2d(16,1,3, padding=1))
        #la loss che utilizzeremo per il training
        self.criterion = nn.MSELoss()
        self.l1 = nn.L1Loss()
        
        self.s = 0.05
        self.beta = 0.5

    def forward(self, x):
        code = self.encoder(x)
        reconstructed = self.decoder(code)
        return code, reconstructed
    # questo metodo definisce l'optimizer

    def configure_optimizers(self):
        optimizer = SGD(self.parameters(), lr=0.01, momentum=0.99)
        return optimizer


    # questo metodo definisce come effettuare ogni singolo step di training
    def training_step(self, train_batch, batch_idx):
        x, _ = train_batch
        code, reconstructed = self.forward(x)

        #definiamo il vincolo di sparsità mediante loss l1
        sparse_loss = self.l1(torch.ones_like(code)*self.s, code)
        
        #sommiamo la loss MSE alla loss di sparsità moltiplicata per beta
        loss = self.criterion(x, reconstructed) + self.beta * sparse_loss
        self.log('train/loss', loss)
        return loss

    # questo metodo definisce come effettuare ogni singolo step di validation
    def validation_step(self, val_batch, batch_idx):
        x, _ = val_batch
        _, reconstructed = self.forward(x)
        loss = self.criterion(x, reconstructed)
        self.log('val/loss', loss)
        if batch_idx==0:
            return {'inputs':x, 'outputs':reconstructed}


    def validation_epoch_end(self, results):
        images_in = results[0]['inputs'].view(-1,1,28,28)[:50,...]
        images_out = results[0]['outputs'].view(-1,1,28,28)[:50,...]
        self.logger.experiment.add_image('input_images', make_grid(images_in, nrow=10,normalize=True),self.global_step) 
        self.logger.experiment.add_image('generated_images', make_grid(images_out, nrow=10, normalize=True),self.global_step)

def extract_codes(model, loader):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device)
    codes, labels = [], []
    for batch in loader:
        x = batch[0].to(device)
        code, *_ = model(x)
        code = code.detach().to('cpu').numpy()
        labels.append(batch[1])
        codes.append(code)
    return np.concatenate(codes), np.concatenate(labels)

def make_TSNE(autoencoder: pl.LightningModule, test_loader: DataLoader) -> None:
    codes, labels = extract_codes(autoencoder, test_loader)
    print(codes.shape, labels.shape)

    # trasformo le mappe di feature in vettori monodimensionali e seleziono un sottoinsieme di dati
    selected_codes = np.random.choice(len(codes),1000)
    codes = codes.reshape(codes.shape[0],-1)
    codes = codes[selected_codes]
    labels = labels[selected_codes]
    print(codes.shape)

    # trasformo i dati mediante TSNE ed eseguo il plot
    tsne = TSNE(2)
    codes_tsne_conv=tsne.fit_transform(codes)
    plt.figure(figsize=(8,6))
    for c in np.unique(labels):
        plt.plot(codes_tsne_conv[labels==c, 0], codes_tsne_conv[labels==c, 1], 'o', label= c)
    plt.legend()
    plt.show()
