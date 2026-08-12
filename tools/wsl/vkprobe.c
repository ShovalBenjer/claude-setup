/* Enumerates Vulkan physical devices and prints name plus device type.
 *
 * Same reason as glprobe.c: vulkan-tools is not installed and installing it needs a
 * sudo password. Only the loader (libvulkan.so.1) is needed at runtime.
 *
 * Struct layouts are hand-declared against the Vulkan 1.0 ABI, which is frozen, so
 * this stays correct across loader versions:
 *   VkInstanceCreateInfo is 64 bytes with sType at 0 and every pointer 8-aligned.
 *   VkPhysicalDeviceProperties has deviceType at offset 16 and deviceName at 20.
 * The properties buffer is over-allocated rather than fully declared, because the
 * only fields read are in the first 276 bytes and VkPhysicalDeviceLimits is 400+
 * bytes of fields nothing here looks at.
 *
 *     gcc -O0 -o vkprobe vkprobe.c -ldl
 *
 * A CPU device type (4) means lavapipe, which is software. On WSL the hardware path
 * would be the dzn driver over D3D12, and dzn is not in Ubuntu's mesa-vulkan-drivers.
 */
#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include <dlfcn.h>

typedef void *VkInstance;
typedef void *VkPhysicalDevice;
typedef int VkResult;

#define VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO 1
#define MAX_DEVICES 8

static const char *device_type_name(uint32_t t) {
    switch (t) {
        case 0: return "OTHER";
        case 1: return "INTEGRATED_GPU";
        case 2: return "DISCRETE_GPU";
        case 3: return "VIRTUAL_GPU";
        case 4: return "CPU (software)";
        default: return "UNKNOWN";
    }
}

int main(void) {
    void *vk = dlopen("libvulkan.so.1", RTLD_LAZY);
    if (!vk) { fprintf(stderr, "no libvulkan.so.1: %s\n", dlerror()); return 2; }

    VkResult (*createInstance)(const void *, const void *, VkInstance *) =
        dlsym(vk, "vkCreateInstance");
    VkResult (*enumeratePhysicalDevices)(VkInstance, uint32_t *, VkPhysicalDevice *) =
        dlsym(vk, "vkEnumeratePhysicalDevices");
    void (*getPhysicalDeviceProperties)(VkPhysicalDevice, void *) =
        dlsym(vk, "vkGetPhysicalDeviceProperties");
    void (*destroyInstance)(VkInstance, const void *) = dlsym(vk, "vkDestroyInstance");

    if (!createInstance || !enumeratePhysicalDevices || !getPhysicalDeviceProperties) {
        fprintf(stderr, "libvulkan is missing entry points\n");
        return 2;
    }

    unsigned char create_info[64];
    memset(create_info, 0, sizeof(create_info));
    *(uint32_t *)create_info = VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO;

    VkInstance inst = NULL;
    VkResult r = createInstance(create_info, NULL, &inst);
    if (r != 0 || !inst) { printf("VK_INSTANCE=failed rc=%d\n", r); return 3; }

    uint32_t count = 0;
    r = enumeratePhysicalDevices(inst, &count, NULL);
    if (r != 0) { printf("VK_ENUMERATE=failed rc=%d\n", r); return 4; }
    printf("VK_DEVICE_COUNT=%u\n", count);
    if (count == 0) { if (destroyInstance) destroyInstance(inst, NULL); return 0; }
    if (count > MAX_DEVICES) count = MAX_DEVICES;

    VkPhysicalDevice devices[MAX_DEVICES];
    r = enumeratePhysicalDevices(inst, &count, devices);
    if (r != 0) { printf("VK_ENUMERATE2=failed rc=%d\n", r); return 4; }

    for (uint32_t i = 0; i < count; i++) {
        unsigned char props[2048];
        memset(props, 0, sizeof(props));
        getPhysicalDeviceProperties(devices[i], props);
        uint32_t api  = *(uint32_t *)(props + 0);
        uint32_t type = *(uint32_t *)(props + 16);
        const char *name = (const char *)(props + 20);
        printf("VK_DEVICE_%u=%s | type=%s | api=%u.%u.%u\n",
               i, name, device_type_name(type),
               (api >> 22) & 0x7F, (api >> 12) & 0x3FF, api & 0xFFF);
    }

    if (destroyInstance) destroyInstance(inst, NULL);
    return 0;
}
