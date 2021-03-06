import pytest
import torch
from color_generator.networks import AutoTransformer


@pytest.fixture
def network():
    return AutoTransformer()


def test_output_shape(network):
    output = network(torch.tensor([[1, 2, 3, 4, 5]]), torch.tensor([[1, 1, 1, 1, 1]]))
    assert isinstance(output, torch.Tensor)
    assert tuple(output.size()) == (1, 3)
