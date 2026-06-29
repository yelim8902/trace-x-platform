"""
룰북 로더

TRACE-X 룰북 YAML 파일을 로드하고 파싱
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, Optional
import yaml


class RuleLoader:
    """룰북 로더"""
    
    def __init__(self, rules_path: str = "rules/tracex_rules.yaml"):
        """
        Args:
            rules_path: 룰북 YAML 파일 경로
        """
        self.rules_path = Path(rules_path)
        self._ruleset: Optional[Dict[str, Any]] = None
    
    def load(self) -> Dict[str, Any]:
        """룰북 로드"""
        if self._ruleset is None:
            with open(self.rules_path, "r", encoding="utf-8") as f:
                self._ruleset = yaml.safe_load(f)
        return self._ruleset
    
    def get_rules(self) -> list:
        """룰 목록 반환"""
        ruleset = self.load()
        return ruleset.get("rules", [])
    
    def get_defaults(self) -> Dict[str, Any]:
        """기본 설정 반환"""
        ruleset = self.load()
        return ruleset.get("defaults", {})

