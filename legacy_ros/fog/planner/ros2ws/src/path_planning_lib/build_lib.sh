# Build FIelds2Cover Library
cd Fields2Cover;
mkdir -p build;
cd build;
cmake -DCMAKE_BUILD_TYPE=Release -DUSE_ORTOOLS_RELEASE=ON ..;
make -j$(nproc);

make install;


# Build Path Planning Lib Library
cd ..
python3 /app/ros2ws/src/path_planning_lib/setup.py bdist_wheel
cd dist && pip3 install *.whl --force-reinstall

