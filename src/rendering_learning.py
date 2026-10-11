from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
SHARED_RENDERING_PATH = ROOT / "shared" / "rendering" / "matte_dimensional_anime.json"
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
PLACEHOLDER_PREFIX = "SET_LOCAL_"


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload


def _require_dict(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"{key} must be an object")
    return value


def _require_string(payload: dict[str, Any], key: str, context: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{context}.{key} must be a non-empty string")
    return value.strip()


def _resolve_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return (ROOT / path).resolve()


def _reject_placeholder(value: str, context: str) -> None:
    if value.startswith(PLACEHOLDER_PREFIX):
        raise ValueError(f"{context} is not configured: {value}")


def _comfyui_lora_selector_name(value: str) -> str:
    # ComfyUI exposes nested LoRAs in LoraLoader's selector using Windows
    # backslashes (for example: local-rag\rendering\file.safetensors).
    # The selector value must match that exact representation.
    return value.replace("/", "\\")


def _validate_training_config(config: dict[str, Any]) -> dict[str, Any]:
    if config.get("schema_version") != 1:
        raise ValueError("training config schema_version must be 1")

    trainer = _require_dict(config, "trainer")
    model = _require_dict(config, "model")
    dataset = _require_dict(config, "dataset")
    output = _require_dict(config, "output")
    training = _require_dict(config, "training")

    trainer_repo_value = _require_string(trainer, "repo", "trainer")
    python_value = _require_string(trainer, "python_executable", "trainer")
    accelerate_config_value = _require_string(trainer, "accelerate_config", "trainer")
    pretrained_value = _require_string(model, "pretrained_model_name_or_path", "model")
    output_name = _require_string(model, "output_name", "model")
    train_data_value = _require_string(dataset, "train_data_dir", "dataset")
    caption_extension = _require_string(dataset, "caption_extension", "dataset")
    trigger_token = _require_string(dataset, "trigger_token", "dataset")
    output_dir_value = _require_string(output, "directory", "output")
    comfy_lora_dir_value = _require_string(output, "comfyui_lora_directory", "output")
    comfy_lora_name = _require_string(output, "comfyui_lora_name", "output")

    _reject_placeholder(pretrained_value, "model.pretrained_model_name_or_path")

    trainer_repo = _resolve_path(trainer_repo_value)
    trainer_script = trainer_repo / "sdxl_train_network.py"
    python_executable = _resolve_path(python_value)
    accelerate_config = _resolve_path(accelerate_config_value)
    pretrained_model = _resolve_path(pretrained_value)
    train_data_dir = _resolve_path(train_data_value)
    output_dir = _resolve_path(output_dir_value)

    if not trainer_script.is_file():
        raise FileNotFoundError(f"sd-scripts trainer not found: {trainer_script}")
    if not python_executable.is_file():
        raise FileNotFoundError(f"trainer Python not found: {python_executable}")
    if not accelerate_config.is_file():
        raise FileNotFoundError(f"accelerate config not found: {accelerate_config}")
    if not pretrained_model.is_file():
        raise FileNotFoundError(f"SDXL base model not found: {pretrained_model}")
    if not train_data_dir.is_dir():
        raise FileNotFoundError(f"training dataset directory not found: {train_data_dir}")

    if not caption_extension.startswith("."):
        raise ValueError("dataset.caption_extension must start with '.'")

    minimum_images = dataset.get("minimum_images", 1)
    if not isinstance(minimum_images, int) or minimum_images <= 0:
        raise ValueError("dataset.minimum_images must be a positive integer")

    required_training = {
        "resolution": str,
        "network_dim": int,
        "network_alpha": int,
        "learning_rate": str,
        "max_train_epochs": int,
        "train_batch_size": int,
        "mixed_precision": str,
        "seed": int,
    }
    for key, expected_type in required_training.items():
        if not isinstance(training.get(key), expected_type):
            raise ValueError(f"training.{key} has invalid type")

    return {
        "trainer_repo": trainer_repo,
        "trainer_script": trainer_script,
        "python_executable": str(python_executable),
        "accelerate_config": accelerate_config,
        "pretrained_model": pretrained_model,
        "output_name": output_name,
        "train_data_dir": train_data_dir,
        "caption_extension": caption_extension,
        "trigger_token": trigger_token,
        "minimum_images": minimum_images,
        "output_dir": output_dir,
        "comfy_lora_dir_value": comfy_lora_dir_value,
        "comfy_lora_name": _comfyui_lora_selector_name(comfy_lora_name),
        "training": training,
    }


def _validate_publish_config(config: dict[str, Any]) -> dict[str, Any]:
    if config.get("schema_version") != 1:
        raise ValueError("training config schema_version must be 1")

    model = _require_dict(config, "model")
    output = _require_dict(config, "output")

    output_name = _require_string(model, "output_name", "model")
    output_dir_value = _require_string(output, "directory", "output")
    comfy_lora_dir_value = _require_string(output, "comfyui_lora_directory", "output")
    comfy_lora_name = _require_string(output, "comfyui_lora_name", "output")
    _reject_placeholder(comfy_lora_dir_value, "output.comfyui_lora_directory")

    return {
        "output_name": output_name,
        "output_dir": _resolve_path(output_dir_value),
        "comfy_lora_dir_value": comfy_lora_dir_value,
        "comfy_lora_name": _comfyui_lora_selector_name(comfy_lora_name),
    }


def _dataset_images(train_data_dir: Path) -> list[Path]:
    return sorted(
        path
        for path in train_data_dir.rglob("*")
        if path.is_file() and path.suffix.casefold() in IMAGE_EXTENSIONS
    )


def validate_dataset(settings: dict[str, Any]) -> list[Path]:
    images = _dataset_images(settings["train_data_dir"])
    if len(images) < settings["minimum_images"]:
        raise ValueError(
            f"rendering dataset requires at least {settings['minimum_images']} images; found {len(images)}"
        )

    missing_captions: list[str] = []
    missing_trigger: list[str] = []
    caption_extension = settings["caption_extension"]
    trigger_token = settings["trigger_token"]

    for image in images:
        caption_path = image.with_suffix(caption_extension)
        if not caption_path.is_file():
            missing_captions.append(str(image.relative_to(settings["train_data_dir"])))
            continue
        caption = caption_path.read_text(encoding="utf-8").strip()
        if trigger_token not in caption:
            missing_trigger.append(str(caption_path.relative_to(settings["train_data_dir"])))

    if missing_captions:
        preview = ", ".join(missing_captions[:5])
        raise ValueError(f"missing caption files for {len(missing_captions)} images: {preview}")
    if missing_trigger:
        preview = ", ".join(missing_trigger[:5])
        raise ValueError(
            f"trigger token {trigger_token!r} missing from {len(missing_trigger)} captions: {preview}"
        )
    return images


def build_training_command(settings: dict[str, Any]) -> list[str]:
    training = settings["training"]
    output_dir: Path = settings["output_dir"]
    output_dir.mkdir(parents=True, exist_ok=True)

    return [
        settings["python_executable"],
        "-m",
        "accelerate.commands.launch",
        f"--config_file={settings['accelerate_config']}",
        "--num_cpu_threads_per_process=1",
        str(settings["trainer_script"]),
        f"--pretrained_model_name_or_path={settings['pretrained_model']}",
        f"--train_data_dir={settings['train_data_dir']}",
        f"--output_dir={output_dir}",
        f"--output_name={settings['output_name']}",
        f"--caption_extension={settings['caption_extension']}",
        f"--resolution={training['resolution']}",
        "--enable_bucket",
        "--network_module=networks.lora",
        f"--network_dim={training['network_dim']}",
        f"--network_alpha={training['network_alpha']}",
        f"--learning_rate={training['learning_rate']}",
        f"--max_train_epochs={training['max_train_epochs']}",
        f"--train_batch_size={training['train_batch_size']}",
        f"--mixed_precision={training['mixed_precision']}",
        f"--save_precision={training['mixed_precision']}",
        f"--seed={training['seed']}",
        "--save_model_as=safetensors",
        "--network_train_unet_only",
        "--cache_latents",
        "--cache_latents_to_disk",
        "--cache_text_encoder_outputs",
        "--cache_text_encoder_outputs_to_disk",
        "--gradient_checkpointing",
        "--sdpa",
    ]


def run_training(settings: dict[str, Any]) -> None:
    images = validate_dataset(settings)
    command = build_training_command(settings)
    print(f"[LEARNING] dataset_images={len(images)}")
    print(f"[LEARNING] output={settings['output_dir'] / (settings['output_name'] + '.safetensors')}")
    subprocess.run(command, cwd=settings["trainer_repo"], check=True)


def publish_lora(settings: dict[str, Any], activate: bool) -> Path:
    source = settings["output_dir"] / f"{settings['output_name']}.safetensors"
    if not source.is_file():
        raise FileNotFoundError(f"trained LoRA not found: {source}")

    comfy_lora_dir_value = settings["comfy_lora_dir_value"]
    comfy_lora_root = _resolve_path(comfy_lora_dir_value)
    destination = comfy_lora_root / Path(settings["comfy_lora_name"])
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    print(f"[PUBLISH] {destination}")

    if activate:
        payload = _load_json(SHARED_RENDERING_PATH)
        lora = payload.get("lora")
        if not isinstance(lora, dict):
            raise ValueError("shared rendering lora configuration is missing")
        lora["enabled"] = True
        lora["lora_name"] = settings["comfy_lora_name"]
        version = payload.get("rendering_version")
        if isinstance(version, int):
            payload["rendering_version"] = version + 1
        SHARED_RENDERING_PATH.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"[ACTIVATE] {SHARED_RENDERING_PATH}")

    return destination


