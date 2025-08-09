#include "view.h"
#include "server.h"
#include <stdlib.h>
#include <wlr/util/log.h>

// Frees all border rectangles and their associated scene nodes of the view.
// Checks if borders exist, then destroys each of the 4 border scene nodes per border set.
// Finally frees the allocated borders array.
void qw_view_cleanup_borders(struct qw_view *view) {
    if (!view->borders) {
        return;
    }
    for (int i = 0; i < view->bn; ++i) {
        for (int j = 0; j < 4; ++j) {
            wlr_scene_node_destroy(&view->borders[i][j]->node);
        }
    }
    free(view->borders);
}

void qw_view_reparent(struct qw_view *view, int layer) {
    wlr_scene_node_reparent(&view->content_tree->node, view->server->scene_windows_layers[layer]);
    view->layer = layer;
}

void qw_view_raise_to_top(struct qw_view *view) {
    wlr_scene_node_raise_to_top(&view->content_tree->node);
}
void qw_view_lower_to_bottom(struct qw_view *view) {
    wlr_scene_node_lower_to_bottom(&view->content_tree->node);
}

void qw_view_move_up(struct qw_view *view) {
    // the rightmost sibling in the tree
    // is the upper one
    // so we need to get the window to the right (x)
    // of this window and place this window above x
    struct wlr_scene_node *next_sibling = NULL;
    bool found_child = false;
    struct wlr_scene_node *child;
    wl_list_for_each(child, &view->server->scene_windows_tree[view->layer].children, link) {
        if (child == &view->content_tree->node) {
            found_child = true;
        } else if (found_child) {
            next_sibling = child;
            break;
        }
    }
    if (next_sibling) {
        wlr_scene_node_place_above(&view->content_tree->node, next_sibling);
    }
}

void qw_view_move_down(struct qw_view *view) {
    // the leftmost sibling in the tree
    // is the bottom one
    // so we need to get the window to the left (x)
    // of this window and place this window below x
    struct wlr_scene_node *prev_sibling = NULL;
    struct wlr_scene_node *child;
    wl_list_for_each(child, &view->server->scene_windows_tree[view->layer].children, link) {
        if (child == &view->content_tree->node) {
            break;
        }
        prev_sibling = child;
    }
    if (prev_sibling) {
        wlr_scene_node_place_above(&view->content_tree->node, prev_sibling);
    }
}

bool qw_view_is_visible(struct qw_view *view) { return view->content_tree->node.enabled; }

// Creates and paints multiple border layers around the view content.
// colors: array of RGBA colors for each border layer (each is 4 floats).
// width: total border width in pixels.
// n: number of border layers to draw.
void qw_view_paint_borders(struct qw_view *view, float (*colors)[4], int width, int n) {
    wlr_log(WLR_ERROR, "paint_borders: entry view=%p width=%d n=%d colors=%p", (void *)view, width,
            n, (void *)colors);
    if (!view) {
        wlr_log(WLR_ERROR, "view is null\n");
        return;
    }

    wlr_log(WLR_ERROR, "About to get tree node\n");
    struct wlr_scene_node *tree_node = view->get_tree_node(view);
    wlr_log(WLR_ERROR, "paint_borders: tree_node=%p content_tree=%p", (void *)tree_node,
            (void *)view->content_tree);
    if (!tree_node || !view->content_tree) {
        wlr_log(WLR_ERROR, "paint_borders: abort - missing tree_node or content_tree");
        return;
    }

    wlr_log(WLR_ERROR, "paint_borders: calling cleanup_borders for view=%p borders=%p bn=%d",
            (void *)view, (void *)view->borders, view->bn);

    qw_view_cleanup_borders(view);

    wlr_log(WLR_ERROR, "paint_borders: returned from cleanup_borders");
    view->bn = n;

    /* allocate pointer-array: n rows of 4 pointers each */
    view->borders = malloc(n * sizeof(struct wlr_scene_rect *[4]));
    if (!view->borders) {
        wlr_log(WLR_ERROR, "paint_borders: malloc failed for n=%d", n);
        return;
    }

    /* init to NULL */
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < 4; ++j)
            view->borders[i][j] = NULL;
    }

    /* quick sanity checks */
    if (!colors) {
        wlr_log(WLR_ERROR, "paint_borders: colors == NULL (will abort)");
        free(view->borders);
        view->borders = NULL;
        view->bn = 0;
        return;
    }

    wlr_scene_node_set_position(tree_node, width, width);
    int outer_w = view->width + width * 2;
    int outer_h = view->height + width * 2;
    wlr_log(WLR_ERROR, "paint_borders: view->width=%d view->height=%d outer_w=%d outer_h=%d",
            view->width, view->height, outer_w, outer_h);

    int coord = 0;
    for (int i = 0; i < n; ++i) {
        int bw = width / n + (i < (width % n) ? 1 : 0);
        wlr_log(WLR_ERROR, "paint_borders: layer %d bw=%d coord=%d", i, bw, coord);

        struct border_pairs {
            int x, y, w, h;
        } pairs[4] = {{coord, coord, outer_w - coord * 2, bw},
                      {outer_w - bw - coord, bw + coord, bw, outer_h - bw * 2 - coord * 2},
                      {coord, outer_h - bw - coord, outer_w - coord * 2, bw},
                      {coord, bw + coord, bw, outer_h - bw * 2 - coord * 2}};

        for (int j = 0; j < 4; ++j) {
            int pw = pairs[j].w;
            int ph = pairs[j].h;
            wlr_log(WLR_ERROR,
                    "paint_borders: creating rect i=%d j=%d x=%d y=%d w=%d h=%d color_ptr=%p", i, j,
                    pairs[j].x, pairs[j].y, pw, ph, (void *)&colors[i]);

            /* Guard: skip zero/negative sizes */
            if (pw <= 0 || ph <= 0) {
                wlr_log(WLR_ERROR,
                        "paint_borders: skip create rect due to non-positive size w=%d h=%d", pw,
                        ph);
                view->borders[i][j] = NULL;
                continue;
            }

            /* Create rect and immediately log pointer returned */
            struct wlr_scene_rect *rect = NULL;
            /* Wrap creation in a try to localize crash — if this line crashes, note last log above
             */
            rect = wlr_scene_rect_create(view->content_tree, pw, ph, colors[i]);
            wlr_log(WLR_ERROR, "paint_borders: wlr_scene_rect_create returned %p for i=%d j=%d",
                    (void *)rect, i, j);

            if (!rect) {
                wlr_log(WLR_ERROR, "paint_borders: rect creation returned NULL for i=%d j=%d", i,
                        j);
                view->borders[i][j] = NULL;
                continue;
            }

            rect->node.data = view;
            wlr_scene_node_set_position(&rect->node, pairs[j].x, pairs[j].y);
            view->borders[i][j] = rect;
            wlr_log(WLR_ERROR, "paint_borders: rect stored view->borders[%d][%d]=%p", i, j,
                    (void *)rect);
        }
        coord += bw;
    }

    wlr_scene_node_raise_to_top(tree_node);
    wlr_log(WLR_ERROR, "paint_borders: done normally");
}
