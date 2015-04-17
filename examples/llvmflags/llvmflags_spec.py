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

#CONFIG_FILE = 'lanka-llvm'
CONFIG_FILE = 'Custom-macosx-llvm'
SPEC_TEST = 'bzip' # 483
ITERATIONS = 5

if CONFIG_FILE.startswith('lanka'):
  START_LINE = 130
  SPEC_DIR = '/data/scratch/yygu/spec/config/'
else:
  START_LINE = 45
  SPEC_DIR = '/Users/yygu/MIT/SuperUROP/spec/config/'

PREPEND_FLAG = "-mllvm "
COMMON_LINE = None

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

def addFlags(f, flags):
  import fileinput, sys
  print flags
  i = 0
  for line in fileinput.input(f, inplace=True):
    i+=1
    if i < START_LINE or i > START_LINE+2:
      sys.stdout.write(line)
      continue
    if i == START_LINE:
      print "C" + COMMON_LINE + flags
    elif i == START_LINE+1:
      print "CXX" + COMMON_LINE + flags
    elif i == START_LINE+2:
      print "F" + COMMON_LINE + flags
    else:
      raise RuntimeError("Shouldn't reach here.")
  fileinput.close()

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
    global CONFIG_FILE, COMMON_LINE
    cfg = desired_result.configuration.data
    CONFIG_FILE = SPEC_DIR + CONFIG_FILE + '-O{0}.cfg'.format(cfg['opt_level'])
    llvm_cmd = 'runspec --config=' + CONFIG_FILE.split('/')[-1] + \
               ' --iterations=' + str(ITERATIONS) + ' --noreportable ' + SPEC_TEST
    #llvm_cmd = 'g++ apps/raytracer.cpp -o ./tmp.bin'
    
    COMMON_LINE = 'OPTIMIZE = -O{0} '.format(cfg['opt_level'])
    total_flags = ''
    for flag in LLVM_FLAGS:
      if cfg[flag] == 'on':
        total_flags += PREPEND_FLAG + '-f{0} '.format(flag)
      elif cfg[flag] == 'off':
        continue
    for param, min, max in LLVM_PARAMS:
      total_flags += PREPEND_FLAG + '-{0}={1} '.format(
        param, cfg[param])
    addFlags(CONFIG_FILE, total_flags)

    #compile_result = self.call_program(llvm_cmd)
    #assert compile_result['returncode'] == 0

    print llvm_cmd
    run_result = self.call_program(llvm_cmd)
    print run_result
    assert run_result['returncode'] == 0
    return Result(time=run_result['time'])

if __name__ == '__main__':
  argparser = opentuner.default_argparser()
  LlvmFlagsTuner.main(argparser.parse_args())
