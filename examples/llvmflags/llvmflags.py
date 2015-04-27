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

#CLANGXX_PATH = '/Users/yygu/MIT/SuperUROP/build/Debug+Asserts/bin/clang++ -m32'
CLANGXX_PATH = '/data/scratch/yygu/build/Debug+Asserts/bin/clang++'

DEFAULT_PARAM_VALUE = 1
USE_ONLY_INTERNAL = True
USE_ONLY_EXTERNAL = True
PARAMS_INTERNAL_FILE = 'params_internal.txt'
PARAMS_EXTERNAL_FILE = 'params_external.txt'
FLAGS_INTERNAL_FILE = 'flags_internal.txt'
FLAGS_EXTERNAL_FILE = 'flags_external.txt'

OUTPUT_FILE = './tmp.bin'
PREPEND_FLAG = "-mllvm "
APP = 'apps/raytracer.cpp'

argparser = argparse.ArgumentParser(parents=opentuner.argparsers())
argparser.add_argument('source', help='source file to compile')
argparser.add_argument('--compile-template',
                       default='{clang} {source} -o {output} {flag}',
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

class LlvmFlagsTuner(MeasurementInterface):

  def __init__(self, *pargs, **kwargs):
    super(LlvmFlagsTuner, self).__init__(*pargs, **kwargs)
    self.llvm_flags_internal = self.convert_flags(FLAGS_INTERNAL_FILE)
    self.llvm_params_internal = self.convert_params(PARAMS_INTERNAL_FILE)
    self.llvm_flags_external = self.convert_flags(FLAGS_EXTERNAL_FILE)
    self.llvm_params_external = self.convert_params(PARAMS_EXTERNAL_FILE)

    self.llvm_flags = self.extract_working_flags()
    self.llvm_params = self.extract_working_params()

    try:
      os.stat('./tmp')
    except OSError:
      os.mkdir('./tmp')
    self.run_baselines()

  def run_baselines(self):
    log.info("baseline perfs -O0=%.4f -O1=%.4f -O2=%.4f -O3=%.4f",
             *[self.run_with_flags(['-O%d' % i], None).time
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
        params.append((line[:-1], 0, 1000))
    return params

  def check_if_flag_works(self, flag):
    if flag not in ['O0', 'O1', 'O2', 'O3']:
      flag = 'mllvm -' + flag
    cmd = args.compile_template.format(source=args.source, output=args.output,
                                       flag='-'+flag, clang=args.clang)
    compile_result = self.call_program(cmd, limit=args.compile_limit)
    if compile_result['returncode'] != 0:
      log.warning("removing flag %s because it results in compile error", flag)
      return False
    print compile_result
    return True

  def extract_working_flags(self):
    """
    Figure out which gcc flags work (don't cause gcc to barf) by running
    each one.
    """
    all_flags = []
    if USE_ONLY_INTERNAL:
      all_flags = self.llvm_flags_internal
    elif USE_ONLY_EXTERNAL:
      all_flags = self.llvm_flags_external
    else:
      all_flags = self.llvm_flags_internal + self.llvm_flags_external
    working_flags = filter(check_if_flag_works, all_flags)
    return working_flags

  def extract_working_params(self):
    """
    Figure out which clang params work (don't cause clang to barf) by running
    each one.
    """
    all_params = []
    if USE_ONLY_INTERNAL:
      all_params = self.llvm_params_internal
    elif USE_ONLY_EXTERNAL:
      all_params = self.llvm_params_external
    else:
      all_params = self.llvm_params_internal + self.llvm_params_external

    working_params = []
    for param in all_params:
      if self.check_if_flag_works('-{}={}'.format(param, DEFAULT_PARAM_VALUE)):
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
    for param, min, max in self.llvm_params:
      manipulator.add_parameter(
        IntegerParameter(param, min, max))
    return manipulator

  def cfg_to_flags(self, cfg):
    flags = ['-O%d' % cfg['-O']]
    for flag in self.llvm_flags:
      if cfg[flag] == 'on':
        flags.append(PREPEND_FLAG + '-' + flag)

    for param in self.llvm_params:
      flags.append(PREPEND_FLAG + '-{}={}'.format(param, cfg[param]))

    return flags

  def get_tmpdir(self, result_id):
    return './tmp/%d' % result_id

  def cleanup(self, result_id):
    tmp_dir = self.get_tmpdir(result_id)
    shutil.rmtree(tmp_dir)

  def run(self, desired_result, input, limit):
    pass
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
      llvm_cmd += PREPEND_FLAG + '-{}={} '.format(param, cfg[param])
    
    print llvm_cmd

    compile_result = self.call_program(llvm_cmd)
    if compile_result['returncode'] != 0:
      #temp solution
      return Result(state='ERROR', time=float('inf'))

    run_result = self.call_program(OUTPUT_FILE)
    print run_result
    if run_result['returncode'] != 0:
      return Result(state='ERROR', time=float('inf'))
      
    return Result(time=run_result['time'])
    """

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

    if run_result['returncode'] != 0:
      if run_result['timeout']:
        return Result(state='TIMEOUT', time=float('inf'))
      else:
        log.error('program error')
        return Result(state='ERROR', time=float('inf'))

    return Result(time=run_result['time'])

  def compile_with_flags(self, flags, result_id):
    print flags
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
        log.warning("clang timeout")
        return self.compile_results['timeout']
      else:
        log.warning("clang error %s", compile_result['stderr'])
        self.debug_gcc_error(flags)
        return self.compile_results['error']
    return self.compile_results['ok']

if __name__ == '__main__':
  argparser = opentuner.default_argparser()
  args = argparser.parse_args()
  LlvmFlagsTuner.main(args)
