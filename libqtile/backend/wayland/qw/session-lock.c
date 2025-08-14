#include "session-lock.h"

void qw_session_lock_destroy(qw_session_lock *session_lock, int unlock) {
    // wlr_seat_keyboard_notify_clear_focus(seat);
    // if ((locked = !unlock))
    // 	goto destroy;

    // wlr_scene_node_set_enabled(&locked_bg->node, 0);

    // focusclient(focustop(selmon), 0);
    // motionnotify(0, NULL, 0, 0, 0, 0);
    wlr_log(WLR_ERROR, "Destroying lock.");

    wl_list_remove(&session_lock->new_surface.link);
    wl_list_remove(&session_lock->unlock.link);
    wl_list_remove(&session_lock->destroy.link);

    // wlr_scene_node_destroy(&lock->scene->node);
    session_lock->server->lock = NULL;
    free(session_lock);
}

void qw_session_lock_handle_destroy(struct wl_listener *listener, void *data) {
    qw_session_lock *lock = wl_container_of(listener, lock, destroy);
    qw_session_lock_destroy(lock, 0);
}

void qw_session_lock_handle_new_surface(struct wl_listener *listener, void *data) {}

void qw_session_lock_handle_unlock(struct wl_listener *listener, void *data) {}

void qw_session_lock_handle_new(struct wl_listener *listener, void *data) {
    struct qw_server *server = wl_container_of(listener, server, new_lock);
    struct wlr_session_lock_v1 *session_lock = data;

    wlr_log(WLR_ERROR, "SESSION LOCK - HANDLE NEW LOCK");

    if (server->locked) {
        // Server is already locked
        wlr_session_lock_v1_destroy(session_lock);
        return;
    }

    // Block focus of other windows

    // Stop input in other windows

    qw_session_lock *lock;
    // lock = session_lock->data = ecalloc(1, sizeof(*lock));
    // wlr_scene_node_set_enabled(&locked_bg->node, 1);

    // // focusclient(NULL, 0);

    // lock->scene = wlr_scene_tree_create(layers[LyrBlock]);
    lock->server = server;
    lock->lock = session_lock;
    server->lock = session_lock;
    server->locked = true;

    lock->new_surface.notify = qw_session_lock_handle_new_surface;
    wl_signal_add(&session_lock->events.new_surface, &lock->new_surface);

    lock->new_surface.notify = qw_session_lock_handle_destroy;
    wl_signal_add(&session_lock->events.destroy, &lock->destroy);

    lock->new_surface.notify = qw_session_lock_handle_unlock;
    wl_signal_add(&session_lock->events.unlock, &lock->unlock);

    wlr_session_lock_v1_send_locked(session_lock);
}
