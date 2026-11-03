#!/bin/zsh
cd "${0:A:h}"
B=/Applications/Blender.app/Contents/MacOS/Blender
$B -b -P build.py -- --t 1    --out "$PWD/renders/blender_t01.png" --samples 96 --save kashi_sunrise.blend > renders/log_t01.txt 2>&1
$B -b -P build.py -- --t 14.5 --out "$PWD/renders/blender_t14.png" --samples 96 > renders/log_t14.txt 2>&1
$B -b -P build.py -- --t 29.5 --out "$PWD/renders/blender_t29.png" --samples 128 --save kashi_aarti.blend > renders/log_t29.txt 2>&1
echo ALL_DONE
