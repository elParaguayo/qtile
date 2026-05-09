#ifndef ANIMATION_H
#define ANIMATION_H

#include <stdbool.h>
#include <stdint.h>

struct qw_xdg_view;
struct qw_xwayland_view;
struct qw_view;

typedef enum {
    QW_EASE_IN_SINE,
    QW_EASE_OUT_SINE,
    QW_EASE_IN_OUT_SINE,
    QW_EASE_IN_CUBIC,
    QW_EASE_OUT_CUBIC,
    QW_EASE_IN_OUT_CUBIC,
    QW_EASE_IN_QUINT,
    QW_EASE_OUT_QUINT,
    QW_EASE_IN_OUT_QUINT,
    QW_EASE_IN_CIRC,
    QW_EASE_OUT_CIRC,
    QW_EASE_IN_OUT_CIRC,
    QW_EASE_IN_ELASTIC,
    QW_EASE_OUT_ELASTIC,
    QW_EASE_IN_OUT_ELASTIC,
    QW_EASE_IN_QUAD,
    QW_EASE_OUT_QUAD,
    QW_EASE_IN_OUT_QUAD,
    QW_EASE_IN_QUART,
    QW_EASE_OUT_QUART,
    QW_EASE_IN_OUT_QUART,
    QW_EASE_IN_EXPO,
    QW_EASE_OUT_EXPO,
    QW_EASE_IN_OUT_EXPO,
    QW_EASE_IN_BACK,
    QW_EASE_OUT_BACK,
    QW_EASE_IN_OUT_BACK,
    QW_EASE_IN_BOUNCE,
    QW_EASE_OUT_BOUNCE,
    QW_EASE_IN_OUT_BOUNCE,
} qw_easing_t;

typedef enum {
    QW_ANIM_NONE = 0,
    QW_ANIM_POSITION = 1 << 0,
    QW_ANIM_SIZE = 1 << 1,
    QW_ANIM_OPACITY = 1 << 2,
} qw_anim_flags_t;

typedef struct {
    int x, y;
} Vec2;

typedef struct {
    bool active;
    bool needs_repos;

    uint32_t flags;

    long start_time;
    double duration;

    Vec2 start_pos;
    Vec2 target_pos;

    int start_width;
    int start_height;

    int target_width;
    int target_height;

    float start_opacity;
    float target_opacity;

    qw_easing_t easing;
} qw_anim;

// Capture time states for the animation
typedef struct {
    long now;
    double elapsed;
    double t;
    double eased_t;
} t_state;

typedef double (*qw_easing_func_t)(double t);

long qw_anim_get_time_ms();
void qw_anim_step(struct qw_view *base);
void qw_anim_fill(qw_anim *anim, struct qw_view *base, int x, int y, int w, int h, int duration,
                  bool repos);

void qw_anim_begin(qw_anim *anim, int duration, qw_easing_t easing);
void qw_anim_set_position(qw_anim *anim, struct qw_view *view, int x, int y);
void qw_anim_set_size(qw_anim *anim, struct qw_view *view, int start_w, int start_h, int target_w,
                      int target_h, bool repos);
void qw_anim_set_opacity(qw_anim *anim, float start, float end);

#endif
