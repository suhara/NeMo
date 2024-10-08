# Copyright (c) 2024, NVIDIA CORPORATION.  All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


from typing import Optional

import nemo_run as run
import pytorch_lightning as pl
import torch

from nemo.collections.llm.api import finetune, pretrain
from nemo.collections.llm.gpt.data.mock import MockDataModule
from nemo.collections.llm.gpt.data.squad import SquadDataModule
from nemo.collections.llm.recipes import mixtral_8x3b
from nemo.utils.exp_manager import TimingCallback

NAME = "mixtral_8x3b_64k"


@run.cli.factory(name=NAME)
def model() -> run.Config[pl.LightningModule]:
    """
    Factory function to create a Mixtral 8x3B model configuration with 64k sequence length.

    Returns:
        run.Config[pl.LightningModule]: Configuration for the Mixtral 8x3B model with 64k sequence length.

    Examples:
        CLI usage:
            $ nemo llm pretrain model=mixtral_8x3b_64k ...

        Python API usage:
            >>> model_config = model()
            >>> print(model_config)
    """
    model_config = mixtral_8x3b.model()
    model_config.config.seq_length = 65536
    return model_config


def trainer(
    num_nodes: int = 8,
    num_gpus_per_node: int = 8,
) -> run.Config:
    """
    Configure the NeMo Lightning Trainer for Mixtral 8x3B model with 64k sequence length.

    This function sets up the distributed training strategy optimized for long sequences.

    Args:
        num_nodes (int): Number of compute nodes to use.
        num_gpus_per_node (int): Number of GPUs per node.

    Returns:
        run.Config: Configuration for the NeMo Lightning Trainer.

    Examples:
        CLI usage:
            $ nemo llm pretrain trainer=mixtral_8x3b_64k ...

        Python API usage:
            >>> trainer_config = trainer(num_nodes=8, num_gpus_per_node=8)
            >>> print(trainer_config)

    Note:
        This configuration uses significantly increased parallelism to handle the long sequence length efficiently.
    """
    return mixtral_8x3b.trainer(
        tensor_parallelism=4,
        pipeline_parallelism=4,
        pipeline_parallelism_type=torch.bfloat16,
        virtual_pipeline_parallelism=8,
        context_parallelism=4,
        sequence_parallelism=True,
        expert_parallelism=1,
        num_nodes=num_nodes,
        num_gpus_per_node=num_gpus_per_node,
        callbacks=[run.Config(TimingCallback)],
    )


@run.cli.factory(target=pretrain, name=NAME)
def pretrain_recipe(
    dir: Optional[str] = None,
    name: str = "default",
    num_nodes: int = 8,
    num_gpus_per_node: int = 8,
) -> run.Partial:
    """
    Create a pre-training recipe for Mixtral 8x3B model with 64k sequence length.

    This function sets up a complete configuration for pre-training, including
    model, trainer, and data settings optimized for 64k sequence length.

    Args:
        dir (Optional[str]): Directory for saving logs and checkpoints.
        name (str): Name of the pre-training run.
        num_nodes (int): Number of compute nodes to use.
        num_gpus_per_node (int): Number of GPUs per node.

    Returns:
        run.Partial: Partial configuration for pre-training.

    Examples:
        CLI usage:
            $ nemo llm pretrain --factory mixtral_8x3b_64k
            $ nemo llm pretrain --factory "mixtral_8x3b_64k(num_nodes=8, name='my_64k_pretrain')"

        Python API usage:
            >>> recipe = pretrain_recipe(name="mixtral_8x3b_64k_pretrain", num_nodes=8)
            >>> print(recipe)

    Note:
        This recipe is optimized for handling long sequences (64k) compared to the standard version.
        It requires significant computational resources due to the extended sequence length.
    """
    recipe = mixtral_8x3b.pretrain_recipe(name=name, dir=dir, num_nodes=num_nodes, num_gpus_per_node=num_gpus_per_node)

    recipe.model = model()
    recipe.trainer = trainer(num_nodes=num_nodes, num_gpus_per_node=num_gpus_per_node)
    recipe.data = run.Config(MockDataModule, seq_length=65536, global_batch_size=512, micro_batch_size=1)
    return recipe
