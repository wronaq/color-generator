"""Model class, to be extended by specific types of models."""
from pathlib import Path
import torch.optim as optim
import torch.nn as nn
import torch
import time
from .early_stopping import EarlyStopping
from color_generator.datasets.dataloaders import DataLoaders


class Model:
    """Base class, to be subclassed by predictors for specific type of data."""

    def __init__(self, network_fn, device="cpu"):

        self.device = device
        self.network = network_fn.to(self.device)
        self._dataloaders = None
        self.name = ""

        self._early_stopping = EarlyStopping(
            patience=1, verbose=True, delta=0.001, path="early_stopping_checkpoint.pt"
        )

    @property
    def weights_filename(self):
        p = Path(__file__).resolve().parents[2] / "weights"
        p.mkdir(parents=True, exist_ok=True)
        return str(p / f"{self.name}_weights.pt")

    def fit(self, dataset, epochs=10, testing=False):

        self._dataloaders = DataLoaders(dataset)
        self.name = (
            f"{self.__class__.__name__}_{self._dataloaders._dataset.__class__.__name__}_"
            f"{self.network.__class__.__name__}_{time.strftime('%Y-%m-%d_%H:%M', time.gmtime())}"
        )

        criterion = self.criterion()
        cs = nn.CosineSimilarity(dim=1)
        train_loader = (
            self._dataloaders.train_loader
            if not testing
            else self._dataloaders._testing_batch
        )

        for epoch in range(epochs):
            self.network.train()
            running_loss = 0.0
            running_cs = 0.0
            for i, batch in enumerate(train_loader):
                # forward and backward propagation
                input_ids = batch["input_ids"].to(self.device)
                attention_mask = batch["attention_mask"].to(self.device)
                targets = batch["target"].to(self.device)
                outputs = self.network(input_ids, attention_mask)
                loss = criterion(outputs, targets)
                self.optimizer().zero_grad()
                loss.backward()
                self.optimizer().step()

                # save results
                running_loss += loss.item()
                running_cs += cs(targets, outputs).mean().item()
                if i > 0 and i % 100 == 0:
                    stats = (
                        f"Epoch: {epoch+1}/{epochs}, batch: {i}/{len(train_loader)}, "
                        f"train_loss: {running_loss/i:.5f}, train_cosine_similarity: {running_cs/i:.5f}"
                    )
                    print(stats, flush=True)
                    with open("stats.log", "a") as f:
                        print(stats, file=f)
            if testing:
                continue
            # calculate loss and accuracy on validation dataset
            with torch.no_grad():
                val_loss, val_cs = self.evaluate(self._dataloaders.valid_loader)
            stats = (
                f"Epoch: {epoch+1}/{epochs}, "
                f"train_loss: {running_loss/i:.5f}, train_cosine_similarity: {running_cs/i:.5f}, "
                f"valid_loss: {val_loss:.5f}, valid_cosine_similarity: {val_cs:.5f}"
            )
            print(stats)
            with open("stats.log", "a") as f:
                print(stats, file=f)

            # save after each epoch
            self.save_weights()

            # check for early stopping
            self._early_stopping(val_loss, self.network)
            if self._early_stopping.early_stop:
                print("Early stopping.")
                break

        if testing:
            return running_loss, running_cs
        else:
            self.load_weights(path_to_weights=self._early_stopping.path)
            self.save_weights()
            print("\nFinished training\n")

    def criterion(self):
        return nn.MSELoss(reduction="mean").to(self.device)

    def optimizer(self):
        return optim.AdamW(self.network.parameters())

    def load_weights(self, path_to_weights):
        self.network.load_state_dict(torch.load(path_to_weights))

    def save_weights(self):
        torch.save(self.network.state_dict(), self.weights_filename)

    def evaluate(self, dataloader):
        criterion = self.criterion()
        self.network.eval()
        cos_sim = nn.CosineSimilarity(dim=1)
        valid_loss = 0.0
        valid_cs = 0.0

        for batch in dataloader:
            input_ids = batch["input_ids"].to(self.device)
            attention_mask = batch["attention_mask"].to(self.device)
            targets = batch["target"].to(self.device)
            outputs = self.network(input_ids, attention_mask)
            loss = criterion(outputs, targets)
            # results
            valid_loss += loss.item()
            valid_cs += cos_sim(targets, outputs).mean().item()

        return valid_loss / len(dataloader), valid_cs / len(dataloader)
