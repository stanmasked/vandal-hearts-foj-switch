#include "../gpu/stage345_bmodel_mesh_bridge.h"

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

static int audit_file(const char *path) {
    FILE *file = NULL;
    uint8_t *bytes = NULL;
    long length;
    size_t read_count;
    FojStage345BmodelMesh mesh = {0};
    FojStage345Status status;
    size_t triangles = 0u, skinned_vertices = 0u, influence_records = 0u;

    file = fopen(path, "rb");
    if (file == NULL) {
        puts("{\"ok\":false,\"reason\":\"input_open\"}");
        return 2;
    }
    if (fseek(file, 0L, SEEK_END) != 0 || (length = ftell(file)) <= 0L ||
        (unsigned long)length > FOJ_STAGE343_MAX_MODEL_BYTES ||
        fseek(file, 0L, SEEK_SET) != 0) {
        fclose(file);
        puts("{\"ok\":false,\"reason\":\"input_size\"}");
        return 2;
    }
    bytes = (uint8_t *)malloc((size_t)length);
    if (bytes == NULL) {
        fclose(file);
        puts("{\"ok\":false,\"reason\":\"allocation\"}");
        return 2;
    }
    read_count = fread(bytes, 1u, (size_t)length, file);
    if (fclose(file) != 0 || read_count != (size_t)length) {
        free(bytes);
        puts("{\"ok\":false,\"reason\":\"input_read\"}");
        return 2;
    }

    status = foj_stage345_bmodel_to_rigmesh(bytes, (size_t)length, &mesh);
    if (status != FOJ_STAGE345_OK || !foj_stage345_mesh_integrity_ready(&mesh)) {
        printf("{\"ok\":false,\"status\":%u}\n",
               (unsigned)(status == FOJ_STAGE345_OK ? 255u : (unsigned)status));
        foj_stage345_bmodel_mesh_free(&mesh);
        free(bytes);
        return 1;
    }
    for (size_t i = 0u; i < mesh.mesh.section_count; ++i)
        triangles += mesh.mesh.sections[i].vertex_count / 3u;
    for (size_t i = 0u; i < mesh.mesh.vertex_count; ++i) {
        if (mesh.mesh.vertices[i].influence_count != 0u)
            ++skinned_vertices;
        influence_records += mesh.mesh.vertices[i].influence_count;
    }
    printf("{\"ok\":true,\"integrity_ready\":true,"
           "\"sections\":%zu,\"vertices\":%zu,\"triangles\":%zu,"
           "\"bones\":%zu,\"materials\":%zu,\"texture_references\":%zu,"
           "\"skinned_vertices\":%zu,\"influence_records\":%zu}\n",
           mesh.mesh.section_count, mesh.mesh.vertex_count, triangles,
           mesh.mesh.bone_count, mesh.material_count, mesh.texture_count,
           skinned_vertices, influence_records);
    foj_stage345_bmodel_mesh_free(&mesh);
    free(bytes);
    return 0;
}

int main(int argc, char **argv) {
    if (argc != 2) {
        puts("{\"ok\":false,\"reason\":\"one_input_path_required\"}");
        return 64;
    }
    return audit_file(argv[1]);
}
