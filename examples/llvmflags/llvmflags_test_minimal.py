#!/usr/bin/env python
#
# Autotune flags to LLVM to optimize the performance of apps/raytracer.cpp
#
# This is an extremely simplified version meant only for tutorials
#
import adddeps  # fix sys.path

import opentuner
from opentuner import ConfigurationManipulator
from opentuner import EnumParameter
from opentuner import IntegerParameter
from opentuner import MeasurementInterface
from opentuner import Result

#CLANGXX_PATH = '/Users/yygu/MIT/SuperUROP/build/Debug+Asserts/bin/clang++ -m32'
CLANGXX_PATH = '/data/scratch/yygu/build/Debug+Asserts/bin/clang++'

OUTPUT_FILE = './tmp.bin'
PREPEND_FLAG = '-O0 -D '
APP = 'test.cpp'
PARAM = 'N'

class LlvmFlagsTuner(MeasurementInterface):

  def __init__(self, *pargs, **kwargs):
    super(LlvmFlagsTuner, self).__init__(*pargs, **kwargs)

  def manipulator(self):
    """
    Define the search space by creating a
    ConfigurationManipulator
    """
    manipulator = ConfigurationManipulator()
    manipulator.add_parameter(IntegerParameter(PARAM, 0, 1000))
    return manipulator

  def run(self, desired_result, input, limit):
    """
    Compile and run a given configuration then
    return performance
    """
    cfg = desired_result.configuration.data
    llvm_cmd = CLANGXX_PATH + ' ' + APP + ' -o ' + OUTPUT_FILE + ' '

    llvm_cmd += PREPEND_FLAG + '{0}={1}'.format(PARAM, cfg[PARAM])
    
    print llvm_cmd

    compile_result = self.call_program(llvm_cmd, limit=10, memory_limit=1024**3)
    if compile_result['returncode'] != 0:
      return Result(state='ERROR', time=float('inf'))

    run_result = self.call_program(OUTPUT_FILE, limit=10, memory_limit=1024**3)
    print run_result
    if run_result['returncode'] != 0:
      return Result(state='ERROR', time=float('inf'))
      
    return Result(time=run_result['time'])

if __name__ == '__main__':
  argparser = opentuner.default_argparser()
  args = argparser.parse_args()
  LlvmFlagsTuner.main(args)
