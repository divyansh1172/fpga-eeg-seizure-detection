"""
Course: EE2000 Signal Processing, Fall 2026, IIT Hyderabad
Project: 22-Channel FPGA Seizure Detector
Module: experiments.window_alignment.code.config_loader
Purpose: Robust configuration loader supporting YAML (if pyyaml installed),
         JSON, and native Python dict parsing with zero external dependency requirements.
"""

import os
import json
from pathlib import Path
from typing import Dict, Any

def _parse_simple_yaml(text: str) -> Dict[str, Any]:
    """
    Lightweight fallback parser for basic YAML key-value hierarchies
    when pyyaml is not installed.
    """
    try:
        import yaml
        return yaml.safe_load(text)
    except ImportError:
        pass

    # Simple indentation-based YAML fallback parser
    root: Dict[str, Any] = {}
    stack = [(0, root)]
    
    for raw_line in text.splitlines():
        # Remove comments
        line = raw_line.split("#")[0].rstrip()
        if not line.strip():
            continue
        
        indent = len(line) - len(line.lstrip())
        content = line.strip()
        
        while stack and indent <= stack[-1][0] and len(stack) > 1:
            stack.pop()
        
        curr_dict = stack[-1][1]
        
        if content.startswith("- "):
            # List item
            val_str = content[2:].strip().strip("\"'")
            # Find parent list
            parent = curr_dict
            if isinstance(parent, list):
                parent.append(_cast_scalar(val_str))
            continue
            
        if ":" in content:
            key, val_str = content.split(":", 1)
            key = key.strip().strip("\"'")
            val_str = val_str.strip()
            
            if not val_str:
                # Nested dict or list
                new_dict: Dict[str, Any] = {}
                curr_dict[key] = new_dict
                stack.append((indent, new_dict))
            else:
                curr_dict[key] = _cast_scalar(val_str)
                
    return root

def _cast_scalar(val_str: str) -> Any:
    val_str = val_str.strip().strip("\"'")
    if val_str.lower() in ("true", "yes"):
        return True
    if val_str.lower() in ("false", "no"):
        return False
    if val_str.lower() in ("none", "null"):
        return None
    try:
        if "." in val_str:
            return float(val_str)
        return int(val_str)
    except ValueError:
        return val_str

def load_config(config_path_or_name: str) -> Dict[str, Any]:
    """
    Loads experiment configuration by filename, path, or key ('1s', '2s').
    """
    code_dir = Path(__file__).resolve().parent
    exp_dir = code_dir.parent
    configs_dir = exp_dir / "configs"
    
    path = Path(config_path_or_name)
    if not path.is_file():
        # Check by name in configs_dir
        if config_path_or_name in ("1s", "window_1s", "A", "a"):
            candidates = [configs_dir / "window_1s.yaml", configs_dir / "window_1s.json"]
        elif config_path_or_name in ("2s", "window_2s", "B", "b"):
            candidates = [configs_dir / "window_2s.yaml", configs_dir / "window_2s.json"]
        else:
            candidates = [
                configs_dir / f"{config_path_or_name}.yaml",
                configs_dir / f"{config_path_or_name}.json",
                configs_dir / config_path_or_name
            ]
        
        found = None
        for c in candidates:
            if c.is_file():
                found = c
                break
        if found is None:
            raise FileNotFoundError(f"Configuration not found: {config_path_or_name} in {configs_dir}")
        path = found
        
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
        
    if path.suffix.lower() == ".json":
        return json.loads(text)
    
    try:
        import yaml
        return yaml.safe_load(text)
    except ImportError:
        # Check if equivalent .json exists
        json_alt = path.with_suffix(".json")
        if json_alt.is_file():
            with open(json_alt, "r", encoding="utf-8") as jf:
                return json.load(jf)
        return _parse_simple_yaml(text)
