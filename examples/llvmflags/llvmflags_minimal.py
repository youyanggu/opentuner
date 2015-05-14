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

USE_ONLY_INTERNAL = False

# agg-antidep-debugdiv, align-all-blocks, asan-mapping-scale, etc.
PARAMS_EXTERNAL_FILE = 'working_params_external.txt'

# copy-factor, unroll-runtime-count, etc.
PARAMS_INTERNAL_FILE = 'params_internal.txt'

# aggregate-extracted-args, aggressive-ext-opt, align-neon-spills, etc.
FLAGS_EXTERNAL_FILE = 'working_flags_external.txt'
FLAGS_INTERNAL_FILE = 'flags_internal.txt'

OUTPUT_FILE = './tmp.bin'
PREPEND_FLAG = "-mllvm "
APP = 'apps/raytracer.cpp'

class LlvmFlagsTuner(MeasurementInterface):

  def __init__(self, *pargs, **kwargs):
    super(LlvmFlagsTuner, self).__init__(*pargs, **kwargs)
    self.llvm_flags_internal = self.convert_flags(FLAGS_INTERNAL_FILE)
    self.llvm_params_internal = self.convert_params(PARAMS_INTERNAL_FILE)
    self.llvm_flags_external = self.convert_flags(FLAGS_EXTERNAL_FILE)
    self.llvm_params_external = self.convert_params(PARAMS_EXTERNAL_FILE)

    if USE_ONLY_INTERNAL:
      self.llvm_flags = self.llvm_flags_internal
      self.llvm_params = self.llvm_params_internal
    else:
      self.llvm_flags = self.llvm_flags_internal + self.llvm_flags_external
      self.llvm_params = self.llvm_params_internal + self.llvm_params_external
    self.run_baselines()

  def run_baselines(self):
    results = []
    for i in range(4):
      llvm_cmd = '{} {} -o {} -O{}'.format(CLANGXX_PATH, APP, OUTPUT_FILE, i)
      compile_result = self.call_program(llvm_cmd)
      run_result = self.call_program(OUTPUT_FILE)
      results.append(run_result['time'])
    print "baseline perfs -O0={0:.4f} -O1={1:.4f} -O2={2:.4f} -O3={3:.4f}".format(*results)

  def convert_flags(self, fname):
    flags = []
    with open(fname) as f:
      for line in f:
        flags.append(line[:-1])
    return flags

  def convert_params(self, fname):
    params = []
    with open(fname) as f:
      for line in f:
        params.append((line[:-1], 0, 1000))
    return params

  def manipulator(self):
    """
    Define the search space by creating a
    ConfigurationManipulator
    """
    manipulator = ConfigurationManipulator()
    manipulator.add_parameter(
      IntegerParameter('opt_level', 0, 3))
    for flag in self.llvm_flags:
      manipulator.add_parameter(
        EnumParameter(flag,
                      ['on', 'off', 'default']))
    for param, min, max in self.llvm_params:
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

    for flag in self.llvm_flags:
      if cfg[flag] == 'on':
        llvm_cmd += PREPEND_FLAG + '-{0} '.format(flag)
      elif cfg[flag] == 'off':
        continue
    for param, min, max in self.llvm_params:
      llvm_cmd += PREPEND_FLAG + '-{0}={1} '.format(param, cfg[param])
    
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
