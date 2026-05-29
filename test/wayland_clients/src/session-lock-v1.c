/*
 * Test client for qtile's ext-session-lock-v1 implementation.
 *
 * Then send commands on stdin (one per line):
 *
 *   lock                    - Acquire the session lock
 *   unlock                  - Send unlock request
 *   destroy_without_unlock  - Simulate a crash (destroy lock object without unlocking)
 *   create_surface          - Create lock surfaces for all outputs (must be locked first)
 *   destroy_surface         - Destroy all lock surfaces
 *   double_lock             - Attempt a second concurrent lock (should be rejected)
 *   check_locked            - Assert we have received the "locked" event
 *   check_unlocked          - Assert lock object is gone / we are unlocked
 *   check_surface_count <N> - Assert exactly N lock surfaces are alive
 *   roundtrip               - Force a Wayland roundtrip (flush + sync)
 *   quit                    - Exit the test client
 *
 * Every command prints "OK" or "ERROR: <reason>" to stdout.
 */

#define _POSIX_C_SOURCE 200809L

#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include <wayland-client.h>

/* Generated from ext-session-lock-v1.xml */
#include "ext-session-lock-v1-client-protocol.h"

/* ─── State ──────────────────────────────────────────────────────────────── */

struct output_entry {
    struct wl_output *wl_output;
    int32_t x, y, width, height; /* logical geometry */
    struct wl_list link;
};

struct surface_entry {
    struct ext_session_lock_surface_v1 *lock_surface;
    struct wl_surface *wl_surface;
    struct output_entry *output;
    bool configured;
    struct wl_list link;
};

static struct {
    struct wl_display *display;
    struct wl_registry *registry;
    struct wl_compositor *compositor;
    struct ext_session_lock_manager_v1 *lock_manager;

    struct wl_list outputs;  /* output_entry */
    struct wl_list surfaces; /* surface_entry */

    struct ext_session_lock_v1 *lock;
    struct ext_session_lock_v1 *pending_lock;
    bool got_locked;    /* received "locked" event */
    bool lock_finished; /* lock object was destroyed by compositor */
    bool destroyed;
} state;

/* ─── Protocol helpers ───────────────────────────────────────────────────── */

static void surface_configure(void *data, struct ext_session_lock_surface_v1 *lock_surface,
                              uint32_t serial, uint32_t width, uint32_t height) {
    struct surface_entry *se = data;
    se->configured = true;
    ext_session_lock_surface_v1_ack_configure(lock_surface, serial);
    /* Commit so the compositor considers the surface mapped */
    wl_surface_commit(se->wl_surface);
}

static const struct ext_session_lock_surface_v1_listener surface_listener = {
    .configure = surface_configure,
};

static void lock_locked(void *data, struct ext_session_lock_v1 *lock) {
    (void)data;
    (void)lock;
    state.got_locked = true;
}

static void lock_finished(void *data, struct ext_session_lock_v1 *lock) {
    /*
     * "finished" is sent when:
     *   (a) the compositor rejects the lock (already locked / crashed), or
     *   (b) another compositor-side event invalidates this lock.
     * In either case the client MUST destroy the lock object.
     */
    (void)data;
    state.lock_finished = true;
    if (!state.destroyed) {
        ext_session_lock_v1_destroy(lock);
    }
    if (lock == state.lock) {
        state.lock = NULL;
    };
}

static const struct ext_session_lock_v1_listener lock_listener = {
    .locked = lock_locked,
    .finished = lock_finished,
};

/* ─── Registry ───────────────────────────────────────────────────────────── */

static void output_geometry(void *data, struct wl_output *wl_output, int32_t x, int32_t y,
                            int32_t physical_width, int32_t physical_height, int32_t subpixel,
                            const char *make, const char *model, int32_t transform) {
    struct output_entry *oe = data;
    oe->x = x;
    oe->y = y;
    (void)wl_output;
    (void)physical_width;
    (void)physical_height;
    (void)subpixel;
    (void)make;
    (void)model;
    (void)transform;
}

