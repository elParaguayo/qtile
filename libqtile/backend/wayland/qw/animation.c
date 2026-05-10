#include "animation.h"
#include "util.h"
#include "wlr/types/wlr_scene.h"
#include "xdg-view.h"
#include <time.h>

static double qw_ease_out(qw_easing_func_t ease_in, double t) { return 1.0 - ease_in(1.0 - t); }

static double qw_ease_in_out(qw_easing_func_t ease_in, double t) {
    if (t < 0.5) {
        return ease_in(2.0 * t) / 2.0;
    }

    return 1.0 - ease_in(2.0 - 2.0 * t) / 2.0;
}

static double cubic_bezier(double x1, double y1, double x2, double y2, double t) {
    if (t <= 0.0)
        return 0.0;
    if (t >= 1.0)
        return 1.0;

    double u = t;
    // Newton-Raphson iteration to find the parametric value 'u' for time 't'
    for (int i = 0; i < 8; i++) {
        double om_u = 1.0 - u;      // "One Minus U"
        double om_u2 = om_u * om_u; // (1-u)^2
        double u2 = u * u;          // u^2

        // Standard Cubic Bezier: x = 3*(1-u)^2*u*x1 + 3*(1-u)*u^2*x2 + u^3
        double current_x = (3.0 * om_u2 * u * x1) + (3.0 * om_u * u2 * x2) + (u2 * u);

        // Derivative: dx/du = 3*(1-u)^2*x1 + 6*(1-u)*u*(x2-x1) + 3*u^2*(1-x2)
        double dx = (3.0 * om_u2 * x1) + (6.0 * om_u * u * (x2 - x1)) + (3.0 * u2 * (1.0 - x2));

        if (fabs(dx) < 1e-6)
            break;
        u -= (current_x - t) / dx;
    }

    // Clamp u safety
    if (u < 0.0)
        u = 0.0;
    if (u > 1.0)
        u = 1.0;

    // Calculate final y using the discovered u
    double om_u = 1.0 - u;
    double om_u2 = om_u * om_u;
    double u2 = u * u;

    // y = 3*(1-u)^2*u*y1 + 3*(1-u)*u^2*y2 + u^3
    return (3.0 * om_u2 * u * y1) + (3.0 * om_u * u2 * y2) + (u2 * u);
}

static double qw_anim_ease_in_sine(double t) { return cubic_bezier(0.12, 0, 0.39, 0, t); }

static double qw_anim_ease_out_sine(double t) { return qw_ease_out(qw_anim_ease_in_sine, t); }

static double qw_anim_ease_in_out_sine(double t) { return qw_ease_in_out(qw_anim_ease_in_sine, t); }

static double qw_anim_ease_in_cubic(double t) { return t * t * t; }

static double qw_anim_ease_out_cubic(double t) { return qw_ease_out(qw_anim_ease_in_cubic, t); }

static double qw_anim_ease_in_out_cubic(double t) {
    return qw_ease_in_out(qw_anim_ease_in_cubic, t);
}

static double qw_anim_ease_in_quint(double t) { return t * t * t * t * t; }

static double qw_anim_ease_out_quint(double t) { return qw_ease_out(qw_anim_ease_in_quint, t); }

static double qw_anim_ease_in_out_quint(double t) {
    return qw_ease_in_out(qw_anim_ease_in_quint, t);
}

static double qw_anim_ease_in_circ(double t) { return cubic_bezier(0.55, 0, 1, 0.45, t); }

static double qw_anim_ease_out_circ(double t) { return qw_ease_out(qw_anim_ease_in_circ, t); }

static double qw_anim_ease_in_out_circ(double t) { return qw_ease_in_out(qw_anim_ease_in_circ, t); }

static double qw_anim_ease_in_elastic(double t) {
    const double c4 = (2.0 * M_PI) / 3.0;

    if (t <= 0.0) {
        return 0.0;
    }

    if (t >= 1.0) {
        return 1.0;
    }

    return -exp2(10.0 * t - 10.0) * sin((t * 10.0 - 10.75) * c4);
}

