# Copyright (c) 2025, Nathan Hansen
# All rights reserved.

# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

import pandas as pd
import re

SMD_SIZES = ["0402", "0603", "0805", "1008", "1206", "1210"]
SMD_PREFIXES = ["LED", "R", "C", "L", "Fuse"]
IC_SIZES = ["SOT-23-3", "SOT-23-5", "SOT-23", "SOT-23-6", "SOT-89-3"]
IGNORE = [
    "Custom Library",
    "footprints",
    "Capacitor_THT",
    "Diode_SMD",
    "Button_Switch_SMD",
    "Package_DFN",
    "Package_DFN_QFN",
    "Package_SO",
    "Crystal",
    "Inductor_SMD",
]


def print_full_df(df):
    """
    Print the full non-summarized dataframe.

    Parameters
    ----------
    df : Pandas dataframe
        The dataframe to plot
    """
    with pd.option_context(
        "display.max_rows",
        None,
        "display.max_columns",
        None,
        "display.width",
        2000,
    ):
        print(df)


def _get_prefix(value, ser):
    """
    Using given compiled regex try to find a match and return it

    Parameters
    ----------
    value : string
        A string to search within
    ser : compiled regex
        The compiled regex to apply
    """
    mch = ser.match(value)
    if mch:
        return mch.group()
    else:
        return None


def _extract(line):
    """
    Return a generator over all s-expression items with values in line

    Parameters
    ----------
    line : list
        Contains parsed s-expressions
    """
    for i, item in enumerate(line):
        if len(item) > 0 and hasattr(item[0], "value"):
            yield i, item[0].value(), item


def extract_instance_ref(component, project_id):
    """
    Search through the hierarchy of the given component for its reference value,
    matching the given project_id

    Parameters
    ----------
    component : list
        Contains parsed s-expressions for a schematic object
    project_id : string
        Which id to match
    """
    ref = []
    # For each item in the component data
    for _, id, val in _extract(component):
        if id == "instances":
            # For each occurrence of the component
            for _, id2, val2 in _extract(val):
                if id2 == "project":
                    # For each project_id
                    for _, id3, val3 in _extract(val2):
                        if id3 == "path" and val3[1].split("/")[1] == project_id:
                            # For each reference in this project
                            for _, id4, val4 in _extract(val3):
                                if id4 == "reference":
                                    # Track the relevant reference value and project ID path
                                    ref.append((val4[1], val3[1]))

    return ref


def replace_instance_ref_OLD(component, project_id, rename_map):
    """
    Search through the hierarchy of the given component for its reference value,
    matching the given project_id and replacing it using the provided mapping dictionary

    Parameters
    ----------
    component : list
        Contains parsed s-expressions for a schematic object
    project_id : string
        Which id to match
    rename_map : dict
        Contains pairs of {old_ref: new_ref}
    """
    # For each item in the component data
    for idx, id, val in _extract(component):
        if id == "instances":
            # For each occurrence of the component
            for idx2, id2, val2 in _extract(val):
                if id2 == "project":
                    # For each project_id
                    for idx3, id3, val3 in _extract(val2):
                        # splt = val3[1].split("/")
                        # if id3 == "path" and splt[1] == project_id:
                        if id3 == "path" and val3[1] == project_id:
                            # For each reference in this project
                            for idx4, id4, val4 in _extract(val3):
                                if id4 == "reference":
                                    # Try to map the old reference to a new one
                                    # and update the component in-place
                                    try:
                                        repl = rename_map[val4[1]]
                                        component[idx][idx2][idx3][idx4][1] = repl
                                    except KeyError:
                                        continue