static void output_mode(void *data, struct wl_output *wl_output, uint32_t flags, int32_t width,
                        int32_t height, int32_t refresh) {
    struct output_entry *oe = data;
    if (flags & WL_OUTPUT_MODE_CURRENT) {
        oe->width = width;
        oe->height = height;
    }
    (void)wl_output;
    (void)refresh;
}

static void output_done(void *data, struct wl_output *wl_output) {
    (void)data;
    (void)wl_output;
}
static void output_scale(void *data, struct wl_output *wl_output, int32_t factor) {
    (void)data;
    (void)wl_output;
    (void)factor;
}
static void output_name(void *data, struct wl_output *wl_output, const char *name) {
    (void)data;
    (void)wl_output;
    (void)name;
}
static void output_description(void *data, struct wl_output *wl_output, const char *desc) {
    (void)data;
    (void)wl_output;
    (void)desc;
}

static const struct wl_output_listener output_listener = {
    .geometry = output_geometry,
    .mode = output_mode,
    .done = output_done,
    .scale = output_scale,
    .name = output_name,
    .description = output_description,
};

static void registry_global(void *data, struct wl_registry *registry, uint32_t name,
                            const char *interface, uint32_t version) {
    (void)data;
    if (strcmp(interface, wl_compositor_interface.name) == 0) {
        state.compositor = wl_registry_bind(registry, name, &wl_compositor_interface, 4);
    } else if (strcmp(interface, ext_session_lock_manager_v1_interface.name) == 0) {
        state.lock_manager =
            wl_registry_bind(registry, name, &ext_session_lock_manager_v1_interface, 1);
    } else if (strcmp(interface, wl_output_interface.name) == 0) {
        struct output_entry *oe = calloc(1, sizeof(*oe));
        oe->wl_output = wl_registry_bind(registry, name, &wl_output_interface, 4);
        wl_output_add_listener(oe->wl_output, &output_listener, oe);
        wl_list_insert(&state.outputs, &oe->link);
    }
}

static void registry_global_remove(void *data, struct wl_registry *registry, uint32_t name) {
    (void)data;
    (void)registry;
    (void)name;
}

static const struct wl_registry_listener registry_listener = {
    .global = registry_global,
    .global_remove = registry_global_remove,
};

/* ─── Roundtrip helper ───────────────────────────────────────────────────── */

/*
 * Drain the Wayland socket for up to `timeout_ms` milliseconds.
 * Returns true if at least one event was dispatched.
 */
static bool drain_events(int timeout_ms) {
    wl_display_flush(state.display);
    struct pollfd pfd = {
        .fd = wl_display_get_fd(state.display),
        .events = POLLIN,
    };
    int ready = poll(&pfd, 1, timeout_ms);
    if (ready > 0) {
        wl_display_dispatch(state.display);
        return true;
    }
    return false;
}

static void do_roundtrip(void) { wl_display_roundtrip(state.display); }

/* ─── Commands ───────────────────────────────────────────────────────────── */

/*
 * lock
 * Acquire the session lock.  Expects:
 *   - lock_manager is present
 *   - we are not already locked
 * After sending, we do a roundtrip so we can check whether "locked" or
 * "finished" was received.
 */
static void cmd_lock(void) {
    if (state.lock_manager == NULL) {
        puts("ERROR: ext_session_lock_manager_v1 not advertised");
        return;
    }

    state.got_locked = false;
    state.lock_finished = false;
    state.destroyed = false;

    struct ext_session_lock_v1 *lock = ext_session_lock_manager_v1_lock(state.lock_manager);

    state.pending_lock = lock;

    ext_session_lock_v1_add_listener(lock, &lock_listener, NULL);

    do_roundtrip();

    if (state.got_locked) {
        state.lock = lock;
        state.pending_lock = NULL;

        puts("OK");
    } else if (state.lock_finished) {
        state.pending_lock = NULL;
        puts("ERROR: compositor rejected lock");
    } else {
        ext_session_lock_v1_destroy(lock);
        state.pending_lock = NULL;

        puts("ERROR: no response after roundtrip");
    }
}

