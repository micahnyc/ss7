#rec2spice.py
import os
import sys
import textwrap
import platform
import json
from astropy.time import TimeDelta, Time
from astropy import units as u
import spiceypy
import shutil 

def rec2spice(filepath: str, shot: int, version: int, newname: str):
    """
    convert open space camera recording data to spice kernel
    ARGS:
        filepath(str): full path to the .osrectxt file
        shot(int): shot number, keep to two digits for now (to construct flight path id)
        version(int): version number, keep to two digits for now (to construct flight path id)
        newname(str): naif body name to assign to the flight path
    """
    scriptpath = os.path.dirname(os.path.realpath(__file__))

    spiceypy.spiceypy.furnsh(scriptpath + '/kernelbuilding/naif0012.tls')

    folderpath, filename = os.path.split(filepath)

    # windows
    # if (filename[0:2] == ".\\"):
    #     filename = filename[2:]
    file = open(filepath, 'r')
    Lines = file.readlines()

    SPICE_ID = f"-7{shot.zfill(2)}{version.zfill(2)}"
    SPICE_ID_POS = SPICE_ID[1:]
    SS7 = f"ss7_{SPICE_ID_POS}"
    FRAME_NAME = f"ASS7_SHOT_{shot}_V_{version}"
    GALACTIC_CK_FRAME = "GALACTIC"
    bspfile = SS7 + ".bsp"
    ckfile = SS7 + ".bc"
    sclkfile = SS7 + ".sclk"
    fkfile = SS7 + ".tf"

    dirpath = f"{folderpath}/{newname}_output/"
    if os.path.exists(dirpath) and os.path.isdir(dirpath):
        shutil.rmtree(dirpath)
    os.makedirs(dirpath)

    os.system(f"cp {scriptpath}/kernelbuilding/commnt.txt {dirpath}")
    os.system(f"cp {scriptpath}/kernelbuilding/naif0012.tls {dirpath}")
    #string in file that represents switching targets
    SWITCHSTR = 'openspace.setPropertyValueSingle("NavigationHandler.OrbitalNavigator.Anchor'

    #string in file that represents switching targets
    DELTA_TIME = 'DeltaTime'

    # getting kernel info from kernel_data.json file (in same folder as this)
    with open(f"{scriptpath}/kernel_data.json", "r") as f:
        kernel_data = json.load(f)

    NAIF_CODES = kernel_data["IDS"]["NAIF_CODES"]
    IFRAMES = kernel_data["IDS"]["IFRAMES"]
    KERNELS = kernel_data["KERNELS"]

    #loop thru lines of file to create 'frames' for each segment of the recording based on target
    count = 0
    masterFrames = []
    frames = []
    focus = ''
    deltaTimes = []
    focusList = []

    for line in Lines:
        components = line.split(" ")
        if (components[0] == 'camera'):
            frames.append({'et':float(components[3]),
                            'x': float(components[4]),
                            'y': float(components[5]),
                            'z': float(components[6]),
                            'i': float(components[7]),
                            'j': float(components[8]),
                            'k': float(components[9]),
                            'l': float(components[10]),
                            'focus': components[-1].strip()})
            focus = components[-1].strip()
            focusList.append(focus)
            shotLength = components[2]
        elif (SWITCHSTR in line):
            newfocus = line[line.rindex(',')+3: -3]
            #focus is switched, add frames to master list and create new list
            masterFrames.append(frames)
            frames = []
            focus = newfocus
        elif (DELTA_TIME in line):
            script = components[-1]
            dt = script[script.index('(')+1 : script.index(')')]
            timeChange = {
                "frameTime": components[2],
                "et": components[3],
                "deltaTime": dt
            }
            deltaTimes.append(timeChange)
        # else:
        #     print(f"unhandled script line: {line}")
        count += 1

    masterFrames.append(frames) #add final list of frames to master list

    #loop throu master list and add velocities 
    for frames in masterFrames:
        count = 0
        framecount = len(frames)
        for frame in frames:
            if ( (count > 0) and (count < framecount-1) ): #skip first and last frames when calc'ing central difference 
                dt = frames[count+1]['et'] - frames[count-1]['et']
                dx = frames[count+1]['x']  - frames[count-1]['x']
                dy = frames[count+1]['y'] - frames[count-1]['y']
                dz = frames[count+1]['z'] - frames[count-1]['z']
                frame['vx'] = dx/dt
                frame['vy'] = dy/dt
                frame['vz'] = dz/dt
            count += 1
        #ditch first and last frames with no velocity
        frames.pop(0)
        frames.pop(-1)

    #create orientation frames
    with open(dirpath + 'ori' + '.dat', 'w') as f:
        for frames in masterFrames:
            for frame in frames:
                line = "{}, {}, {}, {}, {}\n".format(
                    frame['et'], frame['i'], frame['j'], frame['k'], frame['l'])
                f.write(line)
        f.close()
    #generate ss7_SPICEID.fk
    with open(f"{dirpath}ss7_{SPICE_ID[1:]}.tf", 'w') as f:
        fkfile = """
        \\begindata
            FRAME_{fn}     = {si}000
            FRAME_{si}000_NAME        = '{fn}'
            FRAME_{si}000_CLASS       = 3
            FRAME_{si}000_CLASS_ID    = {si}000
            FRAME_{si}000_CENTER      = {si}
            CK_{si}000_SCLK           = {si}
            CK_{si}000_SPK            = {si}
        \\begintext\n\n
        """.format(fn=FRAME_NAME, si=SPICE_ID)

        fkfile += """\\begindata
          NAIF_BODY_NAME += ( '{nn}' )
          NAIF_BODY_CODE += ( {si} )
        \\begintext
        """.format(nn=newname, si=SPICE_ID)

        f.write(fkfile)
        f.close()

    #generate setup.msopck
    with open(dirpath + SS7 + ".msopck", 'w') as f:
        msopck = """
        \\begindata

        LSK_FILE_NAME           = 'naif0012.tls'
        MAKE_FAKE_SCLK          = '%s'
        FRAMES_FILE_NAME        = '%s.tf'

        INTERNAL_FILE_NAME      = '%s'
        COMMENTS_FILE_NAME      = 'commnt.txt'

        CK_TYPE                 = 3
        CK_SEGMENT_ID           = 'CAMERA ROTATION'
        INSTRUMENT_ID           = %s
        REFERENCE_FRAME_NAME    = '%s'
        ANGULAR_RATE_PRESENT    = 'MAKE UP/NO AVERAGING'

        INPUT_TIME_TYPE         = 'ET'
        INPUT_DATA_TYPE         = 'MSOP QUATERNIONS',

        PRODUCER_ID             = 'rec2spice.py'

        \\begintext
        """ % (sclkfile, SS7, 'ori.dat', f"{SPICE_ID}000", GALACTIC_CK_FRAME)
        textwrap.dedent(msopck)
        f.write(msopck)
        f.close()
        mkcmd =  "msopck.exe" if platform.system() == 'Windows' else "msopck"
        syscmd = f"{mkcmd} {SS7}.msopck ori.dat {SS7}.bc"
        os.chdir(dirpath)
        os.system(syscmd)

    #generate spk
    for i, frames in enumerate(masterFrames):
        focus = frames[0]['focus']
        #create .dat _position files formatted for spice with one lines per frame
        with open(dirpath + focus + '_pos' + '.dat', 'w') as f:
            for frame in frames:
                line = "{}, {}, {}, {}, {}, {}, {}\n".format(
                    frame['et'], frame['x'], frame['y'], frame['z'], frame['vx'], frame['vy'], frame['vz'])
                f.write(line)
            if i < (len(masterFrames)-1):
                connectionLine = "{}, {}, {}, {}, {}, {}, {}\n".format(
                    masterFrames[i+1][0]['et'], 
                    masterFrames[i][-1]['x'],
                    masterFrames[i][-1]['y'],
                    masterFrames[i][-1]['z'],
                    masterFrames[i][-1]['vx'],
                    masterFrames[i][-1]['vy'],
                    masterFrames[i][-1]['vz'])
                f.write(connectionLine)
            f.close()


        #generate setup.mkspk
        center_id = NAIF_CODES[focus]
        if (not center_id):
            print("Existing due to error looking up naif id for " + focus)
            exit(-1)
        with open(dirpath + focus+".mkspk", 'w') as f:
            mkspk = f"""\\begindata
                INPUT_DATA_TYPE   = 'STATES'
                DATA_ORDER        = 'epoch x y z vx vy vz '
                DATA_DELIMITER    = ','
                LINES_PER_RECORD  = 1
                PRODUCER_ID       = 'OpenSpace (rec2spice)'
                OUTPUT_SPK_TYPE   = 13
                INPUT_DATA_UNITS  = ('DISTANCES=METERS')
                CENTER_ID         = {str(center_id)}
                OBJECT_ID         = {SPICE_ID}
                REF_FRAME_NAME    = '{GALACTIC_CK_FRAME}'
                LEAPSECONDS_FILE  = 'naif0012.tls'
                INPUT_DATA_FILE   = '{focus + '_pos.dat'}'
                OUTPUT_SPK_FILE   = '{SS7}.bsp'
                COMMENT_FILE      = 'commnt.txt'
                POLYNOM_DEGREE    = 11
                TIME_WRAPPER      = '# ETSECONDS'
                APPEND_TO_OUTPUT  = 'YES'
            \\begintext\n"""
            textwrap.dedent(mkspk)
            f.write(mkspk)
            f.close()
            mkcmd =  "mkspk.exe" if platform.system() == 'Windows' else "mkspk"
            os.chdir(dirpath)
            os.system(f"{mkcmd} -setup {dirpath}{focus}.mkspk")
        
    #create meta kernel --TODO fix
    with open (f"{dirpath}{SS7}.tm", 'w') as f:

        metakernel = f"""
        \\begindata
        KERNELS_TO_LOAD = ( '{fkfile}',
                            '{sclkfile}',
                            '{bspfile}',
                            '{ckfile}')  
        \\begintext
        """
        f.write(metakernel)
        f.close()

    #create openspace asset
    with open(f"{dirpath}ss7_{SPICE_ID_POS}.asset", 'w') as f:
        asset_str = """    
        local sun = asset.require("scene/solarsystem/sun/sun")
        local name = '%s'
        local Kernels = {
            asset.localResource('ss7_%s' .. '.sclk'),
            asset.localResource('ss7_%s' .. '.tf'),
            asset.localResource('ss7_%s' .. '.bsp'),
            asset.localResource('ss7_%s' .. '.bc')
        }
        
        local pos = {
            Identifier = name .. '_pos',
            Parent = 'SolarSystemBarycenter',
            Transform = {
                Translation = {
                    Type = "SpiceTranslation",
                    Target = "%s",
                    Observer = '0',
                    Frame = "GALACTIC"
                },
                Rotation = {
                    Type = "SpiceRotation",
                    SourceFrame = "%s",
                    DestinationFrame = 'GALACTIC',
                }
            },
            Renderable = {
                Type="RenderableModel",
                GeometryFile = asset.localResource("xwing.glb"),
                RotationVector = {0, 180, 0}
            },
            BoundingSphere = 10,
            InteractionSphere = 5,
            GUI = {
                Path = '/SS7',
                Name = name .. " position"
            }
        }

        local renderable = {
            Identifier = '%s_visual',
            Parent = pos.Identifier,
            BoundingSphere = 30,
            InteractionSphere = 1,
            Renderable = {
                Type="RenderableModel",
                GeometryFile = asset.localResource("xwing.glb"),
                RotationVector = {0, 180, 0}
            },
            GUI = {
                Path = '/SS7',
                Name = name .. " visual"
            }
        }

        local trails = {}
        """ % (newname, SPICE_ID_POS, SPICE_ID_POS, SPICE_ID_POS, SPICE_ID_POS, SPICE_ID, FRAME_NAME, SPICE_ID)

        for frames in masterFrames:
            et_start = frames[0]['et']
            et_end = frames[-1]['et']
            iso_start = spiceypy.spiceypy.et2utc(et_start, 'ISOC', 8)
            iso_end = spiceypy.spiceypy.et2utc(et_end, 'ISOC', 8)

            focus = frames[0]['focus']
            asset_str += """local %s_trail = {
                Identifier = '%s_trail',
                Parent = "%s",
                Renderable = {
                    Type = "RenderableTrailTrajectory",
                    Translation = {
                        Type = "SpiceTranslation",
                        Target = "%s",
                        Observer = '%s',
                        Frame = "%s"
                    },
                    Color = { 0.9, 0.9, 0.0 },
                    StartTime = '%s',
                    EndTime = '%s',
                    SampleInterval = 1,
                    TimeStampSubsampleFactor = 1,
                    EnableFade = false,
                    ShowFullTrail = true
                },
                GUI = {
                    Path = '/SS7',
                    Name = name .. "_%s trail"
                }
            }\n
            table.insert(trails, %s_trail)
            """ % (focus, focus, focus, SPICE_ID,  NAIF_CODES[focus], IFRAMES[focus], iso_start, iso_end, focus, focus)

        asset_str += """
        asset.onInitialize(function()
            openspace.spice.loadKernel(Kernels)
            openspace.addSceneGraphNode(pos)
            openspace.addSceneGraphNode(renderable)
            for _, n in ipairs(trails) do
                openspace.addSceneGraphNode(n);
            end
        end)

        asset.onDeinitialize(function()
            openspace.removeSceneGraphNode(renderable)
            openspace.removeSceneGraphNode(pos)
            for _, n in ipairs(trails) do
                openspace.removeSceneGraphNode(n);
            end
            openspace.spice.unloadKernel(Kernels)
        end)
        """
        asset_str = textwrap.dedent(asset_str)
        f.write(asset_str)
        f.close()

    focusList = list(set(focusList))

    fullKernelList = KERNELS['OpenSpace']
    for focus in focusList:
        try:
            ker = KERNELS[focus]
            fullKernelList = fullKernelList + KERNELS[focus]
        except:
            print(f"{focus} handled by OpenSpace kernels")

    with open (f"{dirpath}{newname}.json", 'w') as f:
        dataobject = {
            "name": newname,
            "shot": shot,
            "take": version,
            "osrecording": filename,
            "shotLength": float(shotLength),
            "shotStart": masterFrames[0][0]['et'],
            "shotEnd": masterFrames[-1][-1]['et'],
            "deltaTimes": deltaTimes,
            "kernels": fullKernelList
        }
        f.write(json.dumps(dataobject, indent=4))
        f.close()


###########END
#astropy conver
#iso_start = (Time(2000, format='jyear') + TimeDelta(et_start*u.s)).iso
#iso_end = (Time(2000, format='jyear') + TimeDelta(et_end*u.s)).iso

#spicepyconvert
# iso_start = spiceypy.spiceypy.et2utc(et_start, 'ISOC', 8)
# iso_end = spiceypy.spiceypy.et2utc(et_end, 'ISOC', 8)

# print(f"start {iso_start} | end {iso_end}")


if __name__ == "__main__":
    # argv = [thisFile, pathToRecFile, shot, version, name]
    if len(sys.argv) < 5:
        print("python rec2pice.py file.osrectxt shot# version# name")
        exit()
    rec2spice(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])

