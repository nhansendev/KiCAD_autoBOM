# Copyright (c) 2025, Nathan Hansen
# All rights reserved.

# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

import os
from sexpdata import loads, dumps

from parsing import parse_file, _condense_df
from utils import replace_instance_ref, extract_sheet_info, split_refs


def replace_references(path, filename, rename_map, project_id=None, verbose=False):
    """
    Given a map of {old_reference: new_reference} find and replace the designators in
    the provided schematic sheet and any child hierarhical sheets.
    Generates a backup of the original files in the same folder with "_" prefix

    Parameters
    ----------
    path : string
         The full path to the folder containing the sheets
    filename : string
        The name of the root schematic sheet (Ex: "my_schematic.kicad_sch")
    rename_map : dict
        Contains pairs of {old_ref: new_ref}
    project_id : string | None (default)
        The root project id. Detected automatically; typically leave this as None
    verbose : bool (default=False)
    """

    with open(os.path.join(path, filename), "r") as f:
        raw_string = f.read()
    data = [s for s in loads(raw_string)]

    sheets = []
    # Extract components, sheets, and the project ID from the
    # parsed s-expression
    for i, item in enumerate(data):
        if hasattr(item[0], "value"):
            val = item[0].value()
            if val == "symbol":
                # Replace the references
                replace_instance_ref(item, rename_map)
            elif val == "sheet":
                sheets.append(extract_sheet_info(item))
            elif val == "uuid" and project_id is None:
                project_id = item[1]

    # Save the modified files and backups of the originals
    head, tail = os.path.split(filename)
    if path in head:
        os.replace(filename, os.path.join(head, "_" + tail))
        with open(filename, "w") as f:
            f.write(dumps(data))
        if verbose:
            print(f"Updated: {tail}\nBackup: _{tail}")
    else:
        os.replace(os.path.join(path, filename), os.path.join(path, "_" + filename))
        with open(os.path.join(path, filename), "w") as f:
            f.write(dumps(data))
        if verbose:
            print(f"Updated: {filename}\nBackup: _{filename}")

    # Recursively repeat for the hierarhical child sheets
    if len(sheets) > 0:
        # Multi-sheet
        for fname in set([s[1] for s in sheets]):
            replace_references(
                path, fname, rename_map, project_id=project_id, verbose=verbose
            )


def compress_references(path, filename, verbose=True, additional_fields="Vrating"):
    """
    Replace schematic references with new ones based on clustering similar components together

    Parameters
    ----------
    path : string
         The full path to the folder containing the sheets
    filename : string
        The name of the root schematic sheet (Ex: "my_schematic.kicad_sch")
    verbose : bool (default=True)
    additional_fields : list | string | None (default)
        Any custom component field(s) to include when clustering the BOM
    """

    def _get_prefix(val):
        for i, c in enumerate(val):
            if c.isnumeric() or c == "?":
                break
        return val[:i]

    # Extract
    base_df = parse_file(path, filename, additional_fields=additional_fields)

    # Group similar components
    condensed_df = _condense_df(base_df, False, False)

    # Count prefixes
    prefix_counts = {}
    for line in condensed_df["Reference"].values:
        for ref in line:
            pre = _get_prefix(ref)
            try:
                prefix_counts[pre] += 1
            except KeyError:
                prefix_counts[pre] = 1

    rename_map = {}
    # Generate a map of {old_reference: new_reference}
    rename_idx = {k: 1 for k in prefix_counts.keys()}
    # print(rename_idx)
    for line in condensed_df["Reference"].values:
        for ref in line:
            pre = _get_prefix(ref)
            tmp = f"{pre}{rename_idx[pre]}"
            if tmp != ref:
                rename_map[ref] = tmp
            rename_idx[pre] += 1

    # print(rename_map)
    # print(prefix_counts)
    # print(rename_map)

    base_df["NewRef"] = base_df["Reference"].apply(lambda x: rename_map.get(x, x))
    rename_map = base_df.set_index("Reference")[["NewRef", "pID"]]
    rename_map = rename_map[rename_map.index != rename_map["NewRef"]]
    # rename_map.drop_duplicates(inplace=True)
    prefixes, values = split_refs(rename_map["NewRef"].values.tolist())
    rename_map["pref"] = prefixes
    rename_map["vals"] = values
    rename_map.sort_values(["pref", "vals"], inplace=True)

    # from utils import print_full_df

    # print_full_df(rename_map)
    # base_df.loc[:, "Reference"] = base_df["NewRef"]
    # base_df.drop(columns=["NewRef"], inplace=True)
    # print(_condense_df(base_df))
    replace_references(path, filename, rename_map, verbose=verbose)
