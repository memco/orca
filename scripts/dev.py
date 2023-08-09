import argparse
from datetime import datetime
import glob
import os
import platform
import urllib.request
import shutil
import subprocess
from zipfile import ZipFile

from . import checksum
from .bindgen import bindgen
from .gles_gen import gles_gen
from .log import *
from .utils import pushd, removeall
from .embed_text_files import *

ANGLE_VERSION = "2023-07-05"


def attach_dev_commands(subparsers):
    dev_cmd = subparsers.add_parser("dev", help="Commands for building Orca itself. Must be run from the root of an Orca source checkout.")
    dev_cmd.set_defaults(func=orca_root_only)

    dev_sub = dev_cmd.add_subparsers(required=is_orca_root(), title='commands')

    build_cmd = dev_sub.add_parser("build-runtime", help="Build the Orca runtime from source.")
    build_cmd.add_argument("--release", action="store_true", help="compile Orca in release mode (default is debug)")
    build_cmd.set_defaults(func=dev_shellish(build_runtime))

    clean_cmd = dev_sub.add_parser("clean", help="Delete all build artifacts and start fresh.")
    clean_cmd.set_defaults(func=dev_shellish(clean))

    install_cmd = dev_sub.add_parser("install", help="Install the Orca tools into a system folder.")
    install_cmd.add_argument("--no-confirm", action="store_true", help="don't ask the user for confirmation before installing")
    install_cmd.set_defaults(func=dev_shellish(install))


def is_orca_root():
    try:
        os.stat(".orcaroot")
        return True
    except FileNotFoundError:
        return False


def orca_root_only(args):
    print("The Orca dev commands can only be run from an Orca source checkout.")
    print()
    print("If you want to build Orca yourself, download the source here:")
    print("https://git.handmade.network/hmn/orca")
    exit(1)


def dev_shellish(func):
    return shellish(func) if is_orca_root() else orca_root_only


def build_runtime(args):
    ensure_programs()
    ensure_angle()

    build_platform_layer("lib", args.release)
    build_wasm3(args.release)
    build_orca(args.release)


def clean(args):
    yeet("build")
    yeet("ext/angle")
    yeet("scripts/files")
    yeet("scripts/__pycache__")


def build_platform_layer(target, release):
    print("Building Orca platform layer...")

    os.makedirs("build/bin", exist_ok=True)
    os.makedirs("build/lib", exist_ok=True)

    if target == "lib":
        if platform.system() == "Windows":
            build_platform_layer_lib_win(release)
        elif platform.system() == "Darwin":
            build_platform_layer_lib_mac(release)
        else:
            log_error(f"can't build platform layer for unknown platform '{platform.system()}'")
            exit(1)
    elif target == "test":
        with pushd("examples/test_app"):
            # TODO?
            subprocess.run(["./build.sh"])
    elif target == "clean":
        removeall("bin")
    else:
        log_error(f"unrecognized platform layer target '{target}'")
        exit(1)


def build_platform_layer_lib_win(release):

    embed_text_files("src\\graphics\\glsl_shaders.h", "glsl_", [
        "src\\graphics\\glsl_shaders\\common.glsl",
        "src\\graphics\\glsl_shaders\\blit_vertex.glsl",
        "src\\graphics\\glsl_shaders\\blit_fragment.glsl",
        "src\\graphics\\glsl_shaders\\path_setup.glsl",
        "src\\graphics\\glsl_shaders\\segment_setup.glsl",
        "src\\graphics\\glsl_shaders\\backprop.glsl",
        "src\\graphics\\glsl_shaders\\merge.glsl",
        "src\\graphics\\glsl_shaders\\raster.glsl",
        "src\\graphics\\glsl_shaders\\balance_workgroups.glsl",
    ])

    includes = [
        "/I", "src",
        "/I", "ext",
        "/I", "ext/angle/include",
    ]
    libs = [
        "user32.lib",
        "opengl32.lib",
        "gdi32.lib",
        "shcore.lib",
        "delayimp.lib",
        "dwmapi.lib",
        "comctl32.lib",
        "ole32.lib",
        "shell32.lib",
        "shlwapi.lib",
        "/LIBPATH:ext/angle/lib",
        "libEGL.dll.lib",
        "libGLESv2.dll.lib",
        "/DELAYLOAD:libEGL.dll",
        "/DELAYLOAD:libGLESv2.dll",
    ]

    subprocess.run([
        "cl", "/nologo",
        "/we4013", "/Zi", "/Zc:preprocessor",
        "/DMP_BUILD_DLL",
        "/std:c11", "/experimental:c11atomics",
        *includes,
        "src/orca.c", "/Fo:build/bin/orca.o",
        "/LD", "/link",
        "/MANIFEST:EMBED", "/MANIFESTINPUT:src/app/win32_manifest.xml",
        *libs,
        "/OUT:build/bin/orca.dll",
        "/IMPLIB:build/bin/orca.dll.lib",
    ], check=True)


def build_platform_layer_lib_mac(release):
    sdk_dir = "/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk"

    flags = ["-mmacos-version-min=10.15.4", "-maes"]
    cflags = ["-std=c11"]
    debug_flags = ["-O3"] if release else ["-g", "-DDEBUG", "-DLOG_COMPILE_DEBUG"]
    ldflags = [f"-L{sdk_dir}/usr/lib", f"-F{sdk_dir}/System/Library/Frameworks/"]
    includes = ["-Isrc", "-Isrc/util", "-Isrc/platform", "-Iext", "-Iext/angle/include"]

    # compile metal shader
    subprocess.run([
        "xcrun", "-sdk", "macosx", "metal",
        # TODO: shaderFlagParam
        "-fno-fast-math", "-c",
        "-o", "build/mtl_renderer.air",
        "src/graphics/mtl_renderer.metal",
    ], check=True)
    subprocess.run([
        "xcrun", "-sdk", "macosx", "metallib",
        "-o", "build/bin/mtl_renderer.metallib",
        "build/mtl_renderer.air",
    ], check=True)

    # compile platform layer. We use one compilation unit for all C code, and one
    # compilation unit for all Objective-C code
    subprocess.run([
        "clang",
        *debug_flags, "-c",
        "-o", "build/orca_c.o",
        *cflags, *flags, *includes,
        "src/orca.c"
    ], check=True)
    subprocess.run([
        "clang",
        *debug_flags, "-c",
        "-o", "build/orca_objc.o",
        *flags, *includes,
        "src/orca.m"
    ], check=True)

    # build dynamic library
    subprocess.run([
        "ld",
        *ldflags, "-dylib",
        "-o", "build/bin/liborca.dylib",
        "build/orca_c.o", "build/orca_objc.o",
        "-Lext/angle/bin", "-lc",
        "-framework", "Carbon", "-framework", "Cocoa", "-framework", "Metal", "-framework", "QuartzCore",
        "-weak-lEGL", "-weak-lGLESv2",
    ], check=True)

    # change dependent libs path to @rpath
    subprocess.run([
        "install_name_tool",
        "-change", "./libEGL.dylib", "@rpath/libEGL.dylib",
        "build/bin/liborca.dylib",
    ], check=True)
    subprocess.run([
        "install_name_tool",
        "-change", "./libGLESv2.dylib", "@rpath/libGLESv2.dylib",
        "build/bin/liborca.dylib",
    ], check=True)

    # add executable path to rpath. Client executable can still add its own
    # rpaths if needed, e.g. @executable_path/libs/ etc.
    subprocess.run([
        "install_name_tool",
        "-id", "@rpath/liborca.dylib",
        "build/bin/liborca.dylib",
    ], check=True)


def build_wasm3(release):
    print("Building wasm3...")

    os.makedirs("build/bin", exist_ok=True)
    os.makedirs("build/lib", exist_ok=True)
    os.makedirs("build/obj", exist_ok=True)

    if platform.system() == "Windows":
        build_wasm3_lib_win(release)
    elif platform.system() == "Darwin":
        build_wasm3_lib_mac(release)
    else:
        log_error(f"can't build wasm3 for unknown platform '{platform.system()}'")
        exit(1)


def build_wasm3_lib_win(release):
    for f in glob.iglob("./ext/wasm3/source/*.c"):
        name = os.path.splitext(os.path.basename(f))[0]
        subprocess.run([
            "cl", "/nologo",
            "/Zi", "/Zc:preprocessor", "/c",
            "/O2",
            f"/Fo:build/obj/{name}.obj",
            "/I", "./ext/wasm3/source",
            f,
        ], check=True)
    subprocess.run([
        "lib", "/nologo", "/out:build/bin/wasm3.lib",
        "build/obj/*.obj",
    ], check=True)


def build_wasm3_lib_mac(release):
    includes = ["-Iext/wasm3/source"]
    debug_flags = ["-g", "-O2"]
    flags = [
        *debug_flags,
        "-foptimize-sibling-calls",
        "-Wno-extern-initializer",
        "-Dd_m3VerboseErrorMessages",
    ]

    for f in glob.iglob("ext/wasm3/source/*.c"):
        name = os.path.splitext(os.path.basename(f))[0] + ".o"
        subprocess.run([
            "clang", "-c", *flags, *includes,
            "-o", f"build/obj/{name}",
            f,
        ], check=True)
    subprocess.run(["ar", "-rcs", "build/lib/libwasm3.a", *glob.glob("build/obj/*.o")], check=True)
    subprocess.run(["rm", "-rf", "build/obj"], check=True)


def build_orca(release):
    print("Building Orca runtime...")

    os.makedirs("build/bin", exist_ok=True)
    os.makedirs("build/lib", exist_ok=True)

    if platform.system() == "Windows":
        build_orca_win(release)
    elif platform.system() == "Darwin":
        build_orca_mac(release)
    else:
        log_error(f"can't build Orca for unknown platform '{platform.system()}'")
        exit(1)


def build_orca_win(release):

    gen_all_bindings()

    # compile orca
    includes = [
        "/I", "src",
        "/I", "ext",
        "/I", "ext/angle/include",
        "/I", "ext/wasm3/source",
    ]
    libs = [
        "/LIBPATH:build/bin",
        "orca.dll.lib",
        "wasm3.lib",
    ]

    subprocess.run([
        "cl",
        "/Zi", "/Zc:preprocessor",
        "/std:c11", "/experimental:c11atomics",
        *includes,
        "src/runtime.c",
        "/link", *libs,
        "/out:build/bin/orca_runtime.exe",
    ], check=True)


def build_orca_mac(release):

    includes = [
        "-Isrc",
        "-Iext",
        "-Iext/angle/include",
        "-Iext/wasm3/source"
    ]
    libs = ["-Lbuild/bin", "-Lbuild/lib", "-lorca", "-lwasm3"]
    debug_flags = ["-O2"] if release else ["-g", "-DLOG_COMPILE_DEBUG"]
    flags = [
        *debug_flags,
        "-mmacos-version-min=10.15.4",
        "-maes",
    ]

    gen_all_bindings()

    # compile orca
    subprocess.run([
        "clang", *flags, *includes, *libs,
        "-o", "build/bin/orca_runtime",
        "src/runtime.c",
    ], check=True)

    # fix libs imports
    subprocess.run([
        "install_name_tool",
        "-change", "build/bin/liborca.dylib", "@rpath/liborca.dylib",
        "build/bin/orca_runtime",
    ], check=True)
    subprocess.run([
        "install_name_tool",
        "-add_rpath", "@executable_path/",
        "build/bin/orca_runtime",
    ], check=True)


def gen_all_bindings():
    gles_gen("ext/gl.xml",
        "src/wasmbind/gles_api.json",
        "src/graphics/orca_gl31.h"
    )

    bindgen("gles", "src/wasmbind/gles_api.json",
        wasm3_bindings="src/wasmbind/gles_api_bind_gen.c",
    )

    bindgen("core", "src/wasmbind/core_api.json",
        wasm3_bindings="src/wasmbind/core_api_bind_gen.c",
    )

    bindgen("surface", "src/wasmbind/surface_api.json",
        guest_stubs="src/graphics/orca_surface_stubs.c",
        guest_include="graphics/graphics.h",
        wasm3_bindings="src/wasmbind/surface_api_bind_gen.c",
    )

    bindgen("clock", "src/wasmbind/clock_api.json",
        guest_include="platform/platform_clock.h",
        wasm3_bindings="src/wasmbind/clock_api_bind_gen.c",
    )
    bindgen("io", "src/wasmbind/io_api.json",
        guest_stubs="src/platform/orca_io_stubs.c",
        wasm3_bindings="src/wasmbind/io_api_bind_gen.c",
    )


