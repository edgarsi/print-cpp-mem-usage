#!/bin/bash

mkdir -p ~/tmp

#prog="~/critical/updateCarReports"
#args="3007"
#func="DbEntryLock::Acquire"

prog="./test"
args=
#func=f:breakpoint_here
func=st


echo "
b $func
run $args
print-cpp-mem-usage
c
q
" > commands.gdb

PYTHONPATH=$(pwd) \
  gdb \
  --eval-command="python import print_cpp_mem_usage" \
  -q -x commands.gdb \
  --args $prog

