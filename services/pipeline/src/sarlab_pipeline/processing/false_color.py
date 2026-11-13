"""Display HH, HV and HH/HV with fixed stretches shared by both acquisition dates."""

import numpy as np

# Ranges in dB for display only. They do not classify surface cover.
RGB_LIMITS = ((-30, 0), (-35, -5), (0, 15))


def backscatter_rgb(hh_db: np.ndarray, hv_db: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    valid = np.isfinite(hh_db) & np.isfinite(hv_db)
    channels = (hh_db, hv_db, hh_db - hv_db)
    rgb = np.stack([
        np.rint(255 * np.clip((np.where(valid, channel, low) - low) / (high - low), 0, 1))
        for channel, (low, high) in zip(channels, RGB_LIMITS, strict=True)
    ]).astype(np.uint8)
    return rgb, valid.astype(np.uint8) * 255
