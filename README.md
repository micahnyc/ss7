# ss7 - files

- kernelbuilding - this folder contains a few static files needed for making the kernels, also contains the .def files for locations maybe later will be removed by having scripts download /create static files
- rec2spice.py - main script for converting .osrectxt files from openspace to NAIF Spcie kernels
- mkgaia.py - downloads the kernels and model for gaia, and creates openspace asset
- mkmaunakea.py - creates a .bsp and .tf for Mauna Kea static position kernel