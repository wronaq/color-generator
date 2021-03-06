"""ColorModel class."""
from color_generator.models.base import Model
from transformers import AutoTokenizer


class ColorModel(Model):
    """ColorModel works on datasets providing single text sequence up to 32 tokens, with RGB labels."""

    def __init__(self, network_fn, device, **kwargs):
        super().__init__(network_fn, device, **kwargs)

    def predict_on_text(self, input_text):
        tokenizer = AutoTokenizer.from_pretrained(
            self.network.architecture, use_fast=False
        )
        input_text = tokenizer(input_text, truncation=True, return_tensors="pt")
        self.network.eval()
        predictions = self.network(
            input_text["input_ids"], input_text["attention_mask"]
        ).squeeze()

        return self._unnorm(predictions)

    @staticmethod
    def _unnorm(predictions):
        return [int(x) for x in predictions * 255]