def replace_instance_ref(component, rename_map):
    """
    Search through the hierarchy of the given component for its reference value,
    matching the given project_id and replacing it using the provided mapping dictionary

    Parameters
    ----------
    component : list
        Contains parsed s-expressions for a schematic object
    project_id : string
        Which id to match
    rename_map : DataFrame
        Contains {old_ref: new_ref, pID}
    """
    # For each item in the component data
    for idx, id, val in _extract(component):
        if id == "instances":
            # For each occurrence of the component
            for idx2, id2, val2 in _extract(val):
                if id2 == "project":
                    # For each project_id
                    for idx3, id3, val3 in _extract(val2):
                        if id3 == "path":
                            valid_ids = rename_map["pID"] == val3[1]
                            if sum(valid_ids) < 1:
                                continue
                            ref_list = []
                            # For each reference in this project
                            for idx4, id4, val4 in _extract(val3):
                                if id4 == "reference":
                                    # Try to map the old reference to a new one
                                    # and update the component in-place
                                    ref_list.append([val4[1], idx4])

                            candidates = rename_map[valid_ids]
                            for v, i in ref_list:
                                try:
                                    repl = candidates.loc[v, "NewRef"]
                                    if not isinstance(repl, str):
                                        repl = repl["NewRef"][0]
                                    # print(repl)
                                    component[idx][idx2][idx3][i][1] = repl
                                    # Prevent re-renaming
                                    rename_map.drop(v)
                                except KeyError:
                                    continue


def extract_sheet_info(sheet):
    """
    Given a list containing the parsed s-expression data for a sheet,
    find its name and filename

    Parameters
    ----------
    sheet : list
        Contains parsed s-expressions for a schematic sheet
    """
    name = ""
    filename = ""
    for _, id, item in _extract(sheet):
        if id == "property":
            if item[1] == "Sheetname":
                name = item[2]
            elif item[1] == "Sheetfile":
                filename = item[2]

    return name, filename


def parse_footprint(value):
    """
    Given a footprint description string find any matches to known formats
    and generate a compact representation for better BOM appearance.
    Join by semicolon if multiple matches are found (unlikely)

    Parameters
    ----------
    value : string
        Component footprint designator string
    """
    segments = value.split(":")
    out = []

    for s in segments:
        # Often includes the library containing the footprint, which
        # can be ignored
        if s in IGNORE:
            continue

        # Extract common SMD sizes like "0402".
        # Add a prefix for common types
        # e.g. "R" for resistor: "R_0402"
        for si in SMD_SIZES:
            for p in SMD_PREFIXES:
                tmp = p + "_" + si
                if tmp in s:
                    out.append(tmp)

        # Extract common chip sizes, like "SOT-23"
        for si in IC_SIZES:
            if si in s:
                out.append(si)

    if len(out) < 1:
        # No known values found, so just return anything not ignored
        return ":".join([s for s in segments if s not in IGNORE])
    return ":".join(out)


def _sort_as_numeric(values, replace_seq=True):
    """
    Given reference values: [R15, R18, R20, R22, R24, R41, R5]
    sort them in ascending numeric order: [R5, R15, R18, R20, ...]
    If replace_seq=True:
        Summarize sequences: e.g. R5, R6, ..., R13 becomes R5-R13
        Assumes all prefixes match!

    Parameters
    ----------
    values : list
        A list of reference designators to be sorted
    replace_seq : bool (default=True)
        Whether to replace sequential values with ranges
    """

    as_integers = []
    prefix = ""
    for v in values:
        # For each reference value e.g. "R22"
        # Find the numeric portion e.g. "22"
        # Convert to integer and store for later sorting
        val = 0
        for i in range(len(v)):
            try:
                val = int(v[i:])
                if len(prefix) < 1:
                    prefix = v[:i]
                break
            except ValueError:
                pass
        as_integers.append(val)

    # Sort by found integer values
    pairs = list(zip(as_integers, values))
    pairs.sort()
    sorted_int, sorted_vals = list(zip(*pairs))

    if replace_seq:
        # Find sequential values
        st = sorted_int[0]
        seqs = [[st]]
        for i in sorted_int[1:]:
            if i != st + 1:
                seqs[-1].append(st)
                seqs.append([i])
            st = i
        seqs[-1].append(st)

        # Replace with compact representations as appropriate
        out = []
        for st, en in seqs:
            if abs(en - st) > 1:
                out.append(f"{prefix}{st}-{prefix}{en}")
            elif st != en:
                out.append(f"{prefix}{st}, {prefix}{en}")
            else:
                out.append(f"{prefix}{st}")
        return out

    # Return numerically sorted reference values
    return sorted_vals


