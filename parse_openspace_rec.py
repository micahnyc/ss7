import os
from pprint import pprint
import json
import sys


def process_rec_data(rec_path, write=False):
    """
    Converts data file to dict. Assumes comment line (#) for each step comes before each camera line
    RETURN:
        dict:
            {   record time: {
                    "session_time":float, 
                    "et":float, 
                    "pos":[float, float, float], 
                    "quat":[float, float, float, float], 
                    "node":"someNodeName", 
                }
            }
    """
    data = {}
    matrix_list = None
    with open(rec_path) as file:
        for line in file:
            if line.startswith("#"):
                pass
                # matrix_str = line.split()[1]
                # matrix_list = [float(x.replace("{", "").replace("}", "")) for x in matrix_str.split(",")]
            if line.startswith("camera"):
                line_list = line.split()
                key_val = float(line_list[2])
                data[key_val] = {} # record time

                data[key_val]["session_time"] = float(line_list[1]) # secs since openspace session start
                data[key_val]["et"] = float(line_list[3]) #  secs since rec start
                data[key_val]["pos"] = [float(line_list[4]), float(line_list[5]), float(line_list[6])] # cam position in m from "node" coordinate system
                data[key_val]["quat"] = [float(line_list[7]), float(line_list[8]), float(line_list[9]), float(line_list[10])] # quat rot from "node"
                data[key_val]["scale"] = float(line_list[11]) # camera scale
                data[key_val]["node"] = line_list[13] # node we"re focusing on
    
    if write: # write a json file next to the osrectxt file
        write_json(rec_path, data, "rec_data")

    return(data)


def plot_rectime_et(rec_path):
    """
    Makes a graph plotting the record time in seconds (x) and the associated et values (y)
    """
    try:
        import matplotlib.pyplot as plt
    except:
        print("matplotlib is not found. Try running from a python env that has it (like ss7)")

    data_dict = process_rec_data(rec_path)
    times = []
    ets = []
    for k, v in data_dict.items():
        times.append(k)
        ets.append(data_dict[k]["et"])

    plt.plot(times, ets)
    plt.show()


def convert_to_frames_et_dict(  rec_path, 
                                start_frame=1001, 
                                fps=60,
                                write=True):
    """
    Converts data from rec_path to frame based intervals and lerps the et values for those samples

    ARGS:
        rec_path(str): path to osrectxt file recording
        start_frame(int): animation start frame
        fps(int): frames per second of animation recording
        write(bool): whether to write a json file of the output to the location of the rec_path?

    RETURN:
        dict: {int:float}
    """
    start_frame = int(start_frame)
    fps = int(fps)
    data_dict = process_rec_data(rec_path) # get data as dict w record time samples keys 
    raw_frame_dict = to_raw_frame_dict(data_dict, start_frame, fps) # convert that to dict with float frames as keys 
    raw_frame_list = sorted(raw_frame_dict.keys()) # get list of float frame values
    
    int_frame_dict = {} # dictionary we"re making with integer frame keys
    raw_frame_list = sorted(list(raw_frame_dict.keys())) # get and sort time stamps from incoming data parse
    
    # first two frames. Just to be safe (from tiny et lerps), we"ll start w the second rectime and interp the second frame
    int_frame_dict[0 + start_frame] = raw_frame_dict[raw_frame_list[1]]["et"]
    
    for x in range(2, len(raw_frame_list)-1): #skipping the second frame to prevent any tiny lerp issues putting us out of range
        round_key = round(raw_frame_list[x])
        if round_key in int_frame_dict:
            continue
        percent = (raw_frame_list[x+1]-raw_frame_list[x])/(raw_frame_list[x+1]-raw_frame_list[x-1]) # what % is the frame rectime relative to prev, next
        int_frame_dict[round_key] = interp_value(raw_frame_dict[raw_frame_list[x-1]]["et"], raw_frame_dict[raw_frame_list[x+1]]["et"], percent) # current frame et is lerp between previous and last record time ets
    
    if write: # write a json file next to the osrectxt file
        write_json(rec_path, int_frame_dict, "frames_et")

    return(int_frame_dict)


