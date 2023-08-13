/************************************************************//**
*
*	@file: win32_memory.c
*	@author: Martin Fouilleul
*	@date: 17/12/2022
*	@revision:
*
*****************************************************************/
#define WIN32_LEAN_AND_MEAN
#include<windows.h>
#include"platform_memory.h"

void* mem_base_reserve_win32(mem_base_allocator* context, u64 size)
{
	void* result = VirtualAlloc(0, size, MEM_RESERVE, PAGE_READWRITE);
	return(result);
}

void mem_base_commit_win32(mem_base_allocator* context, void* ptr, u64 size)
{
	VirtualAlloc(ptr, size, MEM_COMMIT, PAGE_READWRITE);
}

void mem_base_release_win32(mem_base_allocator* context, void* ptr, u64 size)
{
	VirtualFree(ptr, size, MEM_RELEASE);
}

void mem_base_decommit_win32(mem_base_allocator* context, void* ptr, u64 size)
{
	VirtualFree(ptr, size, MEM_DECOMMIT);
}

mem_base_allocator* mem_base_allocator_default()
{
	static mem_base_allocator base = {0};
	if(base.reserve == 0)
	{
		base.reserve = mem_base_reserve_win32;
		base.commit = mem_base_commit_win32;
		base.decommit = mem_base_decommit_win32;
		base.release = mem_base_release_win32;
	}
	return(&base);
}