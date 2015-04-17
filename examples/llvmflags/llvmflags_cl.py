#!/usr/bin/env python
#
# Autotune flags to g++ to optimize the performance of apps/raytracer.cpp
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

CLANGXX_PATH = '/Users/yygu/MIT/SuperUROP/build/Debug+Asserts/bin/clang++ -m32'
#CLANGXX_PATH = '/data/scratch/yygu/build/Debug+Asserts/bin/clang++'

OUTPUT_FILE = './tmp.bin'
PREPEND_FLAG = "-mllvm "
APP = 'apps/raytracer.cpp'

LLVM_FLAGS = [
  'simplifycfg-dup-ret',
  'simplifycfg-hoist-cond-stores'
]

# (name, min, max)
LLVM_PARAMS = [
  ('copy-factor', 0, 1000),
  ('unroll-runtime-count', 0, 1000),
  ('jump-threading-threshold', 0, 1000),
]

class LlvmFlagsTuner(MeasurementInterface):

  def manipulator(self):
    """
    Define the search space by creating a
    ConfigurationManipulator
    """
    manipulator = ConfigurationManipulator()
    manipulator.add_parameter(
      IntegerParameter('opt_level', 0, 3))
    for flag in LLVM_FLAGS:
      manipulator.add_parameter(
        EnumParameter(flag,
                      ['on', 'off', 'default']))
    for param, min, max in LLVM_PARAMS:
      manipulator.add_parameter(
        IntegerParameter(param, min, max))
    return manipulator

  def run(self, desired_result, input, limit):
    """
    Compile and run a given configuration then
    return performance
    """
    cfg = desired_result.configuration.data
    llvm_cmd = CLANGXX_PATH + ' ' + APP + ' -o ' + OUTPUT_FILE
    llvm_cmd += ' -O{0} '.format(cfg['opt_level'])

    for flag in LLVM_FLAGS:
      if cfg[flag] == 'on':
        llvm_cmd += PREPEND_FLAG + '-{0} '.format(flag)
      elif cfg[flag] == 'off':
        continue
    for param, min, max in LLVM_PARAMS:
      llvm_cmd += PREPEND_FLAG + '-{0}={1} '.format(param, cfg[param])
    
    print llvm_cmd

    compile_result = self.call_program(llvm_cmd)
    assert compile_result['returncode'] == 0

    
    run_result = self.call_program(OUTPUT_FILE)
    print run_result
    assert run_result['returncode'] == 0
    return Result(time=run_result['time'])

if __name__ == '__main__':
  argparser = opentuner.default_argparser()
  LlvmFlagsTuner.main(argparser.parse_args())
