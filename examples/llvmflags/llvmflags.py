#!/usr/bin/env python
#
# Autotune flags to g++ to optimize the performance of apps/raytracer.cpp
#
# This is an extremely simplified version meant only for tutorials
#
import adddeps  # fix sys.path

import argparse
import logging
import os
import shutil

import opentuner
from opentuner import ConfigurationManipulator
from opentuner import EnumParameter
from opentuner import IntegerParameter
from opentuner import MeasurementInterface
from opentuner import Result

#CLANGXX_PATH = '/Users/yygu/MIT/SuperUROP/build/Debug+Asserts/bin/clang++ -m32'
CLANGXX_PATH = '/data/scratch/yygu/build/Debug+Asserts/bin/clang++'

DEFAULT_PARAM_VALUE = 500
MIN_VAL = 0
MAX_VAL = 1000
PARAMS_INTERNAL_FILE = 'params_internal.txt'
PARAMS_EXTERNAL_FILE = 'params_external.txt'
FLAGS_INTERNAL_FILE = 'flags_internal.txt'
FLAGS_EXTERNAL_FILE = 'flags_external.txt'

PREPEND_FLAG = "-mllvm "

log = logging.getLogger('llvmflags')

argparser = argparse.ArgumentParser(parents=opentuner.argparsers())
argparser.add_argument('source', help='source file to compile')
argparser.add_argument('--compile-template',
                       default='{clang} {source} -o {output} {flags}',
                       help='command to compile {source} into {output} with'
                            ' {flags}')
argparser.add_argument('--output', default='./tmp.bin',
                       help='temporary file for compiler to write to')
argparser.add_argument('--compile-limit', type=float, default=10,
                       help='kill clang if it runs more than {default} sec')
argparser.add_argument('--clang', default='clang++', help='clang++ or clang')
argparser.add_argument('--force-killall', action='store_true',
                       help='killall cc1plus before each collection')
argparser.add_argument('--memory-limit', default=1024 ** 3, type=int,
                       help='memory limit for child process')
argparser.add_argument('--logfile', default=None,
		       help='log file')
argparser.add_argument('--use-internal', action='store_true') 
argparser.add_argument('--use-external', action='store_true') 
argparser.add_argument('--use-params', action='store_true') 
argparser.add_argument('--use-flags', action='store_true') 

