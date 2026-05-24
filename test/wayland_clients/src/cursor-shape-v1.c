#include <errno.h>
#include <getopt.h>
#include <stdarg.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <time.h>
#include <unistd.h>
#include <wayland-client.h>

#include "cursor-shape-v1-client-protocol.h"
#include "xdg-shell-client-protocol.h"

#include <stdarg.h>

static FILE *log_file = NULL;

static void log_msg(const char *fmt, ...) {
    if (!log_file) {
        return;
    }

    time_t now = time(NULL);
    struct tm tm;
    localtime_r(&now, &tm);

    fprintf(log_file, "[%02d:%02d:%02d] ", tm.tm_hour, tm.tm_min, tm.tm_sec);

    va_list args;
    va_start(args, fmt);
    vfprintf(log_file, fmt, args);
    va_end(args);

    fputc('\n', log_file);
    fflush(log_file);
}
/* ---------------- globals ---------------- */

static struct wl_display *display;
static struct wl_registry *registry;

static struct wl_compositor *compositor;
static struct xdg_wm_base *xdg_wm_base;
static struct wl_shm *shm;

static struct wl_surface *surface;
static struct xdg_surface *xdg_surface;
static struct xdg_toplevel *toplevel;

static struct wl_pointer *pointer;
static struct wp_cursor_shape_manager_v1 *cursor_manager;
static struct wp_cursor_shape_device_v1 *cursor_device;

/* ---------------- state ---------------- */

static bool configured = false;
static uint32_t configure_serial = 0;

static uint32_t enter_serial = 0;

static uint32_t requested_shape = WP_CURSOR_SHAPE_DEVICE_V1_SHAPE_CROSSHAIR;

/* ---------------- shm ---------------- */

static int create_shm_file(size_t size) {
    char name[] = "/tmp/wl-shm-XXXXXX";
    int fd = mkstemp(name);
    unlink(name);

    ftruncate(fd, size);
    return fd;
}

static struct wl_buffer *create_buffer(int w, int h, void **data_out) {
    int stride = w * 4;
    int size = stride * h;

    int fd = create_shm_file(size);

    void *data = mmap(NULL, size, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);

    struct wl_shm_pool *pool = wl_shm_create_pool(shm, fd, size);

    struct wl_buffer *buf =
        wl_shm_pool_create_buffer(pool, 0, w, h, stride, WL_SHM_FORMAT_XRGB8888);

    wl_shm_pool_destroy(pool);
    close(fd);

    *data_out = data;
    return buf;
}

/* ---------------- cursor ---------------- */

static void set_shape(uint32_t serial, uint32_t shape) {
    log_msg("[client] set_shape cursor_device=%p", cursor_device);
    if (!cursor_device)
        return;

    wp_cursor_shape_device_v1_set_shape(cursor_device, serial, shape);
    wl_display_flush(display);
}

/* ---------------- pointer ---------------- */

static void pointer_enter(void *data, struct wl_pointer *p, uint32_t serial,
                          struct wl_surface *surf, wl_fixed_t x, wl_fixed_t y) {
    log_msg("[client] POINTER ENTER serial=%u surface=%p x=%f y=%f", serial, surf,
            wl_fixed_to_double(x), wl_fixed_to_double(y));

    enter_serial = serial;

    if (!cursor_device) {
        log_msg("[client] WARNING: cursor_device is NULL at ENTER");
    }

    set_shape(serial, requested_shape);
}

static void pointer_leave(void *data, struct wl_pointer *p, uint32_t serial,
                          struct wl_surface *surf) {
    log_msg("[client] POINTER LEAVE serial=%u surface=%p", serial, surf);
}

static void pointer_motion(void *data, struct wl_pointer *p, uint32_t time, wl_fixed_t x,
                           wl_fixed_t y) {
    (void)data;
    (void)p;
    (void)time;
    (void)x;
    (void)y;
}

static const struct wl_pointer_listener pointer_listener = {
    .enter = pointer_enter,
    .leave = pointer_leave,
    .motion = pointer_motion,
};

/* ---------------- seat ---------------- */

static void seat_capabilities(void *data, struct wl_seat *seat, uint32_t caps) {
    log_msg("[client] SEAT CAPABILITIES: pointer=%d keyboard=%d",
            !!(caps & WL_SEAT_CAPABILITY_POINTER), !!(caps & WL_SEAT_CAPABILITY_KEYBOARD));

    if (caps & WL_SEAT_CAPABILITY_POINTER) {
        pointer = wl_seat_get_pointer(seat);

        log_msg("[client] wl_pointer created: %p", pointer);

        wl_pointer_add_listener(pointer, &pointer_listener, NULL);

        cursor_device = wp_cursor_shape_manager_v1_get_pointer(cursor_manager, pointer);

        log_msg("[client] cursor_device created: %p", cursor_device);
    }
}

static const struct wl_seat_listener seat_listener = {
    .capabilities = seat_capabilities,
};

/* ---------------- xdg-shell ---------------- */

static void wm_ping(void *data, struct xdg_wm_base *wm, uint32_t serial) {
    xdg_wm_base_pong(wm, serial);
}

static const struct xdg_wm_base_listener wm_listener = {
    .ping = wm_ping,
};

static void xdg_surface_configure(void *data, struct xdg_surface *surf, uint32_t serial) {
    xdg_surface_ack_configure(surf, serial);
    wl_surface_commit(surface);
}

static const struct xdg_surface_listener xdg_surface_listener = {
    .configure = xdg_surface_configure,
};

