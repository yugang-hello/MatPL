add_definitions(-D_GLIBCXX_USE_CXX11_ABI=0)

# 1. Basic info
cmake_minimum_required(VERSION 3.2 FATAL_ERROR)
project(CalcOps)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED on)

# 2. Include Torch and Python paths
execute_process(COMMAND python3 -c "import torch; print(torch.utils.cmake_prefix_path)" OUTPUT_VARIABLE TORCH_CMAKE_PREFIX_PATH)
string(REPLACE "\n" "" TORCH_CMAKE_PREFIX_PATH ${TORCH_CMAKE_PREFIX_PATH})
list(APPEND CMAKE_PREFIX_PATH ${TORCH_CMAKE_PREFIX_PATH})

execute_process(COMMAND python3 -c "import sysconfig; print(sysconfig.get_paths()['include'])" OUTPUT_VARIABLE PYTHON_INCLUDE_DIR)
string(REPLACE "\n" "" PYTHON_INCLUDE_DIR ${PYTHON_INCLUDE_DIR})
execute_process(COMMAND python3 -c "import torch; print(torch.__path__[0])" OUTPUT_VARIABLE TORCH_PATH)
string(REPLACE "\n" "" TORCH_PATH ${TORCH_PATH})

include_directories(${PYTHON_INCLUDE_DIR})
include_directories(${TORCH_PATH}/include/)
include_directories(${TORCH_PATH}/include/torch/csrc/api/include/)

# 3. Set output directories
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin)
file(MAKE_DIRECTORY ${CMAKE_RUNTIME_OUTPUT_DIRECTORY})
set(CMAKE_LIBRARY_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/lib)
file(MAKE_DIRECTORY ${CMAKE_LIBRARY_OUTPUT_DIRECTORY})
set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/obj)
file(MAKE_DIRECTORY ${CMAKE_ARCHIVE_OUTPUT_DIRECTORY})

# 4. Detect if CUDA is available
execute_process(
    COMMAND python3 -c "import torch; print(torch.version.cuda is not None)"
    OUTPUT_VARIABLE HAS_CUDA_SUPPORT
    OUTPUT_STRIP_TRAILING_WHITESPACE
)

# 5. Always add CPU subdirectory
add_subdirectory(cmake/cpu)

# 6. Conditionally add GPU subdirectory
if(HAS_CUDA_SUPPORT)
    message(STATUS "CUDA is available. Adding GPU subdirectory.")
    add_subdirectory(cmake/gpu)
else()
    message(STATUS "CUDA is not available. Skipping GPU subdirectory.")
endif()
