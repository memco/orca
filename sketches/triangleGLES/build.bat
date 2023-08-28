
set INCLUDES=/I ..\..\src /I ..\..\src\util /I ..\..\src\platform /I ../../ext /I ../../ext/angle/include

if not exist "bin" mkdir bin
cl /we4013 /Zi /Zc:preprocessor /std:c11 /experimental:c11atomics %INCLUDES% main.c /link /LIBPATH:../../build/bin orca.dll.lib /out:bin/example_gles_triangle.exe
copy ..\..\build\bin\orca.dll bin
copy ..\..\ext\angle\bin\libEGL.dll bin
copy ..\..\ext\angle\bin\libGLESv2.dll bin