static void toplevel_close(void *data, struct xdg_toplevel *t) { exit(0); }

static void toplevel_configure(void *data, struct xdg_toplevel *t, int32_t w, int32_t h,
                               struct wl_array *states) {
    (void)data;
    (void)t;
    (void)w;
    (void)h;
    (void)states;
}

static const struct xdg_toplevel_listener toplevel_listener = {
    .configure = toplevel_configure,
    .close = toplevel_close,
};

/* ---------------- registry ---------------- */

static void registry_global(void *data, struct wl_registry *reg, uint32_t name, const char *iface,
                            uint32_t version) {
    log_msg("[client] GLOBAL: %s (name=%u version=%u)", iface, name, version);

    if (strcmp(iface, wl_compositor_interface.name) == 0) {
        compositor = wl_registry_bind(reg, name, &wl_compositor_interface, 4);
    }

    if (strcmp(iface, xdg_wm_base_interface.name) == 0) {
        xdg_wm_base = wl_registry_bind(reg, name, &xdg_wm_base_interface, 1);

        xdg_wm_base_add_listener(xdg_wm_base, &wm_listener, NULL);
    }

    if (strcmp(iface, wl_shm_interface.name) == 0) {
        shm = wl_registry_bind(reg, name, &wl_shm_interface, 1);
    }

    if (strcmp(iface, wl_seat_interface.name) == 0) {
        log_msg("[client] binding wl_seat");

        struct wl_seat *seat = wl_registry_bind(reg, name, &wl_seat_interface, 1);

        wl_seat_add_listener(seat, &seat_listener, NULL);
    }

    if (strcmp(iface, wp_cursor_shape_manager_v1_interface.name) == 0) {
        log_msg("[client] binding cursor_shape_manager_v1");

        cursor_manager = wl_registry_bind(reg, name, &wp_cursor_shape_manager_v1_interface, 1);
    }
}

static const struct wl_registry_listener registry_listener = {
    .global = registry_global,
};

/* ---------------- main ---------------- */

int main(int argc, char *argv[]) {
    int opt;

    /* ---------------- CLI ---------------- */
    while ((opt = getopt(argc, argv, "c:h")) != -1) {
        switch (opt) {
        case 'c':
            if (strcmp(optarg, "text") == 0)
                requested_shape = WP_CURSOR_SHAPE_DEVICE_V1_SHAPE_TEXT;
            else if (strcmp(optarg, "crosshair") == 0)
                requested_shape = WP_CURSOR_SHAPE_DEVICE_V1_SHAPE_CROSSHAIR;
            else if (strcmp(optarg, "wait") == 0)
                requested_shape = WP_CURSOR_SHAPE_DEVICE_V1_SHAPE_WAIT;
            else if (strcmp(optarg, "help") == 0)
                requested_shape = WP_CURSOR_SHAPE_DEVICE_V1_SHAPE_HELP;
            else if (strcmp(optarg, "pointer") == 0)
                requested_shape = WP_CURSOR_SHAPE_DEVICE_V1_SHAPE_POINTER;
            break;
        }
    }

    /* ---------------- logging ---------------- */
    log_file = fopen("/tmp/wl_cursor_client.log", "a");
    if (!log_file) {
        perror("fopen log file");
        return 1;
    }
    setvbuf(log_file, NULL, _IOLBF, 0);

    log_msg("=== START TEST ===");

    /* ---------------- connect ---------------- */
    display = wl_display_connect(NULL);
    if (!display)
        return 1;

    registry = wl_display_get_registry(display);
    wl_registry_add_listener(registry, &registry_listener, NULL);

    /* ---- MUST: bind globals ---- */
    wl_display_roundtrip(display);

    if (!compositor || !xdg_wm_base || !shm || !cursor_manager) {
        fprintf(stderr, "missing globals\n");
        return 1;
    }

    /* ---------------- surface ---------------- */
    surface = wl_compositor_create_surface(compositor);

    xdg_surface = xdg_wm_base_get_xdg_surface(xdg_wm_base, surface);
    toplevel = xdg_surface_get_toplevel(xdg_surface);

    xdg_surface_add_listener(xdg_surface, &xdg_surface_listener, NULL);
    xdg_toplevel_add_listener(toplevel, &toplevel_listener, NULL);

    xdg_toplevel_set_min_size(toplevel, 300, 300);
    xdg_toplevel_set_max_size(toplevel, 300, 300);

    wl_surface_commit(surface);

    /* ---- MUST: wait for configure ---- */
    wl_display_roundtrip(display);

    /* ---------------- buffer ---------------- */
    void *pixels;
    struct wl_buffer *buffer = create_buffer(300, 300, &pixels);

    memset(pixels, 0x80, 300 * 300 * 4);

    wl_surface_attach(surface, buffer, 0, 0);
    wl_surface_commit(surface);

    log_msg("running cursor-shape test window\n");

    /* =========================================================
     * CRITICAL FIX: SYNC BARRIER BEFORE ENTERING TEST LOOP
     * ========================================================= */

    wl_display_roundtrip(display);
    wl_display_dispatch_pending(display);

    /*
     * This forces:
     * - seat focus to settle
     * - pointer enter to be delivered
     * - cursor-shape device to be fully active
     */

    /* ---------------- main loop ---------------- */
    log_msg("Reached loops");
    while (wl_display_dispatch(display) != -1) {
        /* keep draining events deterministically */
    }

    log_msg("=== END TEST ===\n");

    if (log_file) {
        fclose(log_file);
        log_file = NULL;
    }

    return 0;
}
