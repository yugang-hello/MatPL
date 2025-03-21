#!/bin/bash
current_path=$(pwd)
parent_path=$(dirname "$current_path")
#torch_lib_path=$(python3 -c "import torch; print(torch.__path__[0])")/lib

#python_lib_path=$(dirname $(dirname $(which python3)))/lib

# write enviromenet to env.sh
cat <<EOF > ../env.sh
# Load for MatPL
export PYTHONPATH=$current_path:\$PYTHONPATH

export PATH=$current_path/bin:\$PATH
EOF

echo ""
echo ""
echo "================================="
echo "MatPL has been successfully installed. Please load the MatPL environment variables before use."
echo "You can load the environment variables by running (recommended):"
echo ""
echo "  source $parent_path/env.sh"
echo ""
echo "Or by executing the following commands:"
echo ""
echo "  export PYTHONPATH=$current_path:\$PYTHONPATH"
echo "  export PATH=$current_path/bin:\$PATH"
echo ""
echo "=================================="


