"""Cellpose model training."""
import logging

logger = logging.getLogger(__name__)

try:
    from cellpose import io, models, train, metrics
    CELLPOSE_AVAILABLE = True
except ImportError as e:
    CELLPOSE_AVAILABLE = False
    logger.warning(f"Cellpose not available for training: {e}")


class Trainer:
    """Train custom Cellpose models."""

    def __init__(self, train_dir, test_dir=None, img_filter="_img",
                 mask_filter="_masks", look_one_level_down=True):
        if not CELLPOSE_AVAILABLE:
            raise ImportError("Cellpose is required for training. Install with: pip install cellpose[gui]")

        self.train_dir = train_dir
        self.test_dir = test_dir
        self.image_filter = img_filter
        self.mask_filter = mask_filter
        self.look_one_level_down = look_one_level_down

        io.logger_setup()
        self.output = self._load_data()

    def _load_data(self):
        logger.info(f"Training directory: {self.train_dir}")
        if self.test_dir:
            logger.info(f"Testing directory: {self.test_dir}")

        try:
            output = io.load_train_test_data(
                train_dir=self.train_dir,
                test_dir=self.test_dir,
                image_filter=self.image_filter,
                mask_filter=self.mask_filter,
                look_one_level_down=self.look_one_level_down,
            )
            return output
        except Exception as e:
            raise ValueError(f"Error loading training data: {e}")

    def train(self, model_name: str, model_type: str = "cyto3", channels=None,
              epochs: int = 100, learning_rate: float = 0.1, normalize: bool = True):
        if channels is None:
            channels = [1, 2]

        logger.info(f"Training: model={model_type}, channels={channels}, epochs={epochs}, lr={learning_rate}")
        images, labels, _, test_images, test_labels, _ = self.output

        # Try GPU first, fall back to CPU
        model = None
        for gpu in [True, False]:
            try:
                model = models.CellposeModel(model_type=model_type, gpu=gpu)
                logger.info(f"Initialized training model: {model_type} ({'GPU' if gpu else 'CPU'})")
                break
            except Exception as e:
                if not gpu:
                    raise RuntimeError(f"Unable to initialize model: {model_type}") from e
                logger.warning(f"GPU init failed: {e}, trying CPU")

        try:
            model_path, train_losses, test_losses = train.train_seg(
                model.net,
                train_data=images,
                train_labels=labels,
                channels=channels,
                normalize=normalize,
                test_data=test_images if self.test_dir else None,
                test_labels=test_labels if self.test_dir else None,
                weight_decay=1e-4,
                SGD=True,
                learning_rate=learning_rate,
                n_epochs=epochs,
                model_name=model_name,
            )
            logger.info(f"Training complete. Model saved at: {model_path}")
            return model_path, train_losses, test_losses
        except Exception as e:
            raise RuntimeError(f"Error during training: {e}") from e
