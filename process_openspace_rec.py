import sys
import os

import rec2spice
import parse_openspace_rec


def main(os_rec_file, shot, version, newname, parse_function="et"):
    """
    processes a open space recording file (.osrectxt) into a spice kernel, then makes a frame dictionary (at default 60fps) and a plot of the result
    parse_function can be "et" or "all"
    """
    print(f"running rec2spice.rec2spice on {os_rec_file}")
    rec2spice.rec2spice(os_rec_file, shot, version, newname)

    print(f"running parse_openspace_rec.{parse_function} on {os_rec_file}")
    if parse_function == "et":
        parse_openspace_rec.et(os_rec_file)
    if parse_function == "all":
        parse_openspace_rec.all(os_rec_file)

    print(f"running parse_openspace_rec.plot on {os_rec_file}")
    parse_openspace_rec.plot(os_rec_file)
    print("processing complete!")


if __name__ == "__main__":
    if len(sys.argv)<5:
        print("python process_openspace_rec.py file.osrectxt shot# version# name [optional: 'et'/'all']")
        exit()
    args = sys.argv[1:]
    if len(args) < 5:
        parse = "et"
    else:
        parse = sys.argv[5]

    main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], parse)