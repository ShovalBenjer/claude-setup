#!/usr/bin/env bash
# Measures whether WSLg is actually using the GPU, rather than reporting that a GPU exists.
#
# The distinction matters because every cheap check passes on this machine while the
# rendering is done on the CPU. /dev/dxg exists, /usr/lib/wsl/lib is populated and on the
# loader path, the Windows adapter is healthy, mesa ships d3d12_dri.so, and the default
# GL context is still llvmpipe. Only the renderer string separates those two worlds, so
# that is what this script's verdict is keyed on.
#
# Two traps this avoids:
#   1. GL_VERSION is not evidence. llvmpipe advertises 4.5 and mesa's d3d12 driver caps
#      at 4.1, so the software path reports the higher number.
#   2. A single reading is not evidence either. Section 4 runs a forced-software control
#      alongside the default, so "default equals control" is a measured claim.
#
# WHAT THIS DOES NOT SAY, corrected 2026-08-04 the same hour it was written. The first
# version failed the run whenever the default path was software and told the reader to
# force GALLIUM_DRIVER=d3d12. Then glxgears was run on both paths and inverted it:
#
#   glxgears, llvmpipe                206 and 269 FPS
#   glxgears, GALLIUM_DRIVER=d3d12     10 and  29 FPS   (vblank_mode=0, so not a 60 cap)
#
# WSLg moves every finished frame across an RDP transport, and a GPU-resident buffer
# costs a readback that a system-memory buffer does not. So "software" is not a defect
# here and this script no longer claims it is. Caveat on the caveat: glxgears is GLX
# over XWayland, whose glamor is on its own software fallback, so it measures the worst
# path and settles nothing about native-Wayland clients like kitty. glmark2-wayland
# would. Until someone runs it, which driver is FASTER is open.
#
# So the oracle is REACHABILITY, not selection: exit 1 only when the hardware path
# cannot be reached at all, which is a real plumbing regression. Exit 0 when it can,
# whether or not it is the default. Exit 2 when nothing could be measured. Vulkan never
# fails the run: there is no Vulkan-over-D3D12 driver in Ubuntu's mesa, so software
# Vulkan is the expected state here.
#
#     bash tools/wsl/gpu-probe.sh
#     bash tools/wsl/gpu-probe.sh --quiet    # verdict line only

set -uo pipefail

QUIET=0
[ "${1:-}" = "--quiet" ] && QUIET=1

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD="$(mktemp -d)"
trap 'rm -rf "$BUILD"' EXIT

say() { [ "$QUIET" -eq 1 ] || printf '%s\n' "$*"; }
hdr() { [ "$QUIET" -eq 1 ] || printf '\n== %s ==\n' "$*"; }

hdr "1. versions"
if command -v powershell.exe >/dev/null 2>&1; then
    # Runs from /mnt/c so powershell.exe does not warn about a UNC working directory.
    (cd /mnt/c && powershell.exe -NoProfile -Command 'wsl.exe --version' 2>/dev/null) \
        | tr -d '\r\0' | grep -E '^(WSL|Kernel|WSLg|MSRDC|Windows) ' | sed 's/^/  /'
else
    say "  powershell.exe not reachable, skipping the Windows-side version block"
fi
[ -f /mnt/wslg/versions.txt ] && sed -n '1,3p' /mnt/wslg/versions.txt | sed 's/^/  /'

hdr "2. the adapter Windows sees"
if command -v powershell.exe >/dev/null 2>&1; then
    (cd /mnt/c && powershell.exe -NoProfile -Command \
        'Get-CimInstance Win32_VideoController | ForEach-Object { "{0} | driver {1} | {2}" -f $_.Name, $_.DriverVersion, $_.Status }' 2>/dev/null) \
        | tr -d '\r\0' | grep -v '^\s*$' | sed 's/^/  /'
fi

hdr "3. kernel and loader plumbing"
if [ -e /dev/dxg ]; then say "  /dev/dxg          present"; else say "  /dev/dxg          MISSING, no GPU paravirtualisation"; fi
# /dev/dri is expected to be absent under WSL: the GPU is reached through /dev/dxg and
# libdxcore, not through a DRM render node. Its absence is also why mesa's default
# device probe finds nothing and silently falls back to llvmpipe.
if [ -d /dev/dri ]; then say "  /dev/dri          present ($(ls /dev/dri 2>/dev/null | tr '\n' ' '))"
else say "  /dev/dri          absent, which is normal under WSL"; fi
if [ -d /usr/lib/wsl/lib ]; then say "  /usr/lib/wsl/lib  $(ls /usr/lib/wsl/lib 2>/dev/null | tr '\n' ' ')"
else say "  /usr/lib/wsl/lib  MISSING"; fi
say "  ldconfig d3d12    $(ldconfig -p 2>/dev/null | grep -c 'libd3d12\|libdxcore') entries"
if [ -e /usr/lib/x86_64-linux-gnu/dri/d3d12_dri.so ]; then say "  d3d12_dri.so      present"
else say "  d3d12_dri.so      MISSING, install mesa's gallium d3d12 driver"; fi

