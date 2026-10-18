#include "coll_iso_view.h"

#include <math.h>
#include <stddef.h>
#include <stdint.h>

typedef struct { int x, y; } Point;
typedef struct { uint32_t *pixels; int width, height, stride; } Canvas;

enum { MAX_VISUAL_EXTRUSION = 32 };

static uint32_t rgba(unsigned r, unsigned g, unsigned b) {
    return (uint32_t)(r | (g << 8) | (b << 16) | (255u << 24));
}
static int imin(int x,int y) { return x<y?x:y; }
static int imax(int x,int y) { return x>y?x:y; }

static void pixel(Canvas *canvas, int x, int y, uint32_t color) {
    if (x>=0 && x<canvas->width && y>=0 && y<canvas->height)
        canvas->pixels[(size_t)y*(size_t)canvas->stride+(size_t)x]=color;
}
static int64_t cross(Point a,Point b,Point p) {
    return (int64_t)(b.x-a.x)*(p.y-a.y) -
           (int64_t)(b.y-a.y)*(p.x-a.x);
}
static void triangle(Canvas *canvas, Point a,Point b,Point c,uint32_t color) {
    int lo_x=imax(0,imin(a.x,imin(b.x,c.x)));
    int hi_x=imin(canvas->width-1,imax(a.x,imax(b.x,c.x)));
    int lo_y=imax(0,imin(a.y,imin(b.y,c.y)));
    int hi_y=imin(canvas->height-1,imax(a.y,imax(b.y,c.y)));
    for (int y=lo_y;y<=hi_y;++y)
        for (int x=lo_x;x<=hi_x;++x) {
            Point p={x,y};
            const int64_t ab=cross(a,b,p),bc=cross(b,c,p),ca=cross(c,a,p);
            if ((ab>=0 && bc>=0 && ca>=0) ||
                (ab<=0 && bc<=0 && ca<=0))pixel(canvas,x,y,color);
        }
}
static void quad(Canvas *canvas,Point a,Point b,Point c,Point d,uint32_t color) {
    triangle(canvas,a,b,c,color);
    triangle(canvas,a,c,d,color);
}
static void line(Canvas *canvas,Point a,Point b,uint32_t color) {
    int dx=a.x>b.x?a.x-b.x:b.x-a.x;
    int dy=a.y>b.y?a.y-b.y:b.y-a.y;
    int sx=a.x<b.x?1:-1, sy=a.y<b.y?1:-1;
    int error=dx-dy;
    for (;;) {
        pixel(canvas,a.x,a.y,color);
        if (a.x==b.x && a.y==b.y) break;
        int twice=error*2;
        if (twice>-dy) {error-=dy;a.x+=sx;}
        if (twice<dx) {error+=dx;a.y+=sy;}
    }
}

static void project(int x,int y,int cx,int cy,int tile,int width,int height,
                    int visual_extrusion,Point *top,Point *right,
                    Point *bottom,Point *left) {
    const int center_x=width/2+((x-y)-(cx-cy))*tile;
    const int center_y=height/2+((x+y)-(cx+cy))*(tile/2) -
                       visual_extrusion;
    const int half_h=tile/2;
    *top=(Point){center_x,center_y-half_h};
    *right=(Point){center_x+tile,center_y};
    *bottom=(Point){center_x,center_y+half_h};
    *left=(Point){center_x-tile,center_y};
}