def convert_to_frame_data_dict( rec_path, 
                                start_frame=1001, 
                                fps=60,
                                write=True):
    """
    Converts data from process_rec_data to frame based intervals  via lerp pos, rot between et values to get frame values

    ARGS:
        rec_path(str): path to recording file
        start_frame(int): starting frame for conversion
        fps(int): frames per second of the recording
        write(bool): whether to write the output to a json file (at same location as recording file)

    RETURN:
        dict:   {int:{
                        "rectime":  float,
                        "et":       float,
                        "pos":      [float, float, float],
                        "quat":     [float, float, float],
                        "scale":    float,
                        "node":     "node_name",
                    }

                }
    """
    start_frame = int(start_frame)
    fps = int(fps)
    data_dict = process_rec_data(rec_path)
    raw_frame_dict = to_raw_frame_dict(data_dict, start_frame, fps) # convert that to dict with float frames as keys 
    raw_frame_list = sorted(raw_frame_dict.keys()) # get list of float frame values

    int_frame_dict = {} # dictionary we"re making with integer frame keys
    raw_frame_list = sorted(list(raw_frame_dict.keys())) # get and sort time stamps from incoming data parse

    # set first frame, not lerping this
    int_frame_dict[0 + start_frame] = { "et": raw_frame_dict[raw_frame_list[1]]["et"],
                                        "rectime": raw_frame_dict[raw_frame_list[1]]["rectime"],
                                        "pos": raw_frame_dict[raw_frame_list[1]]["pos"],
                                        "quat": raw_frame_dict[raw_frame_list[1]]["quat"],
                                        "scale": raw_frame_dict[raw_frame_list[1]]["scale"],
                                        "node": raw_frame_dict[raw_frame_list[1]]["node"], 
                                        }
    
    for x in range(2, len(raw_frame_list)-1):
        round_key = round(raw_frame_list[x])
        if round_key in int_frame_dict:
            continue
        int_frame_dict[round_key] = {}
        percent = (raw_frame_list[x+1]-raw_frame_list[x])/(raw_frame_list[x+1]-raw_frame_list[x-1]) # what % is the frame rectime relative to prev, next
        int_frame_dict[round_key]["et"] = interp_value(raw_frame_dict[raw_frame_list[x-1]]["et"], raw_frame_dict[raw_frame_list[x+1]]["et"], percent) # current frame et is lerp between previous and last record time ets
        int_frame_dict[round_key]["rectime"] = interp_value(raw_frame_dict[raw_frame_list[x-1]]["rectime"], raw_frame_dict[raw_frame_list[x+1]]["rectime"], percent)
        # lerp pos and rot values from prev and next et vals from t(%) of current frame et value
        pos_list = []
        for y in range(3):
            pos_list.append(interp_value(raw_frame_dict[raw_frame_list[x-1]]["pos"][y], raw_frame_dict[raw_frame_list[x+1]]["pos"][y], percent))
        quat_list = []
        for y in range(4):
            quat_list.append(interp_value(raw_frame_dict[raw_frame_list[x-1]]["quat"][y], raw_frame_dict[raw_frame_list[x+1]]["quat"][y], percent))
        # build out dict for current frame
        int_frame_dict[round_key]["pos"] = pos_list
        int_frame_dict[round_key]["quat"] = quat_list
        int_frame_dict[round_key]["scale"] = raw_frame_dict[raw_frame_list[x]]["scale"]
        int_frame_dict[round_key]["node"] = raw_frame_dict[raw_frame_list[x]]["node"]

    if write:
        write_json(rec_path, int_frame_dict, "frames_data")

    return(int_frame_dict)


