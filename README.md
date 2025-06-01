# autoBOM
Python scripts for BOM operations in KiCAD (tested on 9+ only)

### Requirements
- python
- pandas

#### To install pandas for KiCAD's instance of python
1. Navigate to installation `bin` folder, such as `C:\Program Files\KiCad\9.0\bin` in a terminal
2. Run `./python -m pip install pandas`

### Usage
#### TODO
Currently, the scripts must be navigated-to, imported, and run either inside or outside of KiCAD.
The plan is to make the scripts into either an installable package, or an addon to streamline this process.

From within the KiCAD scripting console:

` > cd <folder containing autoBOM.py> `

#### To print text BOM
To print the current project's BOM as a string, which can be copy-pasted into a schematic text-box with mono-spaced font.
```
> from autoBOM import printBOM
> printBOM()
```
```
def printBOM(maxlen=50, add_fields=None, to_csv=False):
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
```

Example:
![image](https://github.com/user-attachments/assets/66033c3a-f2b7-4c65-8ed2-37a1c884e5b9)

### To replace reference designators with clustered values
```
> from autoBOM import compactREF
> compactREF()
```
```
def compactREF(to_print=True, maxlen=50, add_fields=None):
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
```
Automatic annotating assigns component references geometrically, which can result in very non-sequential designators for identical components:
![image](https://github.com/user-attachments/assets/c4e8f29c-a621-490b-9a9e-151a57857bb3)

Using `compactREF` the components are clustered by value and footprint, then given sequential designators:

(must close and re-open schematic to observe changes, then update PCB from schematic afterwards)
![image](https://github.com/user-attachments/assets/63007260-c200-4a36-acdd-f6bf6c1264ff)