static double qw_anim_ease_out_elastic(double t) { return qw_ease_out(qw_anim_ease_in_elastic, t); }

static double qw_anim_ease_in_out_elastic(double t) {
    return qw_ease_in_out(qw_anim_ease_in_elastic, t);
}

static double qw_anim_ease_in_quad(double t) { return t * t; }

static double qw_anim_ease_out_quad(double t) { return qw_ease_out(qw_anim_ease_in_quad, t); }

static double qw_anim_ease_in_out_quad(double t) { return qw_ease_in_out(qw_anim_ease_in_quad, t); }

static double qw_anim_ease_in_quart(double t) { return t * t * t * t; }

static double qw_anim_ease_out_quart(double t) { return qw_ease_out(qw_anim_ease_in_quart, t); }

static double qw_anim_ease_in_out_quart(double t) {
    return qw_ease_in_out(qw_anim_ease_in_quart, t);
}

static double qw_anim_ease_in_expo(double t) { return cubic_bezier(0.7, 0, 0.84, 0, t); }
static double qw_anim_ease_out_expo(double t) { return qw_ease_out(qw_anim_ease_in_expo, t); }

static double qw_anim_ease_in_out_expo(double t) { return qw_ease_in_out(qw_anim_ease_in_expo, t); }

static double qw_anim_ease_in_back(double t) {
    const double c1 = 1.70158;
    const double c3 = c1 + 1;

    return c3 * t * t * t - c1 * t * t;
}

static double qw_anim_ease_out_back(double t) { return qw_ease_out(qw_anim_ease_in_back, t); }

static double qw_anim_ease_in_out_back(double t) { return qw_ease_in_out(qw_anim_ease_in_back, t); }

static double qw_anim_ease_out_bounce(double t) {
    if (t >= 1.0)
        return 1.0;
    if (t <= 0.0)
        return 0.0;

    if (t < (1.0f / 2.75f)) {
        return 7.5625f * t * t;
    } else if (t < (2.0f / 2.75f)) {
        t -= (1.5f / 2.75f);
        return 7.5625f * t * t + 0.75f;
    } else if (t < (2.5f / 2.75f)) {
        t -= (2.25f / 2.75f);
        return 7.5625f * t * t + 0.9375f;
    } else {
        t -= (2.625f / 2.75f);
        return 7.5625f * t * t + 0.984375f;
    }
}

static double qw_anim_ease_in_bounce(double t) {
    // The qw_ease_out wrapper just reverses the input function
    return qw_ease_out(qw_anim_ease_out_bounce, t);
}

static double qw_anim_ease_in_out_bounce(double t) {
    return qw_ease_in_out(qw_anim_ease_in_bounce, t);
}

