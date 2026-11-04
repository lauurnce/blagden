"""Read .fit, .gpx and .tcx run files and resample heart rate to one-minute steps."""

from blagden.ingest.clean import clean
from blagden.ingest.readers import detect_format, read_activity, sniff_format
from blagden.ingest.resample import MinuteSeries, resample_minutes
from blagden.ingest.table import (
    ActivityTable,
    CleaningReport,
    EmptyActivityError,
    Gap,
    IngestError,
    NoHeartRateError,
    RawActivity,
    RawRecord,
    UnsupportedFormatError,
)

__all__ = [
    "ActivityTable",
    "CleaningReport",
    "EmptyActivityError",
    "Gap",
    "IngestError",
    "MinuteSeries",
    "NoHeartRateError",
    "RawActivity",
    "RawRecord",
    "UnsupportedFormatError",
    "clean",
    "detect_format",
    "read_activity",
    "resample_minutes",
    "sniff_format",
]