void foj_coll_iso_render(const FojCollGrid *grid,uint32_t *pixels,
                         int width,int height,int stride,
                         int cursor_x,int cursor_y,
                         int tile_size,int channel) {
    if (!grid||!pixels||width<=0||height<=0||stride<width||
        grid->width<1||grid->height<1||
        grid->width>FOJ_COLL_MAX_SIDE||grid->height>FOJ_COLL_MAX_SIDE||
        cursor_x<0||cursor_x>=grid->width||
        cursor_y<0||cursor_y>=grid->height||
        tile_size<4||tile_size>30||channel<0||channel>5)return;

    /* Preflight every selected scalar before touching any framebuffer pixel.
     * Work in double to avoid float overflow in max-min and normalization. */
    double minimum=0.0,maximum=1.0;
    if (channel<4) {
        minimum=INFINITY;
        maximum=-INFINITY;
        for (int y=0;y<grid->height;++y)
            for (int x=0;x<grid->width;++x) {
                const double value=(double)grid->samples[y][x][channel];
                if (!isfinite(value))return;
                if (value<minimum)minimum=value;
                if (value>maximum)maximum=value;
            }
    } else {
        for (int y=0;y<grid->height;++y)
            for (int x=0;x<grid->width;++x)
                if (grid->flags[y][x][channel-4]>1u)return;
    }

    Canvas canvas={pixels,width,height,stride};
    const uint32_t background=rgba(16,22,35);
    for (int y=0;y<height;++y)
        for (int x=0;x<width;++x)pixel(&canvas,x,y,background);

    const double range=maximum>minimum?maximum-minimum:0.0;
    for (int diagonal=0;diagonal<grid->width+grid->height-1;++diagonal)
        for (int y=0;y<grid->height;++y) {
            const int x=diagonal-y;
            if (x<0||x>=grid->width)continue;
            unsigned magnitude=0;
            uint32_t face;
            if (channel<4) {
                double norm=range>0.0?
                    ((double)grid->samples[y][x][channel]-minimum)/range:0.0;
                if (norm<0.0)norm=0.0;
                if (norm>1.0)norm=1.0;
                magnitude=(unsigned)(norm*MAX_VISUAL_EXTRUSION+0.5);
                face=rgba(36u+(unsigned)(norm*174.0),
                          84u+(unsigned)(norm*110.0),
                          179u-(unsigned)(norm*101.0));
            } else {
                const unsigned flag=grid->flags[y][x][channel-4];
                face=flag?rgba(217,97,112):rgba(53,89,103);
            }
            Point top,right,bottom,left;
            project(x,y,cursor_x,cursor_y,tile_size,width,height,
                    (int)magnitude,&top,&right,&bottom,&left);
            /* Numeric height is VISUAL magnitude, never COLL elevation.
             * Draw just the two front faces before the top diamond. */
            if (magnitude>0u) {
                const Point lower_bottom={bottom.x,bottom.y+(int)magnitude};
                const Point lower_left={left.x,left.y+(int)magnitude};
                const Point lower_right={right.x,right.y+(int)magnitude};
                quad(&canvas,left,bottom,lower_bottom,lower_left,
                     rgba(32,51,73));
                quad(&canvas,bottom,right,lower_right,lower_bottom,
                     rgba(41,63,85));
            }
            triangle(&canvas,top,right,bottom,face);
            triangle(&canvas,top,bottom,left,face);
            const uint32_t edge=rgba(21,37,53);
            line(&canvas,top,right,edge);
            line(&canvas,right,bottom,edge);
            line(&canvas,bottom,left,edge);
            line(&canvas,left,top,edge);
        }

    /* Draw selected cell last so the cursor is not occluded by later cells. */
    unsigned focus_magnitude=0u;
    if (channel<4 && range>0.0) {
        double norm=((double)grid->samples[cursor_y][cursor_x][channel]-
                     minimum)/range;
        if (norm<0.0)norm=0.0;
        if (norm>1.0)norm=1.0;
        focus_magnitude=(unsigned)(norm*MAX_VISUAL_EXTRUSION+0.5);
    }
    Point top,right,bottom,left;
    project(cursor_x,cursor_y,cursor_x,cursor_y,tile_size,width,height,
            (int)focus_magnitude,&top,&right,&bottom,&left);
    const uint32_t selected=rgba(255,224,118);
    line(&canvas,top,right,selected);
    line(&canvas,right,bottom,selected);
    line(&canvas,bottom,left,selected);
    line(&canvas,left,top,selected);

    /* Distinct channel indicator: raw columns 0-3 or flags 4-5. */
    for (int index=0;index<6;++index)
        for (int dy=0;dy<10;++dy)
            for (int dx=0;dx<12;++dx)
                pixel(&canvas,12+index*18+dx,12+dy,
                      index==channel?rgba(255,224,118):rgba(67,84,104));
}
