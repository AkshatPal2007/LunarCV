import json
from datetime import datetime
from pathlib import Path
from typing import Any


class Pipeline:
    """
    Lightweight pipeline manager for lunar image registration.
    Tracks intermediate outputs and metadata across stages.
    """

    def __init__(self, name: str, output_dir: Path = Path("outputs")):
        self.name = name
        self.output_dir = Path(output_dir) / name
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Stage outputs tracking
        self.stages: dict[str, Path] = {}
        self.metadata: dict[str, Any] = {
            "name": name,
            "created_at": datetime.now().isoformat(),
        }

        # Load existing state if pipeline was resumed
        self._load_state()

    def _load_state(self):
        """Load pipeline state if it exists"""
        state_path = self.output_dir / "pipeline_state.json"
        if state_path.exists():
            with open(state_path) as f:
                state = json.load(f)
                self.stages = {k: Path(v) for k, v in state.get("stages", {}).items()}
                self.metadata.update(state.get("metadata", {}))

    def _save_state(self):
        """Save pipeline state"""
        state = {
            "stages": {k: str(v) for k, v in self.stages.items()},
            "metadata": self.metadata,
        }

        state_path = self.output_dir / "pipeline_state.json"
        with open(state_path, "w") as f:
            json.dump(state, f, indent=2)

    def record_stage(
        self,
        stage_name: str,
        output_path: Path,
        metadata: dict[str, Any] | None = None,
    ):
        """Record completion of a pipeline stage"""
        self.stages[stage_name] = output_path

        if metadata:
            if "stages_metadata" not in self.metadata:
                self.metadata["stages_metadata"] = {}
            self.metadata["stages_metadata"][stage_name] = metadata

        self._save_state()

    def get_stage_output(self, stage_name: str) -> Path | None:
        """Get output path from a previous stage"""
        return self.stages.get(stage_name)

    def has_stage(self, stage_name: str) -> bool:
        """Check if a stage has been completed"""
        return stage_name in self.stages

    def get_stage_dir(self, stage_name: str) -> Path:
        """Get output directory for a stage"""
        stage_dir = self.output_dir / stage_name
        stage_dir.mkdir(parents=True, exist_ok=True)
        return stage_dir

    def add_metadata(self, key: str, value: Any):
        """Add metadata to pipeline"""
        self.metadata[key] = value
        self._save_state()

    def get_metadata(self, key: str) -> Any | None:
        """Get metadata from pipeline"""
        return self.metadata.get(key)

    def summary(self) -> dict[str, Any]:
        """Get pipeline summary"""
        return {
            "name": self.name,
            "output_dir": str(self.output_dir),
            "completed_stages": list(self.stages.keys()),
            "metadata": self.metadata,
        }
