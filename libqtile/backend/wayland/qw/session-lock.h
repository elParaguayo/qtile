#ifndef SESSIONLOCK_H
#define SESSIONLOCK_H

#include <wayland-server-core.h>
#include <wlr/types/wlr_session_lock_v1.h>

struct qw_server;

// Session lock
struct qw_session_lock {
    struct qw_server *server;
    struct wlr_scene_tree *scene;
    struct wlr_session_lock_v1 *lock;
    struct wl_listener new_surface;
    struct wl_listener unlock;
    struct wl_listener destroy;
};

// Function when server receives new session lock request
static void qw_session_lock_handle_new(struct wl_listener *listener, void *data);

#endif // SESSIONLOCK_H
