"""Загрузка акустической модели Vosk в каталог ``models/``.

Модели не хранятся в git, поэтому после клонирования репозитория их нужно
скачать отдельно::

    python scripts/download_vosk_model.py

Каталог назначения берётся из переменной окружения ``VOSK_MODEL_PATH``
(как в ``src/common/.env``) и разрешается относительно корня проекта.
Переопределить можно флагами ``--dest`` и ``--model``.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

import requests

BASE_URL = "https://alphacephei.com/vosk/models"
DEFAULT_MODEL = "vosk-model-small-ru-0.22"
CHUNK_SIZE = 1 << 20  # 1 MiB
TIMEOUT = 60

# scripts/download_vosk_model.py -> корень проекта. Вычисляется детерминированно,
# без обхода родителей вверх (в отличие от common/config.py).
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=None, help=f"имя модели (по умолчанию {DEFAULT_MODEL})")
    parser.add_argument("--dest", default=None, help="каталог назначения (перекрывает VOSK_MODEL_PATH)")
    parser.add_argument("--force", action="store_true", help="перекачать, даже если модель уже установлена")
    return parser.parse_args(argv)


def resolve_target(args: argparse.Namespace, model_name: str) -> Path:
    """Определяет каталог модели из CLI / VOSK_MODEL_PATH / значения по умолчанию."""
    raw = args.dest or os.getenv("VOSK_MODEL_PATH") or str(Path("models") / model_name)
    target = Path(raw)
    return target if target.is_absolute() else (PROJECT_ROOT / target).resolve()


def is_valid_model(path: Path) -> bool:
    """Каталог считается моделью Vosk, если в нём есть am/ или conf/."""
    return path.is_dir() and ((path / "am").is_dir() or (path / "conf").is_dir())


def download(url: str, dest: Path) -> None:
    """Скачивает файл потоково, печатая прогресс."""
    with requests.get(url, stream=True, timeout=TIMEOUT) as response:
        response.raise_for_status()
        total = int(response.headers.get("Content-Length") or 0)
        done = 0
        with dest.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                if not chunk:
                    continue
                handle.write(chunk)
                done += len(chunk)
                if total:
                    print(f"\r  {done * 100 // total:3d}%  {done >> 20}/{total >> 20} MiB",
                          end="", flush=True)
        if total:
            print()


def safe_extract(archive: Path, dest_root: Path) -> None:
    """Распаковывает zip, отклоняя записи с выходом за пределы dest_root (zip-slip)."""
    root = dest_root.resolve()
    with zipfile.ZipFile(archive) as zf:
        for member in zf.infolist():
            candidate = (root / member.filename).resolve()
            if not candidate.is_relative_to(root):
                raise RuntimeError(f"небезопасный путь в архиве: {member.filename}")
        zf.extractall(root)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    model_name = args.model or os.getenv("VOSK_MODEL_NAME") or DEFAULT_MODEL
    target = resolve_target(args, model_name)

    if is_valid_model(target) and not args.force:
        print(f"Модель уже установлена: {target}")
        return 0

    url = f"{BASE_URL}/{model_name}.zip"
    print(f"Загрузка {url}")

    with tempfile.TemporaryDirectory() as tmp_name:
        tmp = Path(tmp_name)
        archive = tmp / f"{model_name}.zip"

        try:
            download(url, archive)
        except requests.RequestException as exc:
            print(f"Не удалось скачать модель: {exc}", file=sys.stderr)
            print(f"Скачайте архив вручную: {url}", file=sys.stderr)
            return 1

        extract_dir = tmp / "extracted"
        extract_dir.mkdir()
        try:
            safe_extract(archive, extract_dir)
        except (zipfile.BadZipFile, RuntimeError) as exc:
            print(f"Не удалось распаковать архив: {exc}", file=sys.stderr)
            return 1

        children = list(extract_dir.iterdir())
        # Архивы Vosk содержат один каталог верхнего уровня с именем модели.
        payload = children[0] if len(children) == 1 and children[0].is_dir() else extract_dir

        if not is_valid_model(payload):
            print(f"В архиве не найдена структура модели Vosk: {url}", file=sys.stderr)
            return 1

        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            shutil.rmtree(target)
        shutil.move(str(payload), str(target))

    print(f"Модель установлена: {target}")
    return 0


if __name__ == "__main__":
    # Консоли Windows часто работают в cp866/cp1251, из-за чего кириллица в
    # справке и индикаторе прогресса отображается нечитаемо.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
