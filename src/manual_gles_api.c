
void glShaderSource_stub(void* userdata, bb_module_instance* module, const bb_val* params, bb_val* returns)
{
	i32 shader = params[0].i32_val;
	i32 count = params[1].i32_val;
	i32 stringArrayOffset = params[2].i32_val;
	i32 lengthArrayOffset = params[3].i32_val;

	const int* lengthArray = lengthArrayOffset ? (int*)(bb_module_instance_mem(module, lengthArrayOffset, count * sizeof(int))) : 0;
	const int* stringOffsetArray = (int*)(bb_module_instance_mem(module, stringArrayOffset, count * sizeof(int)));
	const char** stringArray = (const char**)mem_arena_alloc_array(mem_scratch(), char*, count);
	for(int i=0; i<count; i++)
	{
		stringArray[i] = (char*)bb_module_instance_mem(module, stringOffsetArray[i], lengthArray ? lengthArray[i] : (size_t)-1);
	}

	glShaderSource(shader, count, stringArray, lengthArray);
}

int manual_link_gles_api(bb_import_package* package)
{
	bb_valtype params[] = {BB_VALTYPE_I32, BB_VALTYPE_I32, BB_VALTYPE_I32, BB_VALTYPE_I32};
	size_t num_params = 4;
	bb_error err = bb_import_package_add_function(package, glShaderSource_stub, "glShaderSource", params, num_params, NULL, 0, NULL);
	if(err != BB_ERROR_OK) { log_error("error: %s\n", bb_error_str(err)); return(-1); }

	return(0);
}
