#include"canvas_api_bind_gen.c"

typedef struct wasm_str8
{
	i64 len;
	i32 offset;
} wasm_str8;

const void* mg_text_outlines_stub(void* userdata, bb_module_instance* module, const bb_val* params, bb_val* returns)
{
	wasm_str8 wasmStr = *(wasm_str8*)bb_module_instance_mem(module, params[0].i32_val, sizeof(wasm_str8));

	str8 str = {.len = wasmStr.len,
	            .ptr = (char*)bb_module_instance_mem(module, wasmStr.offset, wasmStr.len)};

	if(str.ptr)
	{
		mg_text_outlines(str);
	}
	return(0);
}
