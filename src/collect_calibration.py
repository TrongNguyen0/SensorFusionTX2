"""Compatibility entrypoint for calibration data collection.

The calibration workflow is maintained in app_pyqt.py so the collection UI,
preview, and saved data format stay consistent. Running this file opens the
same PyQt application and uses the direct 3-point correspondence workflow.
"""

from app_pyqt import main


if __name__ == "__main__":
    main()