static qw_easing_func_t qw_anim_get_easing(qw_easing_t easing) {
    switch (easing) {
    case QW_EASE_IN_SINE:
        return qw_anim_ease_in_sine;
    case QW_EASE_OUT_SINE:
        return qw_anim_ease_out_sine;
    case QW_EASE_IN_OUT_SINE:
        return qw_anim_ease_in_out_sine;
    case QW_EASE_IN_CUBIC:
        return qw_anim_ease_in_cubic;
    case QW_EASE_OUT_CUBIC:
        return qw_anim_ease_out_cubic;
    case QW_EASE_IN_OUT_CUBIC:
        return qw_anim_ease_in_out_cubic;
    case QW_EASE_IN_QUINT:
        return qw_anim_ease_in_quint;
    case QW_EASE_OUT_QUINT:
        return qw_anim_ease_out_quint;
    case QW_EASE_IN_OUT_QUINT:
        return qw_anim_ease_in_out_quint;
    case QW_EASE_IN_CIRC:
        return qw_anim_ease_in_circ;
    case QW_EASE_OUT_CIRC:
        return qw_anim_ease_out_circ;
    case QW_EASE_IN_OUT_CIRC:
        return qw_anim_ease_in_out_circ;
    case QW_EASE_IN_ELASTIC:
        return qw_anim_ease_in_elastic;
    case QW_EASE_OUT_ELASTIC:
        return qw_anim_ease_out_elastic;
    case QW_EASE_IN_OUT_ELASTIC:
        return qw_anim_ease_in_out_elastic;
    case QW_EASE_IN_QUAD:
        return qw_anim_ease_in_quad;
    case QW_EASE_OUT_QUAD:
        return qw_anim_ease_out_quad;
    case QW_EASE_IN_OUT_QUAD:
        return qw_anim_ease_in_out_quad;
    case QW_EASE_IN_QUART:
        return qw_anim_ease_in_quart;
    case QW_EASE_OUT_QUART:
        return qw_anim_ease_out_quart;
    case QW_EASE_IN_OUT_QUART:
        return qw_anim_ease_in_out_quart;
    case QW_EASE_IN_EXPO:
        return qw_anim_ease_in_expo;
    case QW_EASE_OUT_EXPO:
        return qw_anim_ease_out_expo;
    case QW_EASE_IN_OUT_EXPO:
        return qw_anim_ease_in_out_expo;
    case QW_EASE_IN_BACK:
        return qw_anim_ease_in_back;
    case QW_EASE_OUT_BACK:
        return qw_anim_ease_out_back;
    case QW_EASE_IN_OUT_BACK:
        return qw_anim_ease_in_out_back;
    case QW_EASE_IN_BOUNCE:
        return qw_anim_ease_in_bounce;
    case QW_EASE_OUT_BOUNCE:
        return qw_anim_ease_out_bounce;
    case QW_EASE_IN_OUT_BOUNCE:
        return qw_anim_ease_in_out_bounce;
    default:
        return qw_anim_ease_in_out_cubic;
    }
}

static inline double qw_anim_lerp(double start, double end, double amount) {
    return start + amount * (end - start);
}

static void qw_anim_update_position(Vec2 start, Vec2 end, double elapsed_ms, double duration_ms,
                                    Vec2 *current) {
    double t = elapsed_ms / duration_ms;
    double eased_t = qw_anim_ease_in_out_bounce(t);

    current->x = qw_anim_lerp(start.x, end.x, eased_t);
    current->y = qw_anim_lerp(start.y, end.y, eased_t);
}