hdr "4. OpenGL, measured three ways"
GL_DEFAULT=""; GL_D3D12=""; GL_SOFT=""
if ! command -v gcc >/dev/null 2>&1; then
    say "  gcc missing, cannot build the probe"
    printf 'VERDICT: UNKNOWN (no compiler)\n'
    exit 2
fi
if ! gcc -O0 -o "$BUILD/glprobe" "$HERE/glprobe.c" -ldl 2>"$BUILD/glbuild.err"; then
    say "  glprobe.c did not build:"; sed 's/^/    /' "$BUILD/glbuild.err"
    printf 'VERDICT: UNKNOWN (probe build failed)\n'
    exit 2
fi
# The "default" reading must have the overrides STRIPPED, not merely left unset by the
# caller. Found the hard way: this script was run from a shell that had already exported
# GALLIUM_DRIVER=d3d12, and it duly reported the forced value as the machine's default.
# A probe that inherits the thing it is measuring is measuring its own caller.
CLEAN='env -u GALLIUM_DRIVER -u MESA_LOADER_DRIVER_OVERRIDE -u LIBGL_ALWAYS_SOFTWARE -u GALLIUM_DRIVER_OVERRIDE'
AMBIENT="${GALLIUM_DRIVER:-}${MESA_LOADER_DRIVER_OVERRIDE:+ MESA_LOADER_DRIVER_OVERRIDE=$MESA_LOADER_DRIVER_OVERRIDE}"

GL_DEFAULT=$($CLEAN                       "$BUILD/glprobe" 2>/dev/null | grep '^GL_RENDERER=' | cut -d= -f2-)
GL_D3D12=$($CLEAN  GALLIUM_DRIVER=d3d12   "$BUILD/glprobe" 2>/dev/null | grep '^GL_RENDERER=' | cut -d= -f2-)
GL_SOFT=$($CLEAN   LIBGL_ALWAYS_SOFTWARE=1 "$BUILD/glprobe" 2>/dev/null | grep '^GL_RENDERER=' | cut -d= -f2-)
say "  default, overrides stripped   ${GL_DEFAULT:-<no context>}"
say "  GALLIUM_DRIVER=d3d12          ${GL_D3D12:-<no context>}"
say "  LIBGL_ALWAYS_SOFTWARE=1       ${GL_SOFT:-<no context>}   <- control"
if [ -n "$AMBIENT" ]; then
    say "  NOTE the calling shell already sets GALLIUM_DRIVER=$AMBIENT, stripped for the reading above"
fi

hdr "5. Vulkan"
if gcc -O0 -o "$BUILD/vkprobe" "$HERE/vkprobe.c" -ldl 2>/dev/null; then
    "$BUILD/vkprobe" 2>/dev/null | sed 's/^/  /'
else
    say "  vkprobe.c did not build"
fi
if [ -d /usr/share/vulkan/icd.d ]; then
    say "  ICDs installed: $(ls /usr/share/vulkan/icd.d 2>/dev/null | tr '\n' ' ')"
    if ls /usr/share/vulkan/icd.d 2>/dev/null | grep -q dzn; then
        say "  dzn present, so a Vulkan-over-D3D12 hardware path exists"
    else
        say "  no dzn ICD, so there is no Vulkan-over-D3D12 path and software Vulkan is expected"
    fi
fi

hdr "6. compositor"
if [ -f /mnt/wslg/stderr.log ]; then
    grep -iE 'glamor|falling back to sw' /mnt/wslg/stderr.log | tail -3 | sed 's/^/  /'
fi
# grep -c prints its count and then exits 1 when the count is zero, so an `|| echo`
# fallback here appends a second line to a substitution that already holds "0".
say "  weston instances started this boot: $(grep -c '] weston ' /mnt/wslg/weston.log 2>/dev/null | head -1)"
say "  weston SIGSEGVs this boot:          $(grep -c 'terminated with signal 11' /mnt/wslg/stderr.log 2>/dev/null | head -1)"

is_software() {
    case "$1" in *llvmpipe*|*softpipe*|*swrast*|"") return 0;; *) return 1;; esac
}

printf '\n'
if [ -z "$GL_DEFAULT" ]; then
    printf 'VERDICT: UNKNOWN, no GL context could be created\n'
    exit 2
fi

if is_software "$GL_DEFAULT"; then
    printf 'SELECTED: software, "%s"\n' "$GL_DEFAULT"
else
    printf 'SELECTED: hardware, "%s"\n' "$GL_DEFAULT"
fi

if is_software "$GL_D3D12"; then
    printf 'VERDICT: GPU UNREACHABLE. GALLIUM_DRIVER=d3d12 also lands on "%s".\n' "${GL_D3D12:-<no context>}"
    printf 'Check /dev/dxg, /usr/lib/wsl/lib and d3d12_dri.so in section 3.\n'
    exit 1
fi

printf 'VERDICT: GPU REACHABLE. GALLIUM_DRIVER=d3d12 gives "%s".\n' "$GL_D3D12"
printf 'Reachable is not the same as faster. On this box glxgears measured 206-269 FPS on\n'
printf 'llvmpipe against 10-29 FPS on d3d12, because WSLg pays a readback per frame. Which\n'
printf 'driver a native-Wayland client should use here is unmeasured; glmark2-wayland would\n'
printf 'settle it. The launchers are deliberately left on the default.\n'
exit 0
