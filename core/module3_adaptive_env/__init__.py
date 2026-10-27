"""
HumanCheck Core - Module 3: Adaptive Environment & Background Management
"""

from core.module3_adaptive_env.lighting_adapter import LightingAdapter
from core.module3_adaptive_env.background_engine import BackgroundEngine
from core.module3_adaptive_env.shadow_filter import ShadowAndNoiseFilter
from core.module3_adaptive_env.engine import AdaptiveEnvironmentEngine

__all__ = [
    "LightingAdapter",
    "BackgroundEngine",
    "ShadowAndNoiseFilter",
    "AdaptiveEnvironmentEngine"
]
