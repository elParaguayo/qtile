#ifndef ANIMATION_H
#define ANIMATION_H

#include <stdbool.h>

struct qw_xdg_view;
struct qw_xwayland_view;
struct qw_view;

typedef struct {
    int x, y;
} Vec2;

typedef struct {
    bool active;
    bool needs_repos;
    long start_time;
    Vec2 start_pos;
    Vec2 target_pos;
    int start_width;
    int start_height;
    int target_width;
    int target_height;
    double duration;
} qw_anim;

// Capture time states for the animation
typedef struct {
    long now;
    double elapsed;
    double t;
    double eased_t;
} t_state;

long qw_anim_get_time_ms();
void qw_anim_step(struct qw_view *base);
void qw_anim_fill(qw_anim *anim, struct qw_view *base, int x, int y, int w, int h, int duration,
                  bool repos);

#endif
