#!/usr/bin/env python

FLAGS_FILE = 'opt_flags2.txt'
EXPORT_FLAGS_FILE = 'flags_external.txt'
EXPORT_PARAMS_FILE = 'params_external.txt'

params = []
flags = []

f = open(FLAGS_FILE, 'rb')
for line in f:
	splits = line.split()
	param = splits[0]
	if param[0] != '-':
		continue
	if "=" in param:
		# it's a param
		splits2 = param.split('=')
		if 'int' in splits2[-1]:
			params.append(splits2[0][1:])
	else:
		# it's a flag
		flags.append(param[1:])
f.close()

f = open(EXPORT_FLAGS_FILE, 'w')
for flag in flags:
	f.write(flag+'\n')
f.close()


f = open(EXPORT_PARAMS_FILE, 'w')
for param in params:
	f.write(param+'\n')
f.close()