/*
 * unlock
 * Send the unlock request.  Expects we are currently locked.
 */
static void cmd_unlock(void) {
    if (state.lock == NULL) {
        puts("ERROR: no active lock");
        return;
    }

    ext_session_lock_v1_unlock_and_destroy(state.lock);
    state.lock = NULL;
    state.got_locked = false;

    do_roundtrip();
    puts("OK");
}

/*
 * create_surface
 * Create one lock surface per advertised output.
 */
static void cmd_create_surface(void) {
    if (state.lock == NULL) {
        puts("ERROR: not locked");
        return;
    }
    if (state.compositor == NULL) {
        puts("ERROR: wl_compositor not available");
        return;
    }

    int created = 0;
    struct output_entry *oe;
    wl_list_for_each(oe, &state.outputs, link) {
        struct surface_entry *se = calloc(1, sizeof(*se));
        se->output = oe;
        se->wl_surface = wl_compositor_create_surface(state.compositor);

        se->lock_surface =
            ext_session_lock_v1_get_lock_surface(state.lock, se->wl_surface, oe->wl_output);
        ext_session_lock_surface_v1_add_listener(se->lock_surface, &surface_listener, se);

        wl_list_insert(&state.surfaces, &se->link);
        created++;
    }

    if (created == 0) {
        puts("ERROR: no outputs found");
        return;
    }

    /* Roundtrip: compositor should send configure events */
    do_roundtrip();

    /* Check all surfaces received configure */
    bool all_configured = true;
    struct surface_entry *se;
    wl_list_for_each(se, &state.surfaces, link) {
        if (!se->configured) {
            all_configured = false;
            break;
        }
    }

    if (all_configured) {
        printf("OK\n");
    } else {
        puts("ERROR: one or more lock surfaces did not receive configure event");
    }
}

/*
 * destroy_surface
 * Destroy all current lock surfaces.
 */
static void cmd_destroy_surface(void) {
    if (wl_list_empty(&state.surfaces)) {
        puts("ERROR: no surfaces to destroy");
        return;
    }

    struct surface_entry *se, *tmp;
    wl_list_for_each_safe(se, tmp, &state.surfaces, link) {
        ext_session_lock_surface_v1_destroy(se->lock_surface);
        wl_surface_destroy(se->wl_surface);
        wl_list_remove(&se->link);
        free(se);
    }

    do_roundtrip();
    puts("OK");
}

/*
 * check_locked
 * Verify we have received the "locked" event (synchronous check).
 */
static void cmd_check_locked(void) {
    do_roundtrip();
    if (state.lock != NULL) {
        puts("OK");
    } else {
        puts("ERROR: not in locked state");
    }
}

/*
 * check_unlocked
 * Verify the lock has been torn down.
 */
static void cmd_check_unlocked(void) {
    do_roundtrip();
    if (state.lock == NULL) {
        puts("OK");
    } else {
        puts("ERROR: still in locked state");
    }
}

/*
 * check_surface_count <N>
 * Assert exactly N lock surfaces are tracked.
 */
static void cmd_check_surface_count(const char *arg) {
    if (arg == NULL) {
        puts("ERROR: usage: check_surface_count <N>");
        return;
    }
    int expected = atoi(arg);
    int actual = 0;
    struct surface_entry *se;
    wl_list_for_each(se, &state.surfaces, link) { actual++; }
    if (actual == expected) {
        puts("OK");
    } else {
        printf("ERROR: expected %d surfaces, got %d\n", expected, actual);
    }
}

/*
 * roundtrip
 * Force a Wayland roundtrip (useful to drain pending events from the
 * compositor before a subsequent check command).
 */
static void cmd_roundtrip(void) {
    do_roundtrip();
    puts("OK");
}

/* ─── Command dispatcher ─────────────────────────────────────────────────── */

