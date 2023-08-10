#!/usr/bin/env python3

from argparse import ArgumentParser
import json


parser = ArgumentParser(prog='bindgen.py')
parser.add_argument('api')
parser.add_argument('spec')
parser.add_argument('-g', '--guest-stubs')
parser.add_argument('--guest-include')
parser.add_argument('--wasm3-bindings')

args = parser.parse_args()

apiName = args.api
spec = args.spec
guest_stubs_path = args.guest_stubs
if guest_stubs_path == None:
	guest_stubs_path = 'bindgen_' + apiName + '_guest_stubs.c'

wasm3_bindings_path = args.wasm3_bindings
if wasm3_bindings_path == None:
	wasm3_bindings_path = 'bindgen_' + apiName + '_wasm3_bindings.c'

host_bindings = open(wasm3_bindings_path, 'w')
guest_bindings = None

specFile = open(spec, 'r')
data = json.load(specFile)

def needs_arg_ptr_stub(decl):
	res = (decl['ret']['tag'] == 'S')
	for arg in decl['args']:
		if arg['type']['tag'] == 'S':
			res = True
	return(res)

for decl in data:
	if needs_arg_ptr_stub(decl):
		guest_bindings = open(guest_stubs_path, 'w')
		if args.guest_include != None:
			s = '#include"' + args.guest_include + '"\n\n'
			print(s, file=guest_bindings)
		break

for decl in data:

	name = decl['name']
	cname = decl.get('cname', name)

	if needs_arg_ptr_stub(decl):
		argPtrStubName = name + '_argptr_stub'
		# pointer arg stub declaration
		s = ''
		if decl['ret']['tag'] == 'S':
			s += 'void'
		else:
			s += decl['ret']['name']

		s += ' ORCA_IMPORT(' + argPtrStubName + ') ('

		if decl['ret']['tag'] == 'S':
			s += decl['ret']['name'] + '* __retArg'
			if len(decl['args']) > 0:
				s += ', '

		for i, arg in enumerate(decl['args']):
			s += arg['type']['name']
			if arg['type']['tag'] == 'S':
				s += '*'
			s += ' ' + arg['name']
			if i+1 < len(decl['args']):
				s += ', '
		s += ');\n\n'

		# forward function to pointer arg stub declaration
		s += decl['ret']['name'] + ' ' + name + '('
		for i, arg in enumerate(decl['args']):
			s += arg['type']['name'] + ' ' + arg['name']
			if i+1 < len(decl['args']):
				s += ', '
		s += ')\n'
		s += '{\n'
		s += '\t'
		if decl['ret']['tag'] == 'S':
			s += decl['ret']['name'] + ' __ret;\n\t'
		elif decl['ret']['tag'] != 'v':
			s += decl['ret']['name']
			s += ' __ret = '
		s += argPtrStubName + '('

		if decl['ret']['tag'] == 'S':
			s += '&__ret'
			if len(decl['args']) > 0:
				s += ', '

		for i, arg in enumerate(decl['args']):
			if arg['type']['tag'] == 'S':
				s += '&'

			s += arg['name']
			if i+1 < len(decl['args']):
				s += ', '
		s += ');\n'
		if decl['ret']['tag'] != 'v':
			s += '\treturn(__ret);\n'
		s += '}\n\n'

		print(s, file=guest_bindings)

	# host-side stub
	s = 'void ' + cname + '_stub(void* userdata, bb_module_instance* module, const bb_val* params, bb_val* returns)'

	gen_stub = decl.get('gen_stub', True)
	if gen_stub == False:
		s += ';\n\n'
	else:
		s += '\n{\n\t'
		retTag = decl['ret']['tag']

		firstArgIndex = 0
		if retTag == 'i':
			s += 'returns[0].i32_val = '
		elif retTag == 'I':
			s += 'returns[0].i64_val = '
		elif retTag == 'f':
			s += 'returns[0].f32_val = '
		elif retTag == 'F':
			s += 'returns[0].f64_val = '
		elif retTag == 'S':
			retTypeName = decl['ret']['name']
			retTypeCName = decl['ret'].get('cname', retTypeName)
			s += '*(' + retTypeCName + '*)(bb_module_instance_mem(module, params[0].i32_val, sizeof(' + retTypeCName + '))) = '
			firstArgIndex = 1

		s += cname + '('

		for i, arg in enumerate(decl['args']):
			typeName = arg['type']['name']
			typeCName = arg['type'].get('cname', typeName)
			argTag = arg['type']['tag']
			if argTag == 'i':
				s += 'params[' + str(firstArgIndex + i) + '].i32_val'
			elif argTag == 'I':
				s += 'params[' + str(firstArgIndex + i) + '].i64_val'
			elif argTag == 'f':
				s += 'params[' + str(firstArgIndex + i) + '].f32_val'
			elif argTag == 'F':
				s += 'params[' + str(firstArgIndex + i) + '].f64_val'
			elif argTag == 'p':
				s += 'bb_module_instance_mem(module, params[' + str(firstArgIndex + i) + '].i32_val, sizeof(1))'
			elif argTag == 'S':
				s += '*(' + typeCName + '*)bb_module_instance_mem(module, params[' + str(firstArgIndex + i) + '].i32_val, sizeof(' + typeCName + '))'
			else:
				print('unrecognized type ' + typeCName + ' in procedure signature\n')
				break

			if i+1 < len(decl['args']):
				s += ', '

		s += ');\n}\n'

	print(s, file=host_bindings)

