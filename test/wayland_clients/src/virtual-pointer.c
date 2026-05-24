#define _POSIX_C_SOURCE 200809L

#include "virtual-pointer-unstable-v1-client-protocol.h"
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/select.h>
#include <unistd.h>
#include <wayland-client-protocol.h>
#include <wayland-client.h>

/* globals */
static struct wl_display *display;
static struct wl_registry *registry;

static struct zwlr_virtual_pointer_manager_v1 *vp_manager;
static struct zwlr_virtual_pointer_v1 *vp;
static struct wl_seat *seat;

/* registry */
static void registry_global(void *data, struct wl_registry *registry, uint32_t name,
                            const char *iface, uint32_t version) {
    if (strcmp(iface, wl_seat_interface.name) == 0) {
        seat = wl_registry_bind(registry, name, &wl_seat_interface, 1);
    }

    if (strcmp(iface, zwlr_virtual_pointer_manager_v1_interface.name) == 0) {

        vp_manager =
            wl_registry_bind(registry, name, &zwlr_virtual_pointer_manager_v1_interface, 1);
    }
}

static const struct wl_registry_listener registry_listener = {
    .global = registry_global,
};

/* create vp */
static void create_vp(void) {
    vp = zwlr_virtual_pointer_manager_v1_create_virtual_pointer(vp_manager, seat);

    if (!vp) {
        fprintf(stderr, "failed to create virtual pointer\n");
        exit(1);
    }
    fprintf(stderr, "Created virtual pointer\n");
}

/* command handlers */
static void handle_line(char *line) {
    if (strncmp(line, "move ", 5) == 0) {
        int dx, dy;
        sscanf(line + 5, "%d %d", &dx, &dy);
        zwlr_virtual_pointer_v1_motion(vp, 0, dx, dy);
        zwlr_virtual_pointer_v1_frame(vp);
    }

    if (strncmp(line, "abs ", 4) == 0) {
        int x, y, w, h;
        sscanf(line + 4, "%d %d %d %d", &x, &y, &w, &h);
        zwlr_virtual_pointer_v1_motion_absolute(vp, 0, x, y, w, h);
        zwlr_virtual_pointer_v1_frame(vp);
    }

    if (strncmp(line, "button ", 7) == 0) {
        int b, s;
        sscanf(line + 7, "%d %d", &b, &s);
        zwlr_virtual_pointer_v1_button(vp, 0, b, s);
        zwlr_virtual_pointer_v1_frame(vp);
    }
}

/* main */
int main(void) {
    display = wl_display_connect(NULL);
    if (!display)
        return 1;

    registry = wl_display_get_registry(display);
    wl_registry_add_listener(registry, &registry_listener, NULL);

    wl_display_roundtrip(display);

    if (!vp_manager) {
        fprintf(stderr, "no virtual pointer support\n");
        return 1;
    }

    fprintf(stderr, "Creating virtual pointer\n");
    create_vp();
    fprintf(stderr, "Created request, doing roundtrip\n");
    wl_display_roundtrip(display);
    fprintf(stderr, "Roundtrip complete\n");

    fprintf(stderr, "vp_client ready\n");

    /* keep alive + command loop */
    char *line = NULL;
    size_t len = 0;

    // while (wl_display_dispatch_pending(display) != -1) {

    //     /* flush Wayland */
    //     wl_display_flush(display);

    //     /* non-blocking stdin check */
    //     fd_set fds;
    //     FD_ZERO(&fds);
    //     FD_SET(STDIN_FILENO, &fds);
    //     FD_SET(wl_display_get_fd(display), &fds);

    //     int maxfd = wl_display_get_fd(display);

    //     if (select(maxfd + 1, &fds, NULL, NULL, NULL) > 0) {

    //         if (FD_ISSET(STDIN_FILENO, &fds)) {
    //             if (getline(&line, &len, stdin) == -1)
    //                 break;

    //             handle_line(line);
    //         }

    //         if (FD_ISSET(wl_display_get_fd(display), &fds)) {
    //             wl_display_dispatch(display);
    //         }
    //     }
    // }
    for (;;) {
        if (wl_display_dispatch(display) == -1) {
            break;
        }
    }

    free(line);
    fprintf(stderr, "Exiting...\n");
    return 0;
}
