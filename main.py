"""
StartSense - Main Entry Point for PyCharm (Flask App)
Variant: 02.08 – Soft-Jam versus Hard-Jam Starter
Platform: STM32 NUCLEO-H753ZI + Python Flask
"""

import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import app

if __name__ == "__main__":
    print("=" * 70)
    print("⚡ StartSense – Startup Signature Intelligence for Electric Drives (Flask)")
    print("   Variant: 02.08 – Soft-Jam vs Hard-Jam Starter")
    print("   Target:  STM32 NUCLEO-H753ZI")
    print("   Access dashboard at: http://127.0.0.1:5000")
    print("=" * 70)
    app.run(host="127.0.0.1", port=5000, debug=True)
