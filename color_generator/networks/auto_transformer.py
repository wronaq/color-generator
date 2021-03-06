from importlib import import_module
import torch.nn as nn
from transformers import AutoModel, AutoConfig


class AutoTransformer(nn.Module):
    def __init__(
        self,
        architecture="distilbert-base-uncased",
        freeze=True,
        activation="torch.nn.ReLU",
    ):
        super().__init__()

        self.architecture = architecture
        self.config = AutoConfig.from_pretrained(self.architecture, use_fast=False)

        self.config.output_hidden_states = False
        self.config.output_attentions = False
        self.transformer_model = AutoModel.from_pretrained(
            self.architecture, config=self.config
        )
        self.transformer_output_features = self.transformer_model.transformer.layer[
            -1
        ].output_layer_norm.normalized_shape[0]

        module_path, class_name = activation.rsplit(".", 1)
        module = import_module(module_path)
        _activation = getattr(module, class_name)()

        self.regression_head = nn.Sequential(
            nn.Linear(in_features=self.transformer_output_features, out_features=3),
            _activation,
        )

        if freeze:
            for param in self.transformer_model.parameters():
                param.requires_grad = False

    def forward(self, input_ids, attention_mask):
        trans = self.transformer_model(input_ids, attention_mask)
        head = self.regression_head(trans.last_hidden_state[:, 0, :])

        return head