def to_raw_frame_dict(rectime_dict, start_frame, fps):
    start_frame = int(start_frame)
    fps = int(fps)
    rec_time_list = sorted(rectime_dict.keys())
    frame_time = 1.0/fps
    raw_frame_dict = {}
    for i, rectime in enumerate(rec_time_list):
        time_diff = rec_time_list[i] - rec_time_list[0]
        frame_diff = time_diff *  fps
        raw_frame_dict[frame_diff + start_frame] = rectime_dict[rec_time_list[i]]
        raw_frame_dict[frame_diff + start_frame]["rectime"] = rectime
    write_json(r"/HD/rcp/project/ss7/resource/asset/AMNH/files/openspace/flightpaths/maunakea/24_03_25/ss7-1_2.osrectxt", raw_frame_dict, "raw_frames")
    return(raw_frame_dict)


def interpolate(x1: float, x2: float, y1: float, y2: float, x: float):
    """Perform linear interpolation for % x between (x1,y1) and (x2,y2) """
    return ((y2 - y1) * x + x2 * y1 - x1 * y2) / (x2 - x1)


def interp_value(start, end, t):
    """given some percentage t, find the proportional value between start, end"""
    return(((float(end)-float(start))*t)+float(start))


def write_json(orig_path, dictionary, suffix):
    data_dir, data_file = os.path.split(orig_path)
    file_name = "{0}_{1}.json".format(data_file.split(".")[0], suffix)
    data_file_path = os.path.join(data_dir,file_name)
    with open(data_file_path, "w") as f:
        json.dump(dictionary, f, indent=4)


def et(*args):
    """
    shortcut for cli to convert_to_frames_et_dict()
    ex:
    python path/to/parse_openspace.py et path/to/osrectxt 1001 60 1
    """
    convert_to_frames_et_dict(*args)


def all(*args):
    """
    shortcut for cli to convert_to_frames_data_dict()
    ex:
    python path/to/parse_openspace.py all path/to/osrectxt 1001 60 1
    """
    convert_to_frame_data_dict(*args)


def plot(*args):
    """
    shortcut for cli to plot_rectime_et()
    ex:
    python path/to/parse_openspace.py plot path/to/osrectxt
    """
    plot_rectime_et(*args)


def main(func):
    arg_list = [sys.argv[2]]
    args = [int(x) for x in sys.argv[3:]]
    arg_list.extend(args)
    func(*arg_list)


if __name__ == "__main__":
    arg_list  = sys.argv[2:]
    func = getattr(sys.modules[__name__], sys.argv[1])
    main(func)


"""
<from alex to micah> (note: we"re skipping the matrix bits. . .)
Here is the type of files that Carter will generate;
Each line after the first starts with one of three strings:
camera: the rest of the line is a camera keyframe
script: the rest of the line is a script frame
#: The rest of a line is a comment that OpenSpace ignores
For both  camera  and script  frames the next three numbers are different time information, all in seconds. First number is the time since this OpenSpace instance was started; Second number is how many seconds into the recording we are; Third number is the number if seconds since J2000 epoch (2000 JAN 01 12:00:00  ephemeris time).
For a script frame, the next number is the number of linebreaks in the script;  usually =1. The rest of the line is the actual Lua script that was executed.
For a camera frame, the next numbers are:  3 position values of the camera in the coordinate system of the focus node in x,y,z in meters;  then 4 values that are the x,y,z,w components of the quaternion for the camera rotation; followed by our internal scaling of the scene; next either an F or - depending on if the camera is dragged along the focus node rotationally (you can ignore), followed by the name of the focus nod
e.
I added the model view matrix as a comment line in the row before the camera. Such line starts with # for a comment and the a { and the final character before the newline is a }  in between are 16 comma-separated numbers for the full model matrix M so that rot * M * pos (pos from the three values from the next row"s camera frame and rot the rotation quaterion from next row"s camera frame) should give you the total position an orientation of the camera in Galactic coordinates with a position relative to the solar system barycenter.
The matrices in GLM are column-major, so the first four values are the first column of the matrix, the second four values are the second column, etc.
"""