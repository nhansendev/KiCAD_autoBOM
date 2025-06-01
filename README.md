# autoBOM
Python scripts for BOM operations in KiCAD (tested on 9+ only)

### Requirements
- python
- pandas

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

Example:
![image](https://github.com/user-attachments/assets/66033c3a-f2b7-4c65-8ed2-37a1c884e5b9)

### To replace reference designators with clustered values
```
> from autoBOM import compactREF
> compactREF()
```
Automatic annotating assigns component references geometrically, which can result in very non-sequential designators for identical components:
![image](https://github.com/user-attachments/assets/c4e8f29c-a621-490b-9a9e-151a57857bb3)

Using `compactREF` the components are clustered by value and footprint, then given sequential designators:

(must close and re-open schematic to observe changes, then update PCB from schematic afterwards)
![image](https://github.com/user-attachments/assets/63007260-c200-4a36-acdd-f6bf6c1264ff)
