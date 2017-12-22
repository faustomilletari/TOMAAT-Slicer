cmake_minimum_required(VERSION 3.5)

project(TOMAAT)

#-----------------------------------------------------------------------------
# Extension meta-information
set(EXTENSION_HOMEPAGE "https://github.com/faustomilletari/TOMAAT-Slicer")
set(EXTENSION_CATEGORY "Segmentation")
set(EXTENSION_CONTRIBUTORS "Fausto Milletari")
set(EXTENSION_DESCRIPTION "Segmentation of volumetric data via Deep learning based methods in the cloud")
set(EXTENSION_ICONURL "https://raw.github.com/faustomilletari/TOMAAT-Slicer/master/TOMAAT.png")
set(EXTENSION_SCREENSHOTURLS "http://www.example.com/Slicer/Extensions/TOMAAT/Screenshots/1.png")
set(EXTENSION_DEPENDS "NA") # Specified as a space separated string, a list or 'NA' if any

#-----------------------------------------------------------------------------
# Extension dependencies
find_package(Slicer REQUIRED)
include(${Slicer_USE_FILE})

#-----------------------------------------------------------------------------
# Extension modules
add_subdirectory(TOMAAT)
## NEXT_MODULE

#-----------------------------------------------------------------------------
include(${Slicer_EXTENSION_GENERATE_CONFIG})
include(${Slicer_EXTENSION_CPACK})