static void dispatch_command(char *line) {
    /* Strip trailing newline */
    size_t len = strlen(line);
    while (len > 0 && (line[len - 1] == '\n' || line[len - 1] == '\r')) {
        line[--len] = '\0';
    }
    if (len == 0)
        return;

    /* Split into verb + optional argument */
    char *verb = line;
    char *arg = NULL;
    char *sp = strchr(line, ' ');
    if (sp != NULL) {
        *sp = '\0';
        arg = sp + 1;
    }

    if (strcmp(verb, "lock") == 0)
        cmd_lock();
    else if (strcmp(verb, "unlock") == 0)
        cmd_unlock();
    else if (strcmp(verb, "create_surface") == 0)
        cmd_create_surface();
    else if (strcmp(verb, "destroy_surface") == 0)
        cmd_destroy_surface();
    else if (strcmp(verb, "check_locked") == 0)
        cmd_check_locked();
    else if (strcmp(verb, "check_unlocked") == 0)
        cmd_check_unlocked();
    else if (strcmp(verb, "check_surface_count") == 0)
        cmd_check_surface_count(arg);
    else if (strcmp(verb, "roundtrip") == 0)
        cmd_roundtrip();
    else if (strcmp(verb, "quit") == 0) {
        puts("OK");
        exit(0);
    } else {
        printf("ERROR: unknown command '%s'\n", verb);
    }

    fflush(stdout);
}

/* ─── Main ───────────────────────────────────────────────────────────────── */

int main(void) {
    wl_list_init(&state.outputs);
    wl_list_init(&state.surfaces);

    state.display = wl_display_connect(NULL);
    if (state.display == NULL) {
        fprintf(stderr, "ERROR: failed to connect to Wayland display: %s\n", strerror(errno));
        return 1;
    }

    state.registry = wl_display_get_registry(state.display);
    wl_registry_add_listener(state.registry, &registry_listener, NULL);
    wl_display_roundtrip(state.display); /* bind globals */
    wl_display_roundtrip(state.display); /* receive output events */

    if (state.lock_manager == NULL) {
        fprintf(stderr, "ERROR: compositor does not advertise ext_session_lock_manager_v1\n");
        return 1;
    }

    /* Make stdin non-blocking so we can interleave Wayland event processing */
    int stdin_flags = fcntl(STDIN_FILENO, F_GETFL, 0);
    fcntl(STDIN_FILENO, F_SETFL, stdin_flags | O_NONBLOCK);

    fprintf(stderr, "ready\n");
    fflush(stderr);

    char line[256];
    size_t pos = 0;

    struct pollfd fds[2] = {
        {.fd = STDIN_FILENO, .events = POLLIN},
        {.fd = wl_display_get_fd(state.display), .events = POLLIN},
    };

    while (1) {
        wl_display_flush(state.display);
        int ret = poll(fds, 2, -1);
        if (ret < 0) {
            if (errno == EINTR)
                continue;
            perror("poll");
            break;
        }

        /* Wayland events */
        if (fds[1].revents & POLLIN) {
            wl_display_dispatch(state.display);
        }

        /* Stdin */
        if (fds[0].revents & POLLIN) {
            ssize_t n = read(STDIN_FILENO, line + pos, sizeof(line) - pos - 1);
            if (n <= 0) {
                if (n == 0)
                    break; /* EOF */
                if (errno == EAGAIN)
                    continue;
                perror("read");
                break;
            }
            pos += (size_t)n;
            line[pos] = '\0';

            /* Process all complete lines */
            char *start = line;
            char *nl;
            while ((nl = strchr(start, '\n')) != NULL) {
                *nl = '\0';
                dispatch_command(start);
                start = nl + 1;
            }
            /* Move any incomplete line to the front */
            size_t remaining = (size_t)((line + pos) - start);
            memmove(line, start, remaining);
            pos = remaining;
        }
    }

    /* Cleanup */
    struct surface_entry *se, *stmp;
    wl_list_for_each_safe(se, stmp, &state.surfaces, link) {
        ext_session_lock_surface_v1_destroy(se->lock_surface);
        wl_surface_destroy(se->wl_surface);
        free(se);
    }
    if (state.lock) {
        ext_session_lock_v1_unlock_and_destroy(state.lock);
    }
    wl_display_disconnect(state.display);
    return 0;
}
