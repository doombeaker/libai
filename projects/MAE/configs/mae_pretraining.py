from flowvision.transforms import transforms
from flowvision.data.constants import IMAGENET_DEFAULT_MEAN, IMAGENET_DEFAULT_STD

from libai.config import LazyCall, get_config

from configs.common.data.imagenet import dataloader
from .models.mae_vit_base_patch16 import model
from ..data.pretraining_imagenet import PretrainingImageNetDataset

train = get_config("common/train.py").train
optim = get_config("common/optim.py").optim
graph = get_config("common/models/graph.py").graph

# Refine data path to imagenet
dataloader.train.dataset[0].root = "/path/to/imagenet"
dataloader.test[0].dataset.root = "/path/to/imagenet"
dataloader.train.dataset[0]._target_ = PretrainingImageNetDataset

dataloader.train.dataset[0].root = "/dataset/extract"
dataloader.test[0].dataset.root = "/dataset/extract"

del dataloader.test

# Graph training
graph.enabled = True

# Refine data transform to MAE's default settings
transform_train = LazyCall(transforms.Compose)(
    transforms=[
        LazyCall(transforms.RandomResizedCrop)(
            size=(224, 224),
            scale=(0.2, 1.0),
            interpolation=3
        ),
        LazyCall(transforms.RandomHorizontalFlip)(),
        LazyCall(transforms.ToTensor)(),
        LazyCall(transforms.Normalize)(
            mean=IMAGENET_DEFAULT_MEAN,
            std=IMAGENET_DEFAULT_STD
        )
    ]
)
dataloader.train.dataset[0].transform = transform_train


# Refine training settings for MAE
train.train_micro_batch_size = 8
train.train_epoch = 800
train.warmup_ratio = 40 / 800
train.log_period = 10
train.eval_period = 10

# Base learning in MAE is set to 1.5e-4
# The actually learning rate should be computed by linear scaling rule: lr = base_lr * batch_size / 256
# In LiBai, you should refine the actually learning rate due to your on settings
# Here we use 8 GPUs, 128 batch_size per GPU for training, batch_size equals to 1024
base_lr = 1.5e-4
actual_lr = base_lr * (train.train_micro_batch_size * 8 / 256)


# Refine optim settings
optim.parameters.clip_grad_max_norm = None
optim.parameters.clip_grad_norm_type = None
optim.parameters.weight_decay_norm = None
optim.parameters.weight_decay_bias = None
optim.lr = actual_lr
optim.weight_decay = 0.05
optim.betas = (0.9, 0.95)


# Refine scheduler
# Default scheduler in LiBai training config is WarmupCosineLR
train.scheduler.warmup_factor = 0.001
train.scheduler.alpha = 0.
train.scheduler.warmup_method = "linear"


# Set fp16 ON
train.amp.enabled = True