def ensure_programs():
    if platform.system() == "Windows":
        try:
            subprocess.run(["cl"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except FileNotFoundError:
            msg = log_error("MSVC was not found on your system.")
            msg.more("If you have already installed Visual Studio, make sure you are running in a")
            msg.more("Visual Studio command prompt or you have run vcvarsall.bat. Otherwise, download")
            msg.more("and install Visual Studio: https://visualstudio.microsoft.com/")
            exit(1)

    try:
        subprocess.run(["clang", "-v"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        msg = log_error("clang was not found on your system.")
        if platform.system() == "Windows":
            msg.more("We recommend installing clang via the Visual Studio installer.")
        elif platform.system() == "Darwin":
            msg.more("Run the following to install it:")
            msg.more()
            msg.more("  brew install llvm")
            msg.more()
        exit(1)
    # TODO(ben): Check for xcode command line tools


def ensure_angle():
    if not verify_angle():
        download_angle()
        print("Verifying ANGLE download...")
        if not verify_angle():
            log_error("automatic ANGLE download failed")
            exit(1)


def verify_angle():
    checkfiles = None
    if platform.system() == "Windows":
        checkfiles = [
            "ext/angle/bin/libEGL.dll",
            "ext/angle/lib/libEGL.dll.lib",
            "ext/angle/bin/libGLESv2.dll",
            "ext/angle/lib/libGLESv2.dll.lib",
        ]
    elif platform.system() == "Darwin":
        checkfiles = [
            "ext/angle/bin/libEGL.dylib",
            "ext/angle/bin/libGLESv2.dylib",
        ]

    if checkfiles is None:
        log_warning("could not verify if the correct version of ANGLE is present")
        return False

    ok = True
    for file in checkfiles:
        if not os.path.isfile(file):
            ok = False
            continue
        if not checksum.checkfile(file):
            ok = False
            continue

    return ok


def download_angle():
    print("Downloading ANGLE...")
    if platform.system() == "Windows":
        build = "windows-2019"
    elif platform.system() == "Darwin":
        build = "macos-jank"
    else:
        log_error(f"could not automatically download ANGLE for unknown platform {platform.system()}")
        return

    os.makedirs("scripts/files", exist_ok=True)
    filename = f"angle-{build}-{ANGLE_VERSION}.zip"
    filepath = f"scripts/files/{filename}"
    url = f"https://github.com/HandmadeNetwork/build-angle/releases/download/{ANGLE_VERSION}/{filename}"
    with urllib.request.urlopen(url) as response:
        with open(filepath, "wb") as out:
            shutil.copyfileobj(response, out)

    if not checksum.checkfile(filepath):
        log_error(f"ANGLE download did not match checksum")
        exit(1)

    print("Extracting ANGLE...")
    with ZipFile(filepath, "r") as anglezip:
        anglezip.extractall(path="scripts/files")

    shutil.copytree(f"scripts/files/angle/", "ext/angle", dirs_exist_ok=True)

def yeet(path):
    os.makedirs(path, exist_ok=True)
    shutil.rmtree(path)


def install(args):
    if platform.system() == "Windows":
        dest = os.path.join(os.getenv("LOCALAPPDATA"), "orca")
    else:
        dest = os.path.expanduser(os.path.join("~", ".orca"))

    if not args.no_confirm:
        print("The Orca command-line tools will be installed to:")
        print(dest)
        print()
        while True:
            answer = input("Proceed with the installation? (y/n) >")
            if answer.lower() in ["y", "yes"]:
                break
            elif answer.lower() in ["n", "no"]:
                return
            else:
                print("Please enter \"yes\" or \"no\" and press return.")

    bin_dir = os.path.join(dest, "bin")
    yeet(bin_dir)
    shutil.copytree("scripts", os.path.join(bin_dir, "sys_scripts"))
    shutil.copy("orca", bin_dir)
    if platform.system() == "Windows":
        shutil.copy("orca.bat", bin_dir)

    # TODO: Customize these instructions for Windows
    print()
    if platform.system() == "Windows":
        print("The Orca tools have been installed. Make sure the Orca tools are on your PATH by")
        print("adding the following path to your system PATH variable:")
        print()
        print(bin_dir)
        print()
        print("You can do this in the Windows settings by searching for \"environment variables\".")
    else:
        print("The Orca tools have been installed. Make sure the Orca tools are on your PATH by")
        print("adding the following to your shell config:")
        print()
        print(f"export PATH=\"{bin_dir}:$PATH\"")
    print()
