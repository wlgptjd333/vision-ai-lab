"""모델과 학습 설정을 서버 시작 때 한 번 불러와 모든 요청에서 재사용한다.

6일차 35번 스크립트가 저장한 세 파일 + Action 목록 CSV 를 읽고, 서로 맞는지 먼저 확인한다
(틀리면 서버가 '준비 안 됨'으로 뜨고 이유를 /health 에 보여 준다).
  - Joblib 의 n_features_in_ == Feature 순서 JSON 길이 == 학습 정보 feature_count (1,140)
  - Feature 순서 == t00~t29 × 수업 Frame Feature 38개 (sequence_utils.FRAME_FEATURE_NAMES)
  - Joblib 의 classes_ == 학습 정보 classes (순서까지), 모두 action_classes.csv 에 있음
"""
from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from pathlib import Path

import joblib

from src.sequence_utils import FRAME_FEATURE_NAMES

APP_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = APP_ROOT / "project.json"


def load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def load_action_classes(path: Path) -> dict[str, dict]:
    """label → {action_id, label, name_ko}. 모델은 label(bend_return …)을 Class 로 학습했다."""
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    return {r["action_label"]: {"action_id": r["action_id"], "label": r["action_label"],
                                "name_ko": r["description"]}
            for r in rows}


@dataclass
class ModelBundle:
    config: dict
    model: object = None
    feature_columns: list[str] = field(default_factory=list)
    info: dict = field(default_factory=dict)
    actions: dict = field(default_factory=dict)
    pose_model: object = None
    error: str = ""

    @property
    def ready(self) -> bool:
        return self.model is not None and self.pose_model is not None and not self.error

    @property
    def classes(self) -> list[str]:
        return [str(c) for c in self.model.classes_] if self.model is not None else []

    def summary(self) -> dict:
        return {
            "ready": self.ready,
            "error": self.error,
            "sequence_steps": self.info.get("sequence_steps"),
            "frame_features": len(FRAME_FEATURE_NAMES),
            "n_features": len(self.feature_columns),
            "n_classes": len(self.classes),
            "classes": [self.actions.get(c, {}).get("action_id", c) for c in self.classes],
            "trained_on": {"subjects": self.info.get("subjects"), "clips": self.info.get("train_clips")},
            "window_seconds": self.config.get("window_seconds"),
            "uncertain_below": self.config.get("uncertain_below"),
            "pose_model": Path(self.config["pose_model"]).name,
        }


def _check(model, columns: list[str], info: dict, actions: dict) -> None:
    steps = info["sequence_steps"]
    if model.n_features_in_ != len(columns) or len(columns) != info["feature_count"]:
        raise ValueError(f"모델 입력 {model.n_features_in_}개, Feature 순서 {len(columns)}개, "
                         f"학습 정보 {info['feature_count']}개가 서로 다릅니다.")
    expected = [f"t{i:02d}_{f}" for i in range(steps) for f in FRAME_FEATURE_NAMES]
    if columns != expected:
        raise ValueError("Feature 순서 JSON 이 수업 Frame Feature(38개) × 30단계 순서와 다릅니다.")
    if [str(c) for c in model.classes_] != info["classes"]:
        raise ValueError("모델 classes_ 와 학습 정보 classes 가 다릅니다.")
    missing = [c for c in info["classes"] if c not in actions]
    if missing:
        raise ValueError(f"action_classes.csv 에 없는 Class: {missing}")


def load_bundle(load_pose: bool = True) -> ModelBundle:
    cfg = load_config()
    bundle = ModelBundle(config=cfg)
    try:
        # 본인이 학습해 저장한 파일만 joblib.load 한다 (Pickle 은 임의 코드를 실행할 수 있음)
        bundle.model = joblib.load(APP_ROOT / cfg["rf_model"])
        bundle.feature_columns = json.loads((APP_ROOT / cfg["feature_columns"]).read_text(encoding="utf-8"))
        bundle.info = json.loads((APP_ROOT / cfg["training_info"]).read_text(encoding="utf-8"))
        bundle.actions = load_action_classes(APP_ROOT / cfg["action_classes"])
        _check(bundle.model, bundle.feature_columns, bundle.info, bundle.actions)
        if load_pose:
            from ultralytics import YOLO
            bundle.pose_model = YOLO(str(APP_ROOT / cfg["pose_model"]))
    except Exception as exc:  # 서버는 띄우고 /health 로 원인을 알린다
        bundle.error = f"{type(exc).__name__}: {exc}"
    return bundle