# link function
s = 'int bindgen_link_' + apiName + '_api(bb_import_package* package)\n{\n'

def translateTag(tag):
	if tag == 'i' or tag == 'p':
		return 'BB_VALTYPE_I32'
	elif tag == 'I':
		return 'BB_VALTYPE_I64'
	elif tag == 'f':
		return 'BB_VALTYPE_F32'
	elif tag == 'F':
		return 'BB_VALTYPE_F64'
	elif tag == 'v':
		return ''
	print('translateTag: unhandled tag "' + tag + '" with type ')
	print(type(tag))
	print('\n')
	return ''

for decl in data:
	name = decl['name']
	cname = decl.get('cname', name)

	if needs_arg_ptr_stub(decl):
		name = name + '_argptr_stub'

	retTag = decl['ret']['tag']

	retType = ''
	numReturns = 0
	paramTypes = []
	numParams = 0
	if retTag == 'S':
		paramTypes.append('BB_VALTYPE_I32')
		numParams += 1
	elif retTag != 'v': #no returns
		retType = translateTag(retTag)
		numReturns = 1
		
	for arg in decl['args']:
		tag = arg['type']['tag']
		if tag == 'p' or tag == 'S':
			tag = 'i'
		paramTypes.append(translateTag(tag))
		numParams += 1

	# dummy values
	if numReturns == 0:
		retType = 'BB_VALTYPE_I32'

	if numParams == 0:
		paramTypes.append('BB_VALTYPE_I32')

	s += '\t{\n'
	s += '\t\tbb_valtype params[] = {' + ', '.join(paramTypes) + '};\n'
	s += '\t\tsize_t num_params = ' + str(len(paramTypes)) + ';\n'
	s += '\t\tbb_valtype return_type = ' + retType + ';\n'
	s += '\t\tsize_t num_returns = ' + str(numReturns) + ';\n'

	s += '\t\tbb_error err = bb_import_package_add_function(package, ' + cname + '_stub, "' + name + '", params, num_params, &return_type, num_returns, NULL);\n'
	s += '\t\tif(err != BB_ERROR_OK) { log_error("error: %s\\n", bb_error_str(err)); return(-1); }\n'
	s += '\t}\n'


s += '\treturn(0);\n}\n'

print(s, file=host_bindings)