def df_to_string(df, maxlen=35, category_sep=True, col_sep=" │ ", custom_order=None):
    """
    Convert the provided dataframe into a nicely formatted string.
    Display using monospace fonts, or in terminal!

    Parameters
    ----------
    df : dataframe
        Contains the BOM parsed from provided schematics
    maxlen : int (default=35)
        The maximum column width in characters (truncated)
    category_sep : bool (default=True)
        Whether to add horizontal lines separating the table by component prefix
    col_sep : string (default=" | ")
        String to separate columns with
    custom_order : list | None (default)
        The order to print columns in. Columns are added at the end if not in this list
    """

    # Regex for finding reference prefixes
    ser = re.compile(r"\D+(?=\d+)")

    if custom_order is not None:
        # Check if the user entered valid column names and which were omitted
        missing = []
        for c in custom_order:
            if c not in df.columns.values:
                missing.append(c)
        if len(missing) > 0:
            raise ValueError(f"Specified columns not present in dataframe:\n{missing}")
        col_order = custom_order + list(df.columns[~df.columns.isin(custom_order)])
    else:
        col_order = list(df.columns.values)

    # Get max widths for each column based on content, unless limited by maxlen
    col_widths = []
    ref_idx = 0
    for i, col in enumerate(col_order):
        if col == "Reference":
            ref_idx = i + 1
            # Don't limit display of reference values
            col_widths.append(max(len(col), max([len(str(val)) for val in df[col]])))
        else:
            col_widths.append(
                max(len(col), max([len(str(val)[:maxlen]) for val in df[col]]))
            )

    # Account for index width
    col_widths = [len(str(len(df)))] + col_widths

    # Build header
    out = " " * col_widths[0] + col_sep
    out += (
        col_sep.join([c.ljust(col_widths[i + 1]) for i, c in enumerate(col_order)])
        + "\n"
    )
    row_sep = "─┼─".join(["─" * i for i in col_widths]) + "\n"
    out += row_sep

    # Build rows
    last = None
    for i in range(len(df)):
        # For current row, get index and all values as a list
        tmp = [str(i)] + list(df[col_order].iloc[i].values)

        # If we separate by prefix type, then check prefix and insert newlines as needed
        if category_sep:
            prefix = _get_prefix(tmp[1], ser)

            if last is not None and last != prefix:
                out += row_sep  # "\n"

        # Pad row values using column widths, left-justified
        tstr = []
        for j, w in enumerate(col_widths):
            # Add markers to make following lines easier
            if i % 2:
                if j == ref_idx:
                    base = str(tmp[j])
                else:
                    base = str(tmp[j])[:maxlen]
                if len(base) < w:
                    base += " "

                tstr.append(base.ljust(w, "╌"))
            else:
                if j == ref_idx:
                    base = str(tmp[j])
                else:
                    base = str(tmp[j])[:maxlen]
                tstr.append(base.ljust(w))
        out += col_sep.join(tstr) + "\n"

        if category_sep:
            last = prefix

    return out


def split_refs(refs):
    """
    Given a list of reference designators split them into two lists of
    prefixes and integer values.
    Ex: ["R22", "R24"] -> ["R", "R"], [22, 24]

    Parameters
    ----------
    refs : list
        A list of reference designators to be split
    """
    prefixes = []
    suffixes = []
    for r in refs:
        # Account for grouped values
        # Ex: "R1-R4", "R1, R2"
        if isinstance(r, str):
            base = r.split("-")[0].split(",")[0]
        else:
            base = r[0]
        for i, c in enumerate(base):
            if c.isnumeric():
                break
        prefixes.append(base[:i])
        try:
            suffixes.append(int(base[i:]))
        except ValueError:
            suffixes.append(0)

    return prefixes, suffixes
