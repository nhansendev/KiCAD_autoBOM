# Copyright (c) 2025, Nathan Hansen
# All rights reserved.

# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

import os
import pandas as pd
from sexpdata import loads

from utils import (
    extract_sheet_info,
    extract_instance_ref,
    parse_footprint,
    _sort_as_numeric,
    df_to_string,
    split_refs,
    print_full_df,
)


def parse_file(
    path,
    filename,
    project_id=None,
    additional_fields=None,
):
    """
    Given a schematic file recursively extract component information
    from it and any hierarchical sheets it references, then return as a dataframe

    Parameters
    ----------
    path : string
        The full folder path containing the schematic sheets
    filename : string
        The target sheet's file name (Ex: "my_schematic.kicad_sch")
    project_id : string | None (default)
        The root project id. Detected automatically, typically leave this as None
    additional_fields : list | string | None (default)
        Any custom component field(s) to include in the BOM
    """

    with open(os.path.join(path, filename), "r") as f:
        raw_string = f.read()

    components = []
    sheets = []
    # Extract components, sheets, and the project ID from the
    # parsed s-expression
    for item in loads(raw_string):
        if hasattr(item[0], "value"):
            val = item[0].value()
            if val == "symbol":
                components.append(item)
            elif val == "sheet":
                sheets.append(extract_sheet_info(item))
            elif val == "uuid" and project_id is None:
                project_id = item[1]

    # Construct a dataframe from the extracted info
    base_df = get_BOM_items(
        components, project_id, get_raw=True, additional_fields=additional_fields
    )

    if len(sheets) > 0:
        # Multi-sheet
        for _, fname in sheets:
            # Recursively extract information from hierarchical sheets
            tmp_df = parse_file(
                path, fname, project_id=project_id, additional_fields=additional_fields
            )
            # Add all information to one dataframe
            base_df = pd.concat([base_df, tmp_df], ignore_index=True)

    return base_df


def get_BOM_items(
    components,
    project_id,
    ignore_refs=["G", "H", "J"],
    get_raw=False,
    additional_fields=None,
):
    """
    Given a component properties as a list of parsed s-expression objects,
    extract the desired properties

    Parameters
    ----------
    components : list
        A list of lists of parsed s-expressions for components
    project_id : string
        The id of the project to match info for
    ignore_refs : list (defualt=["G", "H", "J"])
        Ignore references with these prefixes (do not add to BOM)
    get_raw : bool (default=False)
        Return the un-condensed dataframe where each component gets its own line
    additional_fields : list | string | None (default)
        Any custom component field(s) to include in the BOM
    """

    # Ensure the fields are represented as a list
    if isinstance(additional_fields, str):
        additional_fields = [additional_fields]
    elif additional_fields is None:
        additional_fields = []

    # From the given schematic create a dataframe representing a BOM for all components
    # Optionally, ignore certain prefixes for graphics, jumpers, etc.
    df = pd.DataFrame(
        columns=["Reference", "Value", "Description", "Footprint", "pID"]
        + additional_fields
    )

    keys = list(df.columns.values)

    # For each component
    for com in components:
        refs = extract_instance_ref(com, project_id)

        if len(refs) < 1:
            refs = [""]

        for ref, pID in refs:
            if len(ref) > 0 and (ref[0] == "#" or ref[0] in ignore_refs):
                # Ignore undesired references and non-component references,
                # such as power indicators like +3V3 and GND
                continue

            # Will contain the target properties
            term_dict = {k: "-" for k in keys}
            term_dict["pID"] = pID

            ignore = False
            for v in com:
                # Extract values of interest from the data structure
                if isinstance(v, list) and len(v) > 2:
                    key = v[1]
                    if key in keys:
                        if len(ref) < 1 and key == "Reference":
                            ref = v[2]
                            if v[2][0] == "#" or v[2][0] in ignore_refs:
                                ignore = True
                                break
                        elif key == "Footprint":
                            term_dict[key] = parse_footprint(v[2])
                        else:
                            term_dict[key] = v[2]

            # Add the data to the dataframe
            if not ignore:
                term_dict["Reference"] = ref
                df.loc[-1] = list(term_dict.values())
                df.index += 1

    # print_full_df(df)

    # Return the un-condensed dataframe
    # (all references remain separated)
    if get_raw:
        return df

    # Find all common components and combine rows
    return _condense_df(df)


