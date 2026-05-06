#include "animation.h"
#include "util.h"
#include "wlr/types/wlr_scene.h"
#include "xdg-view.h"
#include <time.h>

static double qw_anim_ease_out_quint(double t) {
    if (t < 0.0)
        return 0.0;
    if (t > 1.0)
        return 1.0;

    double inv_t = 1.0 - t;
    return 1.0 - (inv_t * inv_t * inv_t * inv_t * inv_t);
}

static inline double lerp(double start, double end, double amount) {
    return start + amount * (end - start);
}

static void qw_anim_update_position(Vec2 start, Vec2 end, double elapsed_ms, double duration_ms,
                                    Vec2 *current) {
    double t = elapsed_ms / duration_ms;
    double eased_t = qw_anim_ease_out_quint(t);

    current->x = lerp(start.x, end.x, eased_t);
    current->y = lerp(start.y, end.y, eased_t);
}

long qw_anim_get_time_ms() {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec * 1000 + ts.tv_nsec / 1000000;
}

static void qw_anim_set_buffer_render_size(struct wlr_scene_buffer *buffer, int sx, int sy,
                                           void *user_data) {
    UNUSED(sx);
    UNUSED(sy);

    Vec2 *size = user_data;
    if (size->x <= 0 || size->y <= 0) {
        wlr_scene_buffer_set_dest_size(buffer, 0, 0);
    } else {
        wlr_scene_buffer_set_dest_size(buffer, (int)size->x, (int)size->y);
    }
    wlr_scene_buffer_set_filter_mode(buffer, WLR_SCALE_FILTER_BILINEAR);
}

static void qw_anim_apply_view_scale(struct qw_view *base, int w, int h) {
    Vec2 size = {.x = w, .y = h};
    wlr_scene_node_for_each_buffer(&base->content_tree->node, qw_anim_set_buffer_render_size,
                                   &size);
}

static t_state qw_anim_get_state(qw_anim *anim) {
    t_state c_state = {};

    c_state.now = qw_anim_get_time_ms();
    c_state.elapsed = (double)(c_state.now - anim->start_time);
    c_state.t = c_state.elapsed / anim->duration;
    if (c_state.t > 1.0)
        c_state.t = 1.0;
    c_state.eased_t = qw_anim_ease_out_quint(c_state.t);

    return c_state;
}

void qw_anim_fill(qw_anim *anim, struct qw_view *base, int x, int y, int w, int h, int duration,
                  bool repos) {
    anim->start_pos = (Vec2){base->x, base->y};
    anim->target_pos = (Vec2){x, y};
    anim->start_time = qw_anim_get_time_ms();
    anim->start_width = base->width;
    anim->start_height = base->height;
    anim->target_width = w;
    anim->target_height = h;
    anim->duration = (double)duration;
    anim->active = true;
    anim->needs_repos = repos;
}

void qw_anim_step(struct qw_view *base) {
    if (!base->anim.active || !base->content_tree)
        return;

    t_state c_state = qw_anim_get_state(&base->anim);

    Vec2 curr;
    qw_anim_update_position(base->anim.start_pos, base->anim.target_pos, c_state.elapsed,
                            base->anim.duration, &curr);
    wlr_scene_node_set_position(&base->content_tree->node, (int)curr.x, (int)curr.y);

    if (base->anim.needs_repos) {
        int cur_w = (int)lerp(base->anim.start_width, base->anim.target_width, c_state.eased_t);
        int cur_h = (int)lerp(base->anim.start_height, base->anim.target_height, c_state.eased_t);
        qw_anim_apply_view_scale(base, cur_w, cur_h);
    }

    if (c_state.elapsed >= base->anim.duration) {
        wlr_scene_node_set_position(&base->content_tree->node, base->anim.target_pos.x,
                                    base->anim.target_pos.y);

        if (base->anim.needs_repos) {
            qw_anim_apply_view_scale(base, 0, 0);
            base->on_anim_complete(base);
            qw_view_resize_ftl_output_tracking_buffer(base, base->anim.target_width,
                                                      base->anim.target_height);
        }

        base->anim.active = false;
        return;
    }
}
