"""Functions for reading Excel data."""

from datetime import datetime
from typing import Union

import numpy as np
import openpyxl as xl
import pandas as pd
from openpyxl.cell.cell import Cell

CellType = Union[int, float, str, datetime]


def get_name(wbook: xl.Workbook, name: str) -> CellType | np.ndarray:
    """Read an Excel named range as a single value or NumPy array.
    Arrays are flattened to one dimension if possible.

    Args:
        wbook (openpyxl.workbook.workbook.Workbook):
            The workbook object.
        name (str): Name of the Excel range to read.

    Returns:
        int | float | str | datetime.datetime | numpy.ndarray:
            A single value, or a NumPy array containing the named range's values.
    """
    worksheet, cell_range = list(wbook.defined_names[name].destinations)[0]
    cell_range = str.replace(cell_range, "$", "")
    cells = wbook[worksheet][cell_range]
    if isinstance(cells, Cell):
        value = cells.value
    else:
        value = [[cell.value for cell in r] for r in cells]
        value = np.array(value).squeeze().tolist()
    return value


def get_named_matrix(wbook: xl.Workbook, index_name: str, data_name: str
                     ) -> dict[str, dict[str, float]]:
    """Read a matrix with named rows/columns and convert
    to a dict of dicts.

    It is assumed the rows and columns have the same name, i.e. for
    runner times between pairs of locations.

    Args:
        wbook (openpyxl.workbook.workbook.Workbook): The workbook object.
        index_name (str):
            Name of the Excel named range containing the row/column names of the matrix.
        data_name (str): Name of the Excel named range containing the matrix data.

    Returns:
        dict[str, dict[str, float]]:
            The values of the matrix as a dict of dicts.  The keys in both
            levels of the returned dict are those listed in `index_name`.
    """
    names = get_name(wbook, index_name)
    data = get_name(wbook, data_name)
    ret = {}
    for i, from_loc in enumerate(names):
        ret[from_loc] = {}
        for j, to_loc in enumerate(names):
            if i != j:
                ret[from_loc][to_loc] = float(data[i][j])
    return ret


def get_table(workbook: xl.Workbook, sheet_name: str, name: str) -> pd.DataFrame:
    """Gets a named table from an Excel workbook as a pandas array

    Args:
        workbook (openpyxl.workbook.workbook.Workbook): The workbook object.
        sheet (str): Name of the worksheet containing the table.
        name (str): Name of the table to read.

    Returns:
        pandas.DataFrame: A pandas dataframe containing the named table's values.
    """
    # Named Tables in openpyxl belong to the worksheet
    sheet = workbook[sheet_name]
    cell_range = sheet[sheet.tables[name].ref]

    vals = [[cell.value for cell in row] for row in cell_range]
    return pd.DataFrame(vals[1:], columns=vals[0])
