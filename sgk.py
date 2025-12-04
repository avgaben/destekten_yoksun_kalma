from __future__ import annotations

from models import CalculationInput, SGKDeductionType


def compute_sgk_psd(ci: CalculationInput) -> float:
    """
    Çok basit PSD modeli:
      PSD ≈ sgk_monthly_income * 12 * sgk_psd_factor
    Gerçek hesapta Tebliğ katsayıları kullanılır; burada esnek katsayı var.
    """
    if ci.sgk_monthly_income <= 0:
        return 0.0
    return ci.sgk_monthly_income * 12.0 * ci.sgk_psd_factor
