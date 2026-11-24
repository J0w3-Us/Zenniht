"""TFT con metadatos reproducibles persistidos en el checkpoint."""
from pytorch_forecasting import TemporalFusionTransformer


class TFTZenit(TemporalFusionTransformer):
    def __init__(self, zenit_metadata=None, **kwargs):
        super().__init__(**kwargs)
        self.save_hyperparameters({"zenit_metadata": zenit_metadata or {}})
