# Copyright (c) 2025, Nathan Hansen
# All rights reserved.

# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

import os

from condensing import compress_references
from parsing import get_BOM_all_sheets


def printBOM(maxlen=50, add_fields=None, to_csv=False):
    """
    Print the BOM for the current project to terminal.
    Can be pasted into a textbox with mono-spaced font

    Parameters
    ----------
    maxlen : int (default=50)
        Max column width in characters (truncated)
    add_fields : list | string | None (default)
        Any additional property field(s) to include in the BOM
    to_csv : bool (default=False)
        Export a csv of the BOM into the project folder
    """
    import pcbnew

    board = pcbnew.GetBoard()
    filename = board.GetFileName()

    basedir = os.path.dirname(filename)
    get_BOM_all_sheets(
        basedir,
        filename.replace("_pcb", "_sch"),
        maxlen=maxlen,
        to_csv=to_csv,
        additional_fields=add_fields,
    )


def compactREF(to_print=True, maxlen=50, add_fields=None):
    """
    Cluster component by similar properties,
    then order references sequentially within the clusters.
    Overwrites the current schematics, but makes backups

    Parameters
    ----------
    to_print : bool (default=True)
        Whether to also print the BOM to terminal after update
        Can be pasted into a textbox with mono-spaced font
    maxlen : int (default=50)
        Max column width in characters (truncated)
    add_fields : list | string | None (default)
        Additional property field(s) to use when clustering
    """
    import pcbnew

    board = pcbnew.GetBoard()
    filename = board.GetFileName()

    basedir = os.path.dirname(filename)
    name = filename.replace("_pcb", "_sch")
    compress_references(basedir, name, additional_fields=add_fields)
    if to_print:
        get_BOM_all_sheets(
            basedir,
            name,
            to_csv=False,
            maxlen=maxlen,
            additional_fields=add_fields,
        )


if __name__ == "__main__":
    # path = "D:\\KiCAD\\SpotWelder"
    # filename = "SpotWelder.kicad_sch"

    # path = "D:\\KiCAD\\DistSensor5"
    # filename = "DistSensor5.kicad_sch"

    # path = r"D:\KiCAD\PrinterMainboard_Modular"
    # filename = "PrinterMainboard_Modular.kicad_sch"

    # path = r"D:\KiCAD\TMC2226_Multi"
    # filename = "TMC2226_Multi.kicad_sch"

    path = r"D:\KiCAD\PrinterMainModule_STM"
    filename = "PrinterMainModule_STM.kicad_sch"

    # base_df = parse_file(path, filename, additional_fields="Vrating")
    # print_full_df(base_df)

    # get_BOM_all_sheets(path, filename)

    additional_fields = "Vrating"
    order = ["Reference", "Value", "Vrating", "Qty", "Footprint", "Description"]
    compress_references(path, filename, additional_fields=additional_fields)
    get_BOM_all_sheets(
        path,
        filename,
        to_csv=False,
        additional_fields=additional_fields,
        maxlen=50,
        custom_order=order,
    )
