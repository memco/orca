/************************************************************//**
*
*	@file: wasm_main.cpp
*	@author: Martin Fouilleul
*	@date: 14/08/2022
*	@revision:
*
*****************************************************************/

#include"keys.h"
#include"graphics.h"

#include"orca.h"

#define M_PI 3.14159265358979323846

extern float cosf(float x);
extern float sinf(float x);

const mg_color paddleColor = {1, 0, 0, 1};
mp_rect paddle = {200, 40, 200, 40};

const mg_color ballColor = {1, 1, 0, 1};
mp_rect ball = {200, 200, 60, 60};

vec2 velocity = {10, 10};

vec2 frameSize = {100, 100};

bool leftDown = false;
bool rightDown = false;

mg_canvas canvas;
mg_surface surface;
mg_image ballImage;
mg_image paddleImage;
mg_font pongFont;

mg_surface mg_surface_main(void);

ORCA_EXPORT void OnInit(void)
{
	//TODO create surface for main window
	surface = mg_surface_main();
	canvas = mg_canvas_create();

	log_info("try allocating\n");

	char* foo = malloc(1024);
	free(foo);

	log_info("allocated and freed 1024 bytes\n");

	//NOTE: load ball texture
	{
		file_handle file = file_open(STR8("/ball.png"), FILE_ACCESS_READ, 0);
		if(file_last_error(file) != IO_OK)
		{
			log_error("Couldn't open file ball.png\n");
		}
		u64 size = file_size(file);
		char* buffer = mem_arena_alloc(mem_scratch(), size);
		file_read(file, size, buffer);
		file_close(file);
		ballImage = mg_image_create_from_data(surface, str8_from_buffer(size, buffer), false);
	}

	//NOTE: load paddle texture
	{
		file_handle file = file_open(STR8("/wall.png"), FILE_ACCESS_READ, 0);
		if(file_last_error(file) != IO_OK)
		{
			log_error("Couldn't open file wall.png\n");
		}
		u64 size = file_size(file);
		char* buffer = mem_arena_alloc(mem_scratch(), size);
		file_read(file, size, buffer);
		file_close(file);
		paddleImage = mg_image_create_from_data(surface, str8_from_buffer(size, buffer), false);
	}

	//NOTE: load paddle texture
	{
		file_handle file = file_open(STR8("/Literata-SemiBoldItalic.ttf"), FILE_ACCESS_READ, 0);
		if(file_last_error(file) != IO_OK)
		{
			log_error("Couldn't open file Literata-SemiBoldItalic.ttf\n");
		}
		u64 size = file_size(file);
		char* buffer = mem_arena_alloc(mem_scratch(), size);
		file_read(file, size, buffer);
		file_close(file);
		unicode_range ranges[5] = {UNICODE_RANGE_BASIC_LATIN,
	                           UNICODE_RANGE_C1_CONTROLS_AND_LATIN_1_SUPPLEMENT,
	                           UNICODE_RANGE_LATIN_EXTENDED_A,
	                           UNICODE_RANGE_LATIN_EXTENDED_B,
	                           UNICODE_RANGE_SPECIALS};
		// NOTE(ben): Weird that images are "create from data" but fonts are "create from memory"
		// TODO: Decide whether we're using strings or explicit pointer + length
		pongFont = mg_font_create_from_memory(size, (byte*)buffer, 5, ranges);
	}

	mem_arena_clear(mem_scratch());
}

ORCA_EXPORT void OnFrameResize(u32 width, u32 height)
{
	log_info("frame resize %u, %u", width, height);
	frameSize.x = width;
	frameSize.y = height;
}

ORCA_EXPORT void OnMouseDown(int button)
{
	log_info("mouse down!");
}

ORCA_EXPORT void OnKeyDown(int key)
{
	if(key == KEY_SPACE)
	{
		log_error("(this is just for testing errors)");
		return;
	}
	if(key == KEY_ENTER)
	{
		log_warning("(this is just for testing warning)");
		return;
	}

	log_info("key down: %i", key);
	if(key == KEY_LEFT)
	{
		leftDown = true;
	}
	if(key == KEY_RIGHT)
	{
		rightDown = true;
	}
}

ORCA_EXPORT void OnKeyUp(int key)
{
	if(key == KEY_ENTER || key == KEY_SPACE)
	{
		return;
	}

	log_info("key up: %i", key);
	if(key == KEY_LEFT)
	{
		leftDown = false;
	}
	if(key == KEY_RIGHT)
	{
		rightDown = false;
	}
}

ORCA_EXPORT void OnFrameRefresh(void)
{
	f32 aspect = frameSize.x/frameSize.y;

    if(leftDown)
    {
		paddle.x -= 10;
    }
    else if(rightDown)
    {
		paddle.x += 10;
    }
    paddle.x = Clamp(paddle.x, 0, frameSize.x - paddle.w);

    ball.x += velocity.x;
    ball.y += velocity.y;
    ball.x = Clamp(ball.x, 0, frameSize.x - ball.w);
    ball.y = Clamp(ball.y, 0, frameSize.y - ball.h);

    if(ball.x + ball.w >= frameSize.x)
    {
		velocity.x = -10;
    }
    if(ball.x <= 0)
    {
		velocity.x = +10;
    }
    if(ball.y + ball.h >= frameSize.y)
    {
		velocity.y = -10;
    }

    if(ball.y <= paddle.y + paddle.h
       && ball.x+ball.w >= paddle.x
       && ball.x <= paddle.x + paddle.w
       && velocity.y < 0)
    {
		velocity.y *= -1;
		ball.y = paddle.y + paddle.h;

		log_info("PONG!");
    }

    if(ball.y <= 0)
    {
		ball.x = frameSize.x/2. - ball.w;
		ball.y = frameSize.y/2. - ball.h;
	}

	mg_canvas_set_current(canvas);

	mg_set_color_rgba(0, 1, 1, 1);
	mg_clear();

	mg_mat2x3 transform = {1, 0, 0,
	                       0, -1, frameSize.y};

	mg_matrix_push(transform);

	mg_image_draw(paddleImage, paddle);
	/*
	mg_set_color(paddleColor);
	mg_rectangle_fill(paddle.x, paddle.y, paddle.w, paddle.h);
	*/

	mg_image_draw(ballImage, ball);
	/*
	mg_set_color(ballColor);
	mg_circle_fill(ball.x+ball.w/2, ball.y + ball.w/2, ball.w/2.);
	*/

    mg_matrix_pop();

	mg_set_color_rgba(0, 0, 0, 1);
	mg_set_font(pongFont);
	mg_set_font_size(14);
	mg_move_to(10, 20);

	str8 text = str8_pushf(mem_scratch(),
		"wahoo I'm did a text. ball is at x = %f, y = %f",
		ball.x, ball.y
	);
	mg_text_outlines(text);
	mg_fill();

    mg_surface_prepare(surface);
    mg_render(surface, canvas);
    mg_surface_present(surface);
}