def _condense_df(df, replace_sequences=True, to_string=True):
    """
    Find all common components and combine rows
    E.g. ten identical resistors can be combined into one line item
    References are combined in csv format: "R1, R2, ..."
    Quantities are totalled

    Parameters
    ----------
    df : dataframe
        Contains BOM items parsed from the schematic
    replace_sequences : bool (default=True)
        Whether to replace sequences like (R1, R2, R3) with (R1-R3)
    to_string : bool (default=True)
        Whether to represent references as a list or string
    """

    tmp_df = df.drop(columns=["pID"])
    tmp_df.sort_values("Reference", ignore_index=True, inplace=True)
    # Group similar references into lists
    summary = (
        tmp_df.groupby(list(tmp_df.columns[tmp_df.columns != "Reference"].values))[
            "Reference"
        ]
        .apply(list)
        .reset_index()
    )

    # print_full_df(summary)

    qty = []
    refs = []
    # Sort references within each list and count occurrences
    for v in summary["Reference"]:
        tmp = list(set(v))
        qty.append(len(tmp))
        if to_string:
            refs.append(", ".join(_sort_as_numeric(tmp, replace_sequences)))
        else:
            refs.append(_sort_as_numeric(tmp, replace_sequences))

    summary["Reference"] = refs
    summary["Qty"] = qty
    addnl_values = list(
        summary.columns[
            ~summary.columns.isin(
                ["Reference", "Value", "Qty", "Footprint", "Description"]
            )
        ].values
    )
    # Set order of standard attributes + any added attributes
    summary = summary[
        ["Reference", "Value", "Qty", "Footprint", "Description"] + addnl_values
    ]

    # print_full_df(summary)

    # Re-sort
    prefixes, suffixes = split_refs(summary["Reference"].values)
    summary["sortvals1"] = prefixes
    summary["sortvals2"] = suffixes
    summary.sort_values(["sortvals1", "sortvals2"], ignore_index=True, inplace=True)
    summary.drop(labels=["sortvals1", "sortvals2"], axis=1, inplace=True)

    return summary


def get_BOM_all_sheets(
    basepath,
    filename,
    maxlen=None,
    to_csv=True,
    additional_fields="Vrating",
    custom_order=None,
):
    """
    Print a combined BOM for all discoverable sheets
    Must provide root sheet of heirarchy for all child sheets to be found

    Parameters
    ----------
    basepath : string
        The full path to the folder containing the sheets
    filename : string
        The name of the root schematic sheet (Ex: "my_schematic.kicad_sch")
    maxlen : int | None (default)
        Maximum column width in charachters (truncated)
    to_csv : bool (default=True)
        Whether to export a BOM csv to the same folder
    additional_fields : list | string | None
        Any additional component property field(s) to include in the BOM
    custom_order : list | None (default)
        A custom order for BOM columns. Omitted columns are added at the end
    """

    base_df = parse_file(basepath, filename, additional_fields=additional_fields)

    condensed_df = _condense_df(base_df)

    if to_csv:
        condensed_df.to_csv(os.path.join(basepath, filename.split(".")[0] + "_BOM.csv"))

    text = df_to_string(condensed_df, maxlen=maxlen, custom_order=custom_order)
    print(text)


if __name__ == "__main__":
    from utils import print_full_df

    path = r"D:\KiCAD\TMC2226_Multi"
    filename = "TMC2226_Multi.kicad_sch"

    # path = r"D:\KiCAD\PrinterMainModule_STM"
    # filename = "PrinterMainModule_STM.kicad_sch"

    # path = r"D:\KiCAD\force_resistor_1-1"
    # filename = "force_resistor.kicad_sch"

    # base_df = parse_file(path, filename, additional_fields=None)
    # print_full_df(base_df)

    # base_df.sort_values("Reference", ignore_index=True, inplace=True)
    # summary = (
    #     base_df.groupby(list(base_df.columns[base_df.columns != "Reference"].values))[
    #         "Reference"
    #     ]
    #     .apply(list)
    #     .reset_index()
    # )

    # print_full_df(summary)

    get_BOM_all_sheets(path, filename, to_csv=False, additional_fields="Vrating")
