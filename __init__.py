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
import json
import subprocess
from concurrent.futures import ThreadPoolExecutor
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

if platform.system() == "Linux":
    os.system(f"chmod +x {str(exe)}")


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

    # Custom attributes
    teraMeshTilingFloat: bpy.props.FloatProperty(
        name="TeraMesh tiling constant",
        description="Constant, by which to tile TeraMesh files",
        default=250.0,
    )

    teraMeshOffsetVector: bpy.props.FloatVectorProperty(
        name="TeraMesh offset",
        description="Vector, by which to offset TeraMesh files",
        default=(-5000.0, 0.0, -4000.0),
    )

    def draw(self, context):
        layout = self.layout

        col = layout.column()
        col.label(text="Import options: ")
        col.prop(self, "teraMeshTilingFloat")
        col.prop(self, "teraMeshOffsetVector")

    def convert(self, file):
        file_path = Path(self.directory) / file.name
        print(f"Reading '{file_path}'")
        # return Converter.Convert(str(file_path))
        pydatas = json.loads(
            subprocess.run([
                str(exe),
                str(file_path),
                str(self.teraMeshTilingFloat),
                *[str(f) for f in self.teraMeshOffsetVector]
            ], stdout=subprocess.PIPE).stdout.decode())

        print(f"Converting '{file_path}' to mesh.")

        # Construct the blender mesh
        for i, pydata in enumerate(pydatas):
            # mesh = bpy.data.meshes.new(pydata.Name)
            mesh = bpy.data.meshes.new(f"{file_path.stem}_{i}_{pydata['Name']}")
            obj = bpy.data.objects.new(mesh.name, mesh)
            bpy.context.collection.objects.link(obj)

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
                bm = bmesh.new()
                bm.from_mesh(mesh)
                bmesh.ops.convex_hull(bm, input=bm.verts)
                bm.to_mesh(mesh)
                mesh.update()

        print(f"Converting '{file_path.stem}' to mesh done!")

    def execute(self, context):
        with ThreadPoolExecutor() as executor:
            executor.map(self.convert, self.files)

        self.report({"INFO"}, "Collision import finished!")
        print("Collision import finished!")
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