class LlvmFlagsTuner(MeasurementInterface):

  def __init__(self, *pargs, **kwargs):
    super(LlvmFlagsTuner, self).__init__(*pargs, **kwargs)
    self.llvm_flags_internal = self.convert_flags(FLAGS_INTERNAL_FILE)
    self.llvm_params_internal = self.convert_params(PARAMS_INTERNAL_FILE)
    self.llvm_flags_external = self.convert_flags(FLAGS_EXTERNAL_FILE)
    self.llvm_params_external = self.convert_params(PARAMS_EXTERNAL_FILE)

    self.llvm_flags = self.extract_working_flags()
    self.llvm_params = self.extract_working_params()

    # this flag is necessary so that each new command is compiled each time
    self.parallel_compile = True
    try:
      os.stat('./tmp')
    except OSError:
      os.mkdir('./tmp')
    self.run_baselines()

  def run_baselines(self):
    log.info("baseline perfs -O0=%.4f -O1=%.4f -O2=%.4f -O3=%.4f",
             *[self.run_with_flags(['-O{}'.format(i)], None).time
               for i in range(4)])

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
        params.append(line[:-1])
    return params

  def check_if_flag_works(self, flag):
    if flag not in ['O0', 'O1', 'O2', 'O3']:
      flag = 'mllvm -' + flag
    flag = '-' + flag
    print flag
    cmd = args.compile_template.format(source=args.source, output=args.output,
                                       flags=flag, clang=args.clang)
    compile_result = self.call_program(cmd, limit=args.compile_limit)
    if compile_result['returncode'] != 0:
      log.warning("removing flag {} because it results in compile error".format(flag))
      return False
    return True

  def extract_working_flags(self):
    """
    Figure out which gcc flags work (don't cause gcc to barf) by running
    each one.
    """
    if not args.use_flags:
      return []
    all_flags = []
    if args.use_internal or not args.use_external:
      all_flags += self.llvm_flags_internal
    if args.use_external:
      all_flags += self.llvm_flags_external

    working_flags = filter(self.check_if_flag_works, all_flags)
    return working_flags

  def extract_working_params(self):
    """
    Figure out which clang params work (don't cause clang to barf) by running
    each one.
    """
    if not args.use_params and args.use_flags:
      return []
    all_params = []
    if args.use_internal or not args.use_external:
      all_params += self.llvm_params_internal
    elif args.use_external:
      all_params += self.llvm_params_external

    working_params = []
    for param in all_params:
      if self.check_if_flag_works('{}={}'.format(param, DEFAULT_PARAM_VALUE)):
          working_params.append(param)
    return working_params

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
    for param in self.llvm_params:
      manipulator.add_parameter(
        IntegerParameter(param, MIN_VAL, MAX_VAL))
    return manipulator

  def cfg_to_flags(self, cfg):
    flags = ['-O%d' % cfg['opt_level']]
    for flag in self.llvm_flags:
      if cfg[flag] == 'on':
        flags.append(PREPEND_FLAG + '-' + flag)

    for param in self.llvm_params:
      flags.append(PREPEND_FLAG + '-{}={}'.format(param, cfg[param]))

    return flags

  def get_tmpdir(self, result_id):
    return './tmp/{}'.format(result_id)

  def cleanup(self, result_id):
    tmp_dir = self.get_tmpdir(result_id)
    shutil.rmtree(tmp_dir)

  def run(self, desired_result, input, limit):
    pass

  compile_results = {'ok': 0, 'timeout': 1, 'error': 2}

  def compile(self, config_data, result_id):
    flags = self.cfg_to_flags(config_data)
    return self.compile_with_flags(flags, result_id)

  def run_precompiled(self, desired_result, input, limit, compile_result,
                      result_id):
    if self.args.force_killall:
      os.system('killall -9 cc1plus 2>/dev/null')
    # Make sure compile was successful
    if compile_result == self.compile_results['timeout']:
      return Result(state='TIMEOUT', time=float('inf'))
    elif compile_result == self.compile_results['error']:
      return Result(state='ERROR', time=float('inf'))

    tmp_dir = self.get_tmpdir(result_id)
    output_dir = '{}/{}'.format(tmp_dir, args.output)
    try:
      run_result = self.call_program([output_dir], limit=limit,
                                     memory_limit=args.memory_limit)
    except OSError:
      return Result(state='ERROR', time=float('inf'))

    print run_result

    if run_result['returncode'] != 0:
      if run_result['timeout']:
        return Result(state='TIMEOUT', time=float('inf'))
      else:
        log.error('program error')
        return Result(state='ERROR', time=float('inf'))

    return Result(time=run_result['time'])

  def compile_with_flags(self, flags, result_id):
    tmp_dir = self.get_tmpdir(result_id)
    try:
      os.stat(tmp_dir)
    except OSError:
      os.mkdir(tmp_dir)
    output_dir = '{}/{}'.format(tmp_dir, args.output)
    cmd = args.compile_template.format(source=args.source, output=output_dir,
                                       flags=' '.join(flags),
                                       clang=args.clang)

    compile_result = self.call_program(cmd, limit=args.compile_limit,
                                       memory_limit=args.memory_limit)
    if compile_result['returncode'] != 0:
      if compile_result['timeout']:
        #log.warning("clang timeout")
        return self.compile_results['timeout']
      else:
        log.warning("clang error %s", compile_result['stderr'])
        self.debug_gcc_error(flags)
        return self.compile_results['error']
    return self.compile_results['ok']
 
  def run_with_flags(self, flags, limit):
    return self.run_precompiled(None, None, limit, self.compile_with_flags(flags, 0), 0)

if __name__ == '__main__':
  opentuner.init_logging()
  args = argparser.parse_args()
  if args.logfile:
    fh = logging.FileHandler(args.logfile)
    fh.setLevel(logging.INFO)
    log.addHandler(fh)
    logging.getLogger('opentuner.search.plugin.DisplayPlugin').addHandler(fh)
  LlvmFlagsTuner.main(args)