def _load_settings(config_path: Path, command: str) -> dict[str, Any]:
    config = _load_json(config_path)
    if command == "publish":
        return _validate_publish_config(config)
    return _validate_training_config(config)


def main() -> int:
    parser = argparse.ArgumentParser(description="Train and publish the shared rendering LoRA")
    subparsers = parser.add_subparsers(dest="command", required=True)

    for command in ("validate", "train", "publish"):
        sub = subparsers.add_parser(command)
        sub.add_argument("--config", required=True, type=Path)
        if command == "publish":
            sub.add_argument("--activate", action="store_true")

    args = parser.parse_args()
    config_path = args.config if args.config.is_absolute() else (ROOT / args.config)
    settings = _load_settings(config_path.resolve(), args.command)

    if args.command == "validate":
        images = validate_dataset(settings)
        print(f"[LEARNING:OK] dataset_images={len(images)}")
        print(f"[LEARNING:OK] trainer={settings['trainer_script']}")
        print(f"[LEARNING:OK] python={settings['python_executable']}")
        print(f"[LEARNING:OK] model={settings['pretrained_model']}")
        return 0

    if args.command == "train":
        run_training(settings)
        print("[LEARNING:TRAIN:OK]")
        return 0

    if args.command == "publish":
        publish_lora(settings, activate=bool(args.activate))
        print("[LEARNING:PUBLISH:OK]")
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
