/* All sample OBJ files in this test are generated in memory. */
#include "obj_wireframe.h"

#include <assert.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static FILE *sample(const char *content) {
    FILE *f = tmpfile();
    assert(f);
    size_t n = strlen(content);
    assert(fwrite(content,1,n,f)==n);
    rewind(f);
    return f;
}

static void test_triangle_mesh_and_camera(void) {
    static const char source[] =
        "# synthetic mesh\n"
        "o invented_shape\n"
        "v -1 0 0\n"
        "v 1 0 0\n"
        "v 0 2 0\n"
        "vt 0 0\nvt 1 0\nvt 0.5 1\n"
        "vn 0 0 1\n"
        "f 1/1/1 2/2/1 3/3/1\n";
    FojObjMesh *mesh = malloc(sizeof(*mesh));
    assert(mesh);
    FILE *f = sample(source);
    assert(foj_obj_read(f,mesh)==0);
    fclose(f);
    assert(mesh->vertex_count==3 && mesh->triangle_count==1);
    assert(mesh->faces[0].a==0 && mesh->faces[0].b==1 && mesh->faces[0].c==2);
    assert(mesh->center[1]==1.0f);
    assert(mesh->radius==2.0f);

    enum { W=240,H=180,S=252 };
    uint32_t *pixels = malloc(sizeof(*pixels)*H*S);
    assert(pixels);
    for (int i=0;i<H*S;++i) pixels[i]=UINT32_C(0x01234567);
    foj_obj_wireframe(mesh,pixels,W,H,S,0,0,1);
    size_t count=0;
    for (int y=0;y<H;++y) {
        for (int x=0;x<W;++x)
            if (pixels[y*S+x]==UINT32_C(0xffbde4da)) ++count;
        for (int x=W;x<S;++x)
            assert(pixels[y*S+x]==UINT32_C(0x01234567));
    }
    assert(count>40);
    foj_obj_wireframe(mesh,pixels,W,H,S,0.5f,0.2f,1.5f);
    assert(pixels[0]==UINT32_C(0xff181c25));
    free(pixels);
    free(mesh);
}

static void test_input_rejections(void) {
    FojObjMesh *mesh=malloc(sizeof(*mesh));
    assert(mesh);
    FILE *f = sample("v 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 4\n");
    assert(foj_obj_read(f,mesh)!=0);fclose(f);
    f=sample("v 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3 1\n");
    assert(foj_obj_read(f,mesh)!=0);fclose(f);
    f=sample("v 0 0 0\nv nan 0 0\nv 0 1 0\nf 1 2 3\n");
    assert(foj_obj_read(f,mesh)!=0);fclose(f);
    f=sample("v 0 0 0\nv 1 0 0\nv 0 1 0\nf -1 2 3\n");
    assert(foj_obj_read(f,mesh)!=0);fclose(f);
    f=sample("v 0 0 0\nv 1 0 0\nv 0 1 0\n");
    assert(foj_obj_read(f,mesh)!=0);fclose(f);
    f=sample("this-is-not-obj\n");
    assert(foj_obj_read(f,mesh)!=0);fclose(f);
    free(mesh);
}

static void test_synthetic_fallback(void) {
    FojObjMesh *mesh=malloc(sizeof(*mesh));
    assert(mesh);
    foj_obj_synthetic_cube(mesh);
    assert(mesh->vertex_count==8 && mesh->triangle_count==12);
    assert(mesh->radius==2.0f);
    free(mesh);
}

int main(void) {
    test_triangle_mesh_and_camera();
    test_input_rejections();
    test_synthetic_fallback();
    puts("OBJ native wireframe: synthetic tests passed");
    return 0;
}
