from typing import Sequence, Union
import torch

from allenact.base_abstractions.experiment_config import MachineParams
from experiments.two_phase.two_phase_ta_base import TwoPhaseTaskAwareRearrangeExperimentConfig
from allenact_plugins.ithor_plugin.ithor_sensors import RelativePositionChangeTHORSensor
from allenact.base_abstractions.experiment_config import (
    MachineParams,
    split_processes_onto_devices,
)

class TwoPhaseDistributedExp001Config(TwoPhaseTaskAwareRearrangeExperimentConfig):
    
    NUM_DISTRIBUTED_NODES: int = 4
    NUM_DEVICES: Union[int, Sequence[int]] = 1
    
    PIPELINE_TYPE = "4proc-il"
    
    CNN_PREPROCESSOR_TYPE_AND_PRETRAINING = ("RN50", "clip")
    
    SAVE_INTERVAL = int(2e5)
    IL_LOSS_WEIGHT = 1.0
    # RL_LOSS_WEIGHT = 10.0
    
    WALKTHROUGH_TRAINING_PPO = True
    WALKTHROUGH_PPO_LOSS_WEIGHT = 10.0
    # HEADLESS = False
    RGB_NORMALIZATION = True
    EXPERT_VERBOSE = False
    
    SAP_SUBTASK_HISTORY = True
    SAP_SEMANTIC_MAP = True
    REQUIRE_SEMANTIC_SEGMENTATION = True
    
    ONLINE_SUBTASK_PREDICTION = True
    ONLINE_SUBTASK_PREDICTION_USE_EGOVIEW = False
    ONLINE_SUBTASK_PREDICTION_USE_PREV_ACTION = False
    ONLINE_SUBTASK_PREDICTION_USE_IS_WALKTHROUGH_PHASE = True
    ONLINE_SUBTASK_PREDICTION_USE_SEMANTIC_MAP = True
    ONLINE_SUBTASK_PREDICTION_USE_SUBTASK_HISTORY = True
    ONLINE_SUBTASK_LOSS_WEIGHT = 1.0
    
    @classmethod
    def tag(cls) -> str:
        return "TwoPhaseDistributedExp001"
    
    @classmethod
    def num_valid_processes(cls) -> int:
        return 1
    
    @classmethod
    def num_test_processes(cls) -> int:
        return 1
    
    @classmethod
    def machine_params(
        cls,
        mode="train",
        **kwargs
    ) -> MachineParams:
        params = super().machine_params(mode, **kwargs)
        num_gpus = torch.cuda.device_count()
        has_gpu = num_gpus != 0
        
        sampler_devices = None
        nprocesses = 1
        devices = (
            list(range(min(nprocesses, num_gpus)))
            if has_gpu
            else [torch.device("cpu")]
        )
        nprocesses = split_processes_onto_devices(
            nprocesses=nprocesses, ndevices=len(devices)
        )
        params = MachineParams(
            nprocesses=nprocesses,
            devices=devices,
            sampler_devices=sampler_devices,
            sensor_preprocessor_graph=cls.create_preprocessor_graph(mode=mode),
        )
        
        if isinstance(cls.NUM_DEVICES, int):
            num_devices = [cls.NUM_DEVICES] * cls.NUM_DISTRIBUTED_NODES
        else:
            num_devices = cls.NUM_DEVICES
        
        assert len(num_devices) == cls.NUM_DISTRIBUTED_NODES
        
        if mode == "train":
            devices = sum(
                [
                    list(range(min(cls.num_train_processes(), num_devices[idx])))
                    if num_devices[idx] > 0 and torch.cuda.is_available()
                    else torch.device('cpu')
                    for idx in range(cls.NUM_DISTRIBUTED_NODES)
                ], []
            )
            params.devices = tuple(
                torch.device("cpu") if d == -1 else torch.device(d) for d in devices
            )
            params.sampler_devices = params.devices
            
            params.nprocesses = sum(
                [
                    split_processes_onto_devices(
                        cls.num_train_processes() if torch.cuda.is_available() and num_devices[idx] > 0 else 1,
                        num_devices[idx] if num_devices[idx] > 0 else 1
                    )
                    for idx in range(cls.NUM_DISTRIBUTED_NODES)
                ], []
            )
            
            if "machine_id" in kwargs:
                machine_id = kwargs["machine_id"]
                assert (
                    0 <= machine_id < cls.NUM_DISTRIBUTED_NODES
                ), f"machine_id {machine_id} out of range [0, {cls.NUM_DISTRIBUTED_NODES - 1}]"
                
                machine_num_gpus = torch.cuda.device_count()
                machine_has_gpu = machine_num_gpus != 0
                assert (
                    0 <= num_devices[machine_id] <= machine_num_gpus
                ), f"Number of devices for machine {machine_id} ({num_devices[machine_id]}) exceeds the number of gpus {machine_num_gpus}"
                
                local_worker_ids = list(
                    range(
                        sum(num_devices[:machine_id]),
                        sum(num_devices[:machine_id + 1])
                    )
                )
                params.set_local_worker_ids(local_worker_ids)
            
            if "machine_id" in kwargs:
                print(f"Machine id: {machine_id}")
            print(
                f"devices: {params.devices} \n"
                f"processes: {params.nprocesses} \n"
                f"sampler_devices: {params.sampler_devices} \n"
                f"local_worker_ids: {params.local_worker_ids} \n"
            )
        elif mode == "valid":
            # params = super().machine_params(mode, **kwargs)
            params.nprocesses = (0, )
            
        return params