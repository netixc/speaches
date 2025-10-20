from collections.abc import Generator
import logging
from pathlib import Path

import huggingface_hub
from onnxruntime import InferenceSession
from pydantic import BaseModel

from speaches.api_types import Model
from speaches.config import OrtOptions
from speaches.executors.shared.base_model_manager import BaseModelManager, get_ort_providers_with_options
from speaches.hf_utils import (
    HfModelFilter,
    get_cached_model_repos_info,
    get_model_card_data_from_cached_repo_info,
    list_model_files,
)
from speaches.model_registry import ModelRegistry

LIBRARY_NAME = "onnx"
TASK_NAME_TAG = "speaker-embedding"
TAGS = {"pyannote"}


class PyannoteModelFiles(BaseModel):
    model: Path
    readme: Path


hf_model_filter = HfModelFilter(
    library_name=LIBRARY_NAME,
    task=TASK_NAME_TAG,
    tags=TAGS,
)


logger = logging.getLogger(__name__)

MODEL_ID_BLACKLIST = {
    "eek/wespeaker-voxceleb-resnet293-LM"  # reason: doesn't have `task` tag, also has pytorch binary file, onnx model file isn't named `model.onnx`
}


class PyannoteModelRegistry(ModelRegistry):
    def list_remote_models(self) -> Generator[Model, None, None]:
        models = huggingface_hub.list_models(**self.hf_model_filter.list_model_kwargs(), cardData=True)

        for model in models:
            if model.id in MODEL_ID_BLACKLIST:
                continue
            try:
                if model.created_at is None or getattr(model, "card_data", None) is None:
                    logger.info(
                        f"Skipping (missing created_at/card_data): {model}",
                    )
                    continue
                assert model.card_data is not None

                yield Model(
                    id=model.id,
                    created=int(model.created_at.timestamp()),
                    owned_by=model.id.split("/")[0],
                    task=TASK_NAME_TAG,
                )

            except Exception:
                logger.exception(f"Skipping (unexpected error): {model.id}")
                continue

    def list_local_models(self) -> Generator[Model, None, None]:
        cached_model_repos_info = get_cached_model_repos_info()
        for cached_repo_info in cached_model_repos_info:
            if cached_repo_info.repo_id in MODEL_ID_BLACKLIST:
                continue
            model_card_data = get_model_card_data_from_cached_repo_info(cached_repo_info)
            if model_card_data is None:
                continue
            if self.hf_model_filter.passes_filter(cached_repo_info.repo_id, model_card_data):
                yield Model(
                    id=cached_repo_info.repo_id,
                    created=int(cached_repo_info.last_modified),
                    owned_by=cached_repo_info.repo_id.split("/")[0],
                    task=TASK_NAME_TAG,
                )

    def get_model_files(self, model_id: str) -> PyannoteModelFiles:
        model_files = list(list_model_files(model_id))
        model_file_path = next(file_path for file_path in model_files if file_path.name == "model.onnx")
        readme_file_path = next(file_path for file_path in model_files if file_path.name == "README.md")

        return PyannoteModelFiles(
            model=model_file_path,
            readme=readme_file_path,
        )

    def download_model_files(self, model_id: str) -> None:
        _model_repo_path_str = huggingface_hub.snapshot_download(
            repo_id=model_id, repo_type="model", allow_patterns=["model.onnx", "README.md"]
        )


pyannote_model_registry = PyannoteModelRegistry(hf_model_filter=hf_model_filter)


class PyannoteModelManager(BaseModelManager[InferenceSession]):
    def __init__(self, ttl: int, ort_opts: OrtOptions) -> None:
        super().__init__(ttl)
        self.ort_opts = ort_opts

    def _load_fn(self, model_id: str) -> InferenceSession:
        model_files = pyannote_model_registry.get_model_files(model_id)
        providers = get_ort_providers_with_options(self.ort_opts)
        inf_sess = InferenceSession(model_files.model, providers=providers)
        return inf_sess