static void qw_anim_apply_opacity(struct qw_view *view, float opacity) {
    float view_opacity = view->opacity;
    qw_view_set_opacity(view, opacity * view_opacity);
    view->opacity = view_opacity;
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

    qw_easing_func_t easing = qw_anim_get_easing(anim->easing);

    c_state.eased_t = easing(c_state.t);

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
    if (!base->anim.active || !base->content_tree || !base->anim.needs_repos)
        return;

    qw_view_set_borders_visible(base, false);

    t_state c_state = qw_anim_get_state(&base->anim);

    /*
     * FINAL TRANSFORM STATE
     */
    int final_x = base->x;
    int final_y = base->y;

    int final_w = base->width;
    int final_h = base->height;

    /*
     * POSITION ANIMATION
     */
    if (base->anim.flags & QW_ANIM_POSITION) {

        final_x =
            (int)qw_anim_lerp(base->anim.start_pos.x, base->anim.target_pos.x, c_state.eased_t);

        final_y =
            (int)qw_anim_lerp(base->anim.start_pos.y, base->anim.target_pos.y, c_state.eased_t);
    } else {
        /*
         * If no position animation is active,
         * use target position as the stable rect.
         *
         * This is important for centered scaling.
         */
        final_x = base->anim.target_pos.x;
        final_y = base->anim.target_pos.y;
    }

    /*
     * SIZE ANIMATION
     */
    if (base->anim.flags & QW_ANIM_SIZE) {

        final_w =
            (int)qw_anim_lerp(base->anim.start_width, base->anim.target_width, c_state.eased_t);

        final_h =
            (int)qw_anim_lerp(base->anim.start_height, base->anim.target_height, c_state.eased_t);

        /*
         * ORIGIN COMPENSATION
         *
         * Keep scaling centered around the chosen origin.
         *
         * IMPORTANT:
         * Compensation must be relative to the TARGET size,
         * not the start size.
         */
        double dx = (base->anim.target_width - final_w) * base->anim.size_origin_x;

        double dy = (base->anim.target_height - final_h) * base->anim.size_origin_y;

        final_x += (int)dx;
        final_y += (int)dy;

        qw_anim_apply_view_scale(base, final_w, final_h);
    }

    /*
     * APPLY FINAL POSITION
     */
    wlr_scene_node_set_position(&base->content_tree->node, final_x, final_y);

    /*
     * OPACITY ANIMATION
     */
    if (base->anim.flags & QW_ANIM_OPACITY) {

        float opacity = (float)qw_anim_lerp(base->anim.start_opacity, base->anim.target_opacity,
                                            c_state.eased_t);

        if (opacity < 0.0f)
            opacity = 0.0f;
        else if (opacity > 1.0f)
            opacity = 1.0f;

        qw_anim_apply_opacity(base, opacity);
    }

    /*
     * FINISH
     */
    if (c_state.elapsed >= base->anim.duration) {

        /*
         * Final real position
         *
         * IMPORTANT:
         * No resize-origin compensation here.
         * Compensation is only for temporary scaling.
         */
        int end_x = base->x;
        int end_y = base->y;

        if (base->anim.flags & QW_ANIM_POSITION) {
            end_x = base->anim.target_pos.x;
            end_y = base->anim.target_pos.y;
        } else {
            end_x = base->anim.target_pos.x;
            end_y = base->anim.target_pos.y;
        }

        wlr_scene_node_set_position(&base->content_tree->node, end_x, end_y);
        qw_view_set_borders_visible(base, true);
        /*
         * FINAL SIZE
         */
        if (base->anim.flags & QW_ANIM_SIZE) {

            /*
             * Remove temporary compositor scaling
             */
            // qw_anim_apply_view_scale(base, 0, 0);
            qw_anim_apply_view_scale(base, base->anim.target_width, base->anim.target_height);

            /*
             * Apply real window size
             */
            if (base->on_anim_complete)
                base->on_anim_complete(base);

            qw_view_resize_ftl_output_tracking_buffer(base, base->anim.target_width,
                                                      base->anim.target_height);
        }

        /*
         * FINAL OPACITY
         */
        if (base->anim.flags & QW_ANIM_OPACITY) {

            qw_anim_apply_opacity(base, base->anim.target_opacity);
        }

        base->anim.active = false;
    }
}

void qw_anim_begin(qw_anim *anim, int x, int y, int w, int h, int duration, qw_easing_t easing,
                   bool needs_repos) {
    anim->active = true;

    anim->target_pos = (Vec2){.x = x, .y = y};

    anim->target_width = w;
    anim->target_height = h;

    anim->needs_repos = false;

    anim->flags = QW_ANIM_NONE;

    anim->duration = duration;
    anim->start_time = qw_anim_get_time_ms();

    anim->easing = easing;

    anim->needs_repos = needs_repos;
}

void qw_anim_set_position(qw_anim *anim, struct qw_view *view, int x, int y) {
    anim->flags |= QW_ANIM_POSITION;

    anim->start_pos = (Vec2){
        .x = view->x,
        .y = view->y,
    };

    anim->target_pos = (Vec2){
        .x = x,
        .y = y,
    };
}

void qw_anim_set_size(qw_anim *anim, int start_w, int start_h, int end_w, int end_h, float origin_x,
                      float origin_y) {
    anim->flags |= QW_ANIM_SIZE;

    anim->start_width = start_w;
    anim->start_height = start_h;

    anim->target_width = end_w;
    anim->target_height = end_h;

    anim->size_origin_x = origin_x;
    anim->size_origin_y = origin_y;
}

void qw_anim_set_opacity(qw_anim *anim, float start, float end) {
    anim->flags |= QW_ANIM_OPACITY;

    anim->start_opacity = start;
    anim->target_opacity = end;
}
