"""Chart data types for compatibility with https://github.com/lakeesiv/digital-twin"""
from dataclasses import dataclass, field
import pandas as pd


@dataclass
class ChartData:
    """Jsonifiable chart data representation for a single data series."""
    x: list[float | str]
    y: list[float]
    ymin: list[float] | None = field(default=None, kw_only=True)
    ymax: list[float] | None = field(default=None, kw_only=True)

    @staticmethod
    def from_pandas(obj: pd.DataFrame | pd.Series) -> 'ChartData':
        """Instantiate a ChartData object from a pandas :py:class:`~pandas.DataFrame`
        or :py:class:`~pandas.Series`."""
        series = obj.iloc[:, 0] if isinstance(obj, pd.DataFrame) else obj
        return __class__(x=series.index.tolist(), y=series.values.tolist())


@dataclass
class MultiChartData:
    """Jsonifiable chart data representation for multiple data series.

    **Note**: only line charts are supported currently for this data type,
    thus ``x`` must be numeric, unlike for :py:class:`ChartData` which
    can also represent bar chart data with ``string`` x values.
    """
    x: list[float]
    y: list[list[float]]
    """List of line series.  Each series is a ``list[float]``."""
    labels: list[str] = field(kw_only=True)
    """Legend labels for each line series."""
    ymin: list[list[float]] | None = field(default=None, kw_only=True)
    ymax: list[list[float]] | None = field(default=None, kw_only=True)

    @staticmethod
    def from_pandas(df: pd.DataFrame) -> 'MultiChartData':
        """Instantiate a MultiChartData object from a pandas :py:class:`~pandas.DataFrame`."""
        return __class__(
            df.index.tolist(),
            df.T.values.tolist(),
            labels=df.columns.tolist()
        )
