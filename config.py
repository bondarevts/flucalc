import os


class Config:
    SECRET_KEY = os.environ.get('FLUCALC_SECRET_KEY', default='my-secret-key')
    VERSION = '2025.5.1'
    CALCULATION_TIMEOUT_SEC = os.environ.get('FLUCALC_TIMEOUT_SEC', 60)
