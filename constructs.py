from utils import split_refs


class Component:
    def __init__(self, ref, value, loc, addnl_properties=None):
        self.set_ref(ref)
        self.value = value
        self.loc = loc
        self.properties = addnl_properties

    def set_ref(self, ref):
        self._ref = ref
        pref, suff = split_refs([ref])
        self.type = pref[0]
        self.idx = suff[0]

    def get_ref(self):
        return f"{self.type}{self.idx}"

    @property
    def _prop(self):
        return (self.get_ref(), self.value, self.loc, self.properties)

    def __eq__(self, value):
        if isinstance(value, Component):
            return self._prop == value._prop
        else:
            return False

    def __lt__(self, value):
        if isinstance(value, Component):
            return self.idx < value.idx
        else:
            # Can't compare
            return None

    def __repr__(self):
        return f"{self._prop}"


if __name__ == "__main__":
    import os
    from sexpdata import loads
    from utils import extract_sheet_info

    path = r"D:\KiCAD\PrinterMainModule_STM_Plugin"
    filename = "PrinterMainModule_STM_Plugin.kicad_sch"

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

    print(components[0])

    # C = Component("R22", "1k", "TBD")
    # print(C)
    # print(C.type, C.idx)
