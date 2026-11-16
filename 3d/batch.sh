#!/bin/bash
# Render every Pokemon: T-pose shot, then battle video. Log to renders/batch.log
cd "$(dirname "$0")"
B=/opt/blender-dl/blender-4.2.23-linux-x64/blender
KEYS="${@:-swampidile swamporiaer swampest flamber flamezion blazian slimean slimarton slimontoon peeplet featherdash fiercebird}"
for k in $KEYS; do
  for mode in tpose video; do
    echo "$(date +%T) start $k $mode" >> renders/batch.log
    $B -b --factory-startup -P render.py -- $k $mode 2>&1 | grep -E "TPOSE|VIDEO|Error|Traceback" >> renders/batch.log
  done
done
echo "$(date +%T) ALL DONE" >> renders/batch.log
