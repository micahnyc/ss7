#make the mauna_kea spice kernels and openpace asset
import os
import shutil
import textwrap

name = "MAUNAKEA"

pck_url = "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/pck/pck00011.tpc"

scriptpath = os.path.dirname(os.path.realpath(__file__))
output = f"{scriptpath}/output"
kernels = f"{scriptpath}/kernelbuilding"

if os.path.exists(output) and os.path.isdir(output):
    shutil.rmtree(output)
os.makedirs(output)

os.system(f"wget -nc {pck_url} --directory-prefix {kernels}")

os.chdir(output)


site_definition = f"{kernels}/{name}.def"
command = f"pinpoint -def {site_definition} "
command += f"-pck {kernels}/pck00011.tpc "
command += f"-spk {output}/{name}.bsp "
command += f"-fk {output}/{name}.tf "

os.system(command)

asset_str = """local Kernels = {
    asset.localResource("%s.bsp"),
    asset.localResource("%s.tf"),
}

local position = {
    Identifier = '%s',
    Parent = 'Earth',
    Transform = {
        Translation = {
            Type = "SpiceTranslation",
            Target = "%s_SITE",
            Observer = "EARTH",
            Frame = "IAU_EARTH"
        }
    },
    Renderable = {
        Type = "RenderableCartesianAxes"
    },
    GUI = {
        Path = "/SS7",
        Name = "%s Position"
    }
}

asset.onInitialize(function()
    openspace.spice.loadKernel(Kernels)
    openspace.addSceneGraphNode(position)
end)

asset.onDeinitialize(function()
    openspace.removeSceneGraphNode(position)
    openspace.spice.unloadKernel(Kernels)
end)
""" % (name, name, name, name, name)

with open(f"{name}.asset", 'w') as f:
    asset_str = textwrap.dedent(asset_str)
    f.write(asset_str)
    f.close()
