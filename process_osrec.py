import sys
import os

import osrec_to_spice
import osrec_to_dict


def main(os_rec_file, shot, version, newname, parse_function="et"):
    """
    processes a open space recording file (.osrectxt) into a spice kernel, then makes a frame dictionary (at default start frame of 1001, 60fps) and a plot of the result
    parse_function can be "et" or "all"
    """
    print(f"running osrec_to_spice.rec2spice on {os_rec_file}")
    osrec_to_spice.rec2spice(os_rec_file, shot, version, newname)

    print(f"running osrec_to_dict.{parse_function} on {os_rec_file}")
    if parse_function == "et":
        osrec_to_dict.et(os_rec_file)
    if parse_function == "all":
        osrec_to_dict.all(os_rec_file)

    print(f"running osrec_to_dict.plot on {os_rec_file}")
    osrec_to_dict.plot(os_rec_file)
    print("processing complete!")


if __name__ == "__main__":
    if len(sys.argv)<5:
        print("python process_osrec.py file.osrectxt shot# version# name [optional: et or all]")
        exit()
    args = sys.argv[1:]
    if len(args) < 5:
        parse = "et"
    else:
        parse = sys.argv[5]

    main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], parse)