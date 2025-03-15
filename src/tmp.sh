#!/bin/bash

current_path=$(pwd)

torch_lib_path=$(python3 -c "import torch; print(torch.__path__[0])")/lib

python_lib_path=$(dirname $(dirname $(which python3)))/lib

# write enviromenet to env.sh
cat <<EOF > ../env.sh
# Load for MatPL
export PYTHONPATH=$current_path:\$PYTHONPATH
export PATH=$current_path/bin:\$PATH

# Load for LAMMPS
export OP_LIB_PATH=$current_path/op/build/lib
export LD_LIBRARY_PATH=\$LD_LIBRARY_PATH:$torch_lib_path:$python_lib_path:$current_path/op/build/lib
EOF

echo ""
echo ""
echo "================================="
echo "MatPL has been successfully installed. Please load the MatPL environment variables before use."
echo "You can load the environment variables by running (recommended):"
echo ""
echo "  source $(dirname $current_path)/env.sh"
echo ""
echo "Or by executing the following commands:"
echo "  export PYTHONPATH=$current_path:\$PYTHONPATH"
echo "  export PATH=$current_path/bin:\$PATH"
echo "  # Load for LAMMPS"
echo "  export OP_LIB_PATH=$current_path/op/build/lib"
echo "  export LD_LIBRARY_PATH=\$LD_LIBRARY_PATH:$torch_lib_path:$python_lib_path:$current_path/op/build/lib"
echo ""
echo "=================================="


