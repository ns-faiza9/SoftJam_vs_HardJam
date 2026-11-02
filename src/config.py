"""
StartSense - System Configuration & Constants
Variant: 02.08 – Soft-Jam versus Hard-Jam Starter
"""

import os
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
GENERATED_DATA_DIR = DATA_DIR / "generated"
MODELS_DIR = BASE_DIR / "models"
DB_PATH = DATA_DIR / "startsense.db"
CSV_FALLBACK_PATH = DATA_DIR / "experiments.csv"

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
GENERATED_DATA_DIR.mkdir(exist_ok=True)
MODELS_DIR.mkdir(exist_ok=True)

# Project Identity
PROJECT_NAME = "StartSense"
PROJECT_SUBTITLE = "Startup Signature Intelligence for Electric Drives"
PROBLEM_FAMILY = "Problem 02"
VARIANT_ID = "02.08"
VARIANT_NAME = "Soft-Jam versus Hard-Jam Starter"
HARDWARE_PLATFORM = "STM32 NUCLEO-H753ZI"

# Target Condition Classes
CLASS_NORMAL = "NORMAL"
CLASS_SOFT_JAM = "SOFT JAM"
CLASS_HARD_JAM = "HARD JAM"

CLASSES = [CLASS_NORMAL, CLASS_SOFT_JAM, CLASS_HARD_JAM]

# Recommended Safety Actions
ACTION_ACCEPT_START = "ACCEPT_START"
ACTION_RETRY_SAFE = "RETRY_SAFE_PROFILE"
ACTION_DERATE = "DERATE"
ACTION_STOP = "STOP"

ACTIONS = [ACTION_ACCEPT_START, ACTION_RETRY_SAFE, ACTION_DERATE, ACTION_STOP]

# Visual Palette (Industrial Dark IoT Theme)
COLOR_NORMAL = "#00E676"      # Vivid Green
COLOR_SOFT_JAM = "#FFB300"    # Industrial Amber / Orange
COLOR_HARD_JAM = "#FF3D00"    # Safety Red
COLOR_CYAN = "#00E5FF"        # Modern Tech Cyan
COLOR_REAL_INPUT = "#E040FB"  # Real hardware potentiometer indicator (Purple/Pink)
COLOR_BG_DARK = "#0E1117"     # Deep Dark Background
COLOR_CARD_DARK = "#161B22"   # Elevated Card Dark
COLOR_BORDER = "#30363D"      # Subtle Border
COLOR_TEXT_MUTED = "#8B949E"  # Muted Gray

CONDITION_COLORS = {
    CLASS_NORMAL: COLOR_NORMAL,
    CLASS_SOFT_JAM: COLOR_SOFT_JAM,
    CLASS_HARD_JAM: COLOR_HARD_JAM,
}

# Physical Simulation Limits & Local Safety Limits (STM32 Hard Boundaries)
SAFETY_LIMITS = {
    "MAX_CURRENT_AMP": 15.0,          # Local overcurrent threshold on STM32 (Amperes)
    "STALL_TIMEOUT_SEC": 0.8,        # Max duration motor can stay below 300 RPM under load
    "MAX_TEMP_CELSIUS": 75.0,        # Maximum allowable stator temperature
    "MIN_SPEED_ACCEPT_RPM": 1500.0,  # Minimum speed required for ACCEPT_START
    "COMMAND_EXPIRY_MS": 500,        # Watchdog timeout for laptop recommendation heartbeat
}

# Default Motor Parameters (Simulated 24V BLDC / PMDC Drive)
DEFAULT_MOTOR_SPECS = {
    "V_BUS": 24.0,           # Volts
    "R_STATOR": 0.85,        # Ohms
    "L_STATOR": 0.0022,      # Henries
    "K_TORQUE": 0.055,       # N*m / A
    "K_EMF": 0.055,          # V / (rad/s)
    "ROTOR_INERTIA": 0.00045,# kg*m^2
    "VISCOUS_DAMPING": 0.001,# N*m*s/rad
    "TARGET_SPEED_RPM": 3000,# Normal no-load nominal RPM
    "ENCODER_CPR": 24,       # Pulses per revolution
}
