bl_info = {
    "name": "HKX2 Tools",
    "author": "kreny",
    "blender": (2, 80, 0),
    "version": (1, 0, 0),
}


import bpy
import bpy_extras
import bmesh

import sys
import os
import subprocess
from pathlib import Path


# For some reason, custom .NET Core assemblies cannot be imported via CLR in Windows
"""
site = subprocess.Popen(["python", "-m", "site", "--user-site"], stdout=subprocess.PIPE)
site_path = site.stdout.read().decode()[:-1]

if not site_path in sys.path:
    sys.path.insert(1, site_path)

def install(package: str):
    subprocess.check_call(["python", "-m", "pip", "install", package])

try:
    import clr
    dllDir = Path(__file__).parent.absolute()
    clr.AddReference(str(dllDir/"BlenderConverter"))
    from BlenderConverter import Converter
except:
    install('pythonnet')
    import clr
    dllDir = Path(__file__).parent.absolute()
    clr.AddReference(str(dllDir/"BlenderConverter"))
    from BlenderConverter import Converter
"""

import platform

exedir_names = {
    "Linux": "linux-x64",
    "Windows": "win-x64",
}

exe_extensions = {
    "Linux": "",
    "Windows": ".exe",
}

addondir = Path(__file__).parent.absolute()
exedir = addondir / exedir_names[platform.system()]
exe = exedir / ("BlenderConverter" + exe_extensions[platform.system()])

try:
    os.system(f"chmod +x {str(exe)}")
except:
    pass

import json

class ImportCollision(bpy.types.Operator, bpy_extras.io_utils.ImportHelper):
    """Import BotW collision mesh files (*.hksc, *.hkrb, *.hktmrb)"""

    bl_idname = "botw.import_collision"
    bl_label = "Import BotW collision mesh file"
    filename_ext = ""

    directory: bpy.props.StringProperty(subtype='DIR_PATH')
    files: bpy.props.CollectionProperty(
        name="Collision mesh files",
        type=bpy.types.OperatorFileListElement,
    )
    filter_glob: bpy.props.StringProperty(default="*.hksc;*.hkrb;*.hktmrb", options={"HIDDEN"})

    def execute(self, context):
        for file in self.files:
            file_path = Path(self.directory) / file.name

            print("Converting meshes to PyData")
            # pydatas = Converter.Convert(str(file_path))
            pydatas = json.loads(subprocess.Popen([str(exe), str(file_path)], stdout=subprocess.PIPE).stdout.read().decode())
            print("\n************\nDone\n************\n\n")

            # Remove the collection if it exists
            for col in bpy.data.collections:
                if file_path.stem in col.name:
                    bpy.data.collections.remove(col)

            # Create a new collision with the name of the file
            bpy.ops.collection.create(name=file_path.stem)
            collection = bpy.data.collections[file_path.stem]
            bpy.context.scene.collection.children.link(collection)

            # Create a bmesh for convex hull creation
            bm = bmesh.new()

            print("Creating meshes in Blender")
            for pydata in pydatas:
                # Construct the blender mesh
                # mesh = bpy.data.meshes.new(pydata.Name)
                mesh = bpy.data.meshes.new(pydata["Name"])
                obj = bpy.data.objects.new(mesh.name, mesh)
                collection.objects.link(obj)
                bpy.context.view_layer.objects.active = obj

                # Flip some coordinates to account for BotW coordinate system
                # vertices = [(v.X, -v.Z, v.Y) for v in pydata.Vertices]
                vertices = [(v["X"], -v["Z"], v["Y"]) for v in pydata["Vertices"]]

                # Import PyData
                mesh.from_pydata(
                    vertices,
                    # pydata.Edges,
                    pydata["Edges"],
                    # pydata.Primitives,
                    pydata["Primitives"],
                )

                # if pydata.Name in ("hkpConvexVerticesShape", "hkpBoxShape"):
                if pydata["Name"] in ("hkpConvexVerticesShape", "hkpBoxShape"):
                    bm.from_mesh(mesh)
                    bmesh.ops.convex_hull(bm, input=bm.verts)
                    bm.to_mesh(mesh)
                    mesh.update()
                    bm.clear()

                print(f"{pydata['Name']} created!")

            print("\n************\nFILE IMPORT FINISHED\n************\n\n")
        return {"FINISHED"}


def MenuImport(self, context):
    self.layout.operator(ImportCollision.bl_idname, text="BotW Collision mesh (*.hksc/*.hkrb/*.hktmrb)")


classes = (ImportCollision,)

rgstr, unrgstr = bpy.utils.register_classes_factory(classes)


def register():
    rgstr()
    bpy.types.TOPBAR_MT_file_import.append(MenuImport)


def unregister():
    unrgstr()
    bpy.types.TOPBAR_MT_file_import.remove(MenuImport)


if __name__ == "__main__":
    register()
