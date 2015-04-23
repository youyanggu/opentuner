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

import os.path
import subprocess
import time


#CONFIG_FILE = 'lanka-llvm-opentuner.cfg'
CONFIG_FILE = 'Custom-macosx-llvm-opentuner.cfg'
ITERATIONS = 1

if CONFIG_FILE.startswith('lanka'):
  START_LINE = 130
  SPEC_DIR = '/data/scratch/yygu/spec/config/'
  SPEC_TEST = '483'
else:
  START_LINE = 45
  SPEC_DIR = '/Users/yygu/MIT/SuperUROP/spec/config/'
  SPEC_TEST = 'bzip'

PREPEND_FLAG = "-mllvm "
COMMON_LINE = None

USE_ONLY_INTERNAL = True
PARAMS_INTERNAL_FILE = 'params_internal.txt'
PARAMS_EXTERNAL_FILE = 'params_external.txt'
FLAGS_INTERNAL_FILE = 'flags_internal.txt'
FLAGS_EXTERNAL_FILE = 'flags_external.txt'

def get_elapsed_time(output):
  SPEC_RESULT_DIR = "spec/result/"
  BENCHMARK = "483.xalancbmk"

  csv_file_name = ""
  for line in output.split('\n'):
    if ".csv" in line:
      csv_file_name = line.split('/')[-1][:-1]
      break
  if not csv_file_name:
    print "Warning: csv file does not exist for slurm", slurm
    assert False
  times = []
  with open(SPEC_RESULT_DIR + csv_file_name, 'rb') as csv_file:
    reader = csv.reader(csv_file)
    for row in reader:
      if len(row) == 12 and row[0] == BENCHMARK and 'ref iteration' in row[-1]:
        times.append(float(row[2]))
  return sum(times) * 1.0 / len(times)

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
    global CONFIG_FILE, COMMON_LINE
    cfg = desired_result.configuration.data

    COMMON_LINE = 'OPTIMIZE = -O{0} '.format(cfg['opt_level'])
    total_flags = ''
    for flag in self.llvm_flags:
      if cfg[flag] == 'on':
        total_flags += PREPEND_FLAG + '-{0} '.format(flag)
      elif cfg[flag] == 'off':
        continue
    for param, min, max in self.llvm_params:
      total_flags += PREPEND_FLAG + '-{0}={1} '.format(
        param, cfg[param])
    addFlags(SPEC_DIR+CONFIG_FILE, total_flags)

    llvm_cmd = 'runspec --config=' + CONFIG_FILE + \
               ' --iterations=' + str(ITERATIONS) + ' --noreportable ' + SPEC_TEST
    
    print llvm_cmd
    run_result = self.call_program(llvm_cmd)
    print run_result
    assert run_result['returncode'] == 0

    elapsed_time = get_elapsed_time(run_result['stdout'])
    return Result(time=elapsed_time)

    """
    SLEEP = 60
    TIMEOUT = 6000
    DONE_FILE = 'DONE'

    BATCH_FILE = 'opentuner.batch'
    llvm_cmd = 'sbatch ' + BATCH_FILE
    proc = subprocess.Popen(llvm_cmd.split(), stdout=subprocess.PIPE)
    batch_line = proc.stdout.readline()
    batch_num = batch_line[20:-1]
    t = 0
    while (!os.path.isfile(DONE_FILE) and t<TIMEOUT):
      time.sleep(SLEEP)
      t+=SLEEP
    if os.path.isfile(DONE_FILE):
      os.remove(DONE_FILE)
    elapsed_time = get_elapsed_time(batch_num)
    return Result(time=elapsed_time)
    """
    

if __name__ == '__main__':
  argparser = opentuner.default_argparser()
  LlvmFlagsTuner.main(argparser.parse_args())
