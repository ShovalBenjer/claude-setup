/* Reads GL_VENDOR / GL_RENDERER / GL_VERSION through a surfaceless EGL context.
 *
 * Why this exists rather than `glxinfo -B`: mesa-utils is not installed on this box
 * and installing it needs a sudo password the agent does not have. This has no build
 * dependency beyond gcc and libdl, because every EGL and GL type and constant it needs
 * is declared here and both libraries are opened with dlopen at runtime.
 *
 * The renderer string is the only honest answer to "is the GPU being used". A GL
 * VERSION alone is misleading in the other direction: llvmpipe advertises 4.5 while
 * mesa's d3d12 driver caps at 4.1, so the software path reports the HIGHER number.
 *
 *     gcc -O0 -o glprobe glprobe.c -ldl
 *     ./glprobe                      # whatever mesa picks by default
 *     GALLIUM_DRIVER=d3d12 ./glprobe # force the WSL hardware path
 *     LIBGL_ALWAYS_SOFTWARE=1 ./glprobe   # the control: known-software output
 */
#include <stdio.h>
#include <stdlib.h>
#include <dlfcn.h>

typedef void *EGLDisplay;
typedef void *EGLConfig;
typedef void *EGLContext;
typedef void *EGLSurface;
typedef unsigned int EGLenum;
typedef int EGLint;
typedef unsigned int EGLBoolean;

#define EGL_NONE 0x3038
#define EGL_OPENGL_API 0x30A2
#define EGL_SURFACE_TYPE 0x3033
#define EGL_PBUFFER_BIT 0x0001
#define EGL_RENDERABLE_TYPE 0x3040
#define EGL_OPENGL_BIT 0x0008
#define EGL_PLATFORM_SURFACELESS_MESA 0x31DD

#define GL_VENDOR 0x1F00
#define GL_RENDERER 0x1F01
#define GL_VERSION 0x1F02

int main(void) {
    void *egl = dlopen("libEGL.so.1", RTLD_LAZY);
    if (!egl) { fprintf(stderr, "no libEGL.so.1: %s\n", dlerror()); return 2; }

    EGLDisplay (*getPlatformDisplay)(EGLenum, void *, const EGLint *) =
        dlsym(egl, "eglGetPlatformDisplay");
    EGLDisplay (*getDisplay)(void *) = dlsym(egl, "eglGetDisplay");
    EGLBoolean (*initialize)(EGLDisplay, EGLint *, EGLint *) = dlsym(egl, "eglInitialize");
    EGLBoolean (*bindAPI)(EGLenum) = dlsym(egl, "eglBindAPI");
    EGLBoolean (*chooseConfig)(EGLDisplay, const EGLint *, EGLConfig *, EGLint, EGLint *) =
        dlsym(egl, "eglChooseConfig");
    EGLContext (*createContext)(EGLDisplay, EGLConfig, EGLContext, const EGLint *) =
        dlsym(egl, "eglCreateContext");
    EGLBoolean (*makeCurrent)(EGLDisplay, EGLSurface, EGLSurface, EGLContext) =
        dlsym(egl, "eglMakeCurrent");
    void *(*getProcAddress)(const char *) = dlsym(egl, "eglGetProcAddress");
    EGLint (*getError)(void) = dlsym(egl, "eglGetError");

    if (!initialize || !chooseConfig || !createContext || !makeCurrent || !getProcAddress) {
        fprintf(stderr, "libEGL is missing entry points\n");
        return 2;
    }

    /* Surfaceless, so this runs with no compositor and no DISPLAY, which means it
     * can also be run from a hook or from CI where there is no window to attach to. */
    EGLDisplay dpy = 0;
    if (getPlatformDisplay) dpy = getPlatformDisplay(EGL_PLATFORM_SURFACELESS_MESA, NULL, NULL);
    if (!dpy && getDisplay) dpy = getDisplay(NULL);
    if (!dpy) { fprintf(stderr, "no EGL display\n"); return 3; }

    EGLint major = 0, minor = 0;
    if (!initialize(dpy, &major, &minor)) {
        fprintf(stderr, "eglInitialize failed, egl error 0x%x\n", getError ? getError() : 0);
        return 3;
    }
    printf("EGL_VERSION=%d.%d\n", major, minor);

    if (bindAPI) bindAPI(EGL_OPENGL_API);

    EGLint attribs[] = { EGL_SURFACE_TYPE, EGL_PBUFFER_BIT,
                         EGL_RENDERABLE_TYPE, EGL_OPENGL_BIT,
                         EGL_NONE };
    EGLConfig cfg;
    EGLint n = 0;
    if (!chooseConfig(dpy, attribs, &cfg, 1, &n) || n < 1) {
        fprintf(stderr, "no EGL config, egl error 0x%x\n", getError ? getError() : 0);
        return 4;
    }

    EGLContext ctx = createContext(dpy, cfg, NULL, NULL);
    if (!ctx) { fprintf(stderr, "no EGL context, egl error 0x%x\n", getError ? getError() : 0); return 5; }

    /* Needs EGL_KHR_surfaceless_context, which mesa has had for a decade. */
    if (!makeCurrent(dpy, NULL, NULL, ctx)) {
        fprintf(stderr, "eglMakeCurrent failed, egl error 0x%x\n", getError ? getError() : 0);
        return 6;
    }

    const unsigned char *(*glGetString)(unsigned int) =
        (const unsigned char *(*)(unsigned int))getProcAddress("glGetString");
    if (!glGetString) {
        void *gl = dlopen("libGL.so.1", RTLD_LAZY);
        if (gl) glGetString = dlsym(gl, "glGetString");
    }
    if (!glGetString) { fprintf(stderr, "no glGetString\n"); return 7; }

    printf("GL_VENDOR=%s\n", glGetString(GL_VENDOR));
    printf("GL_RENDERER=%s\n", glGetString(GL_RENDERER));
    printf("GL_VERSION=%s\n", glGetString(GL_VERSION));
    return 0;
}
