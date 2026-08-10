import json
import tempfile
from pathlib import Path

from app import resource_policy

def test_ram_tolerance():
    assert abs(resource_policy.get_effective_minimum(8, "ram") - 7.84) < 1e-9
