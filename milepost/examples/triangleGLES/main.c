/************************************************************//**
*
*	@file: main.cpp
*	@author: Martin Fouilleul
*	@date: 30/07/2022
*	@revision:
*
*****************************************************************/
#include<stdio.h>
#include<stdlib.h>
#include<string.h>

#define _USE_MATH_DEFINES //NOTE: necessary for MSVC
#include<math.h>

#define MG_INCLUDE_GL_API 1
#include"milepost.h"

unsigned int program;

const char* vshaderSource =
	//"#version 320 es\n"
	"attribute vec4 vPosition;\n"
	"uniform mat4 transform;\n"
	"void main()\n"
	"{\n"
	"   gl_Position = transform*vPosition;\n"
	"}\n";

const char* fshaderSource =
	//"#version 320 es\n"
	"precision mediump float;\n"
	"void main()\n"
	"{\n"
	"    gl_FragColor = vec4(1.0, 0.0, 0.0, 1.0);\n"
	"}\n";

void compile_shader(GLuint shader, const char* source)
{
	glShaderSource(shader, 1, &source, 0);
	glCompileShader(shader);

	int err = glGetError();
	if(err)
	{
		printf("gl error: %i\n", err);
	}

	int status = 0;
	glGetShaderiv(shader, GL_COMPILE_STATUS, &status);
	if(!status)
	{
		char buffer[256];
		int size = 0;
		glGetShaderInfoLog(shader, 256, &size, buffer);
		printf("shader error: %.*s\n", size, buffer);
	}
}

int main()
{
	mp_init();

	mp_rect rect = {.x = 100, .y = 100, .w = 800, .h = 600};
	mp_window window = mp_window_create(rect, "test", 0);

	//NOTE: create surface
	mg_surface surface = mg_surface_create_for_window(window, MG_GLES);
	mg_surface_prepare(surface);

	//NOTE: init shader and gl state
	GLuint vao;
	glGenVertexArrays(1, &vao);
	glBindVertexArray(vao);

	GLuint vertexBuffer;
	glGenBuffers(1, &vertexBuffer);

	GLfloat vertices[] = {
		-0.866/2, -0.5/2, 0, 0.866/2, -0.5/2, 0, 0, 0.5, 0};

	glBindBuffer(GL_ARRAY_BUFFER, vertexBuffer);
	glBufferData(GL_ARRAY_BUFFER, sizeof(vertices), vertices, GL_STATIC_DRAW);


	unsigned int vshader = glCreateShader(GL_VERTEX_SHADER);
	unsigned int fshader = glCreateShader(GL_FRAGMENT_SHADER);
	program = glCreateProgram();

	compile_shader(vshader, vshaderSource);
	compile_shader(fshader, fshaderSource);

	glAttachShader(program, vshader);
	glAttachShader(program, fshader);
	glLinkProgram(program);

	int status = 0;
	glGetProgramiv(program, GL_LINK_STATUS, &status);
	if(!status)
	{
		char buffer[256];
		int size = 0;
		glGetProgramInfoLog(program, 256, &size, buffer);
		printf("link error: %.*s\n", size, buffer);
 	}

	glUseProgram(program);

	mp_window_bring_to_front(window);
//	mp_window_focus(window);

	while(!mp_should_quit())
	{
		mp_pump_events(0);
		mp_event* event = 0;
		while((event = mp_next_event(mem_scratch())) != 0)
		{
			switch(event->type)
			{
				case MP_EVENT_WINDOW_CLOSE:
				{
					mp_request_quit();
				} break;

				default:
					break;
			}
		}

//		mg_surface_prepare(surface);

		glClearColor(0.3, 0.3, 1, 1);
		glClear(GL_COLOR_BUFFER_BIT);

 		static float alpha = 0;
		//f32 aspect = frameSize.x/frameSize.y;
		f32 aspect = 800/(f32)600;

   		GLfloat matrix[] = {cosf(alpha)/aspect, sinf(alpha), 0, 0,
    	                  		-sinf(alpha)/aspect, cosf(alpha), 0, 0,
    	                  		0, 0, 1, 0,
    	                  		0, 0, 0, 1};

   		alpha += 2*M_PI/120;

   		glUniformMatrix4fv(0, 1, false, matrix);


		glBindBuffer(GL_ARRAY_BUFFER, vertexBuffer);
   		glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 0, 0);
   		glEnableVertexAttribArray(0);

   		glDrawArrays(GL_TRIANGLES, 0, 3);

		mg_surface_present(surface);

		mem_arena_clear(mem_scratch());
	}

	mg_surface_destroy(surface);
	mp_window_destroy(window);
	mp_terminate();

	return(0);
}