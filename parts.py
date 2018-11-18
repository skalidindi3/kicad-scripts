#!/usr/bin/env python3

from __future__ import print_function
import sys
sys.path.insert(0, "./kicad-library-utils/sch/")

from collections import defaultdict
from copy import deepcopy
from sch import Component, Schematic
import IPython


SchematicFieldList = [
    "Reference",
    "Value",
    "Footprint",
    "Datasheet",
    "Description",
    "Manufacturer",
    "Manufacturer Part Number",
    "Supplier",
    "Supplier Part Number",
]
SchematicFieldIndexMap = {v:k for k,v in enumerate(SchematicFieldList)}


def sanitizeValue(value):
    """Ensure that |value| is properly double-quoted."""
    if type(value) != str:
        value = str(value)
    if value[0] != '"':
        value = '"%s"' % value
    return value


############################################
# Methods to monkey-patch into |Component| #
############################################

def _normalizeFields(self):
    """Add spots for all expected schematic fields."""
    to_add = len(SchematicFieldList) - len(self.fields)
    for i in range(len(SchematicFieldList)):
        if i == len(self.fields):
            # copy position & attributes from previous position
            self.fields.append(deepcopy(self.fields[-1]))
            # reset ref
            self.fields[-1]["ref"] = '""'
            # update id & name
            self.fields[-1]["id"] = str(i)
            self.fields[-1]["name"] = '"%s"' % SchematicFieldList[i]


def _setFields(self, footprint=None, datasheet=None, description=None,
        manufacturer=None, mpn=None, supplier=None, spn=None):
    self.normalizeFields()
    if footprint:
        self.fields[SchematicFieldIndexMap["Footprint"]]["ref"] = sanitizeValue(footprint)
    if datasheet:
        self.fields[SchematicFieldIndexMap["Datasheet"]]["ref"] = sanitizeValue(datasheet)
    if description:
        self.fields[SchematicFieldIndexMap["Description"]]["ref"] = sanitizeValue(description)
    if manufacturer:
        self.fields[SchematicFieldIndexMap["Manufacturer"]]["ref"] = sanitizeValue(manufacturer)
    if mpn:
        self.fields[SchematicFieldIndexMap["Manufacturer Part Number"]]["ref"] = sanitizeValue(mpn)
    if supplier:
        self.fields[SchematicFieldIndexMap["Supplier"]]["ref"] = sanitizeValue(supplier)
    if spn:
        self.fields[SchematicFieldIndexMap["Supplier Part Number"]]["ref"] = sanitizeValue(spn)


def _getText(self):
    """Get text representation of the Component."""
    lines = ["$Comp\n"]
    lines.append("L " + " ".join(self.labels[key] for key in self._L_KEYS).strip() + "\n")
    lines.append("U " + " ".join(self.unit[key] for key in self._U_KEYS).strip() + "\n")
    lines.append("P " + " ".join(self.position[key] for key in self._P_KEYS).strip() + "\n")
    for field in self.fields:
        fieldline = "F"
        for key in self._F_KEYS:
            if key == "attributs": # [sic]
                fieldline += " "
            fieldline += " " + field[key]
        lines.append(fieldline.strip() + "\n")
    lines.extend(self.old_stuff)
    lines.append("$EndComp\n")
    return lines


# Apply monkey-patch
Component.normalizeFields = _normalizeFields
Component.getText = _getText
Component.setFields = _setFields


############################################
# Methods to monkey-patch into |Schematic| #
############################################

def _getComponentsGroups(self):
    """Return lists of components grouped by value in a dictionary."""
    groups = defaultdict(list)
    for c in self.components:
        groups[c.fields[SchematicFieldIndexMap["Value"]]["ref"]] += [c]
    return dict(groups)


def _updateComponentGroup(self, value, **kwargs):
    """Change info for all components of a given value."""
    for c in self.getComponentsGroups()[sanitizeValue(value)]:
        c.setFields(**kwargs)


def _saveInline(self, filename=None):
    """Save updates to parts without reordering the schematic file."""
    # default to overwriting the original schematic
    if not filename:
        filename = self.filename

    # read original schematic into memory
    with open(self.filename, "r") as f:
        oldsch = f.readlines()

    # replace components with the updated versions
    in_component = False
    newsch = []
    component_index = 0
    for line in oldsch:
        if line == "$EndComp\n":
            in_component = False
        elif in_component:
            continue
        elif line == "$Comp\n":
            in_component = True
            newsch.extend(self.components[component_index].getText())
            component_index += 1
        else:
            newsch.append(line)

    # save to disk
    with open(filename, "w") as f:
        f.writelines(newsch)


# Apply monkey-patch
Schematic.getComponentsGroups = _getComponentsGroups
Schematic.updateComponentGroup = _updateComponentGroup
Schematic.saveInline = _saveInline


print("")
print("Applied monkey-patches to the 'sch' library to provide the following functionality:")
print("\tComponent.normalizeFields")
print("\tComponent.getText")
print("\tComponent.setFields")
print("\tSchematic.getComponentsGroups")
print("\tSchematic.updateComponentGroup")
print("\tSchematic.saveInline")
print("")


IPython.InteractiveShell.colors = 'Neutral'
IPython.embed()

