#!/usr/bin/env python3
"""Exercise the real camera-relative world-matrix translation against a
float24 rounding simulation.

Regression test for: PICA200 vertex-shader arithmetic and uniforms are
float24 (16-bit mantissa). Uploading an absolute LCS world-space position
(world spans ~+-2000 units) as u_world's translation quantizes to 15-31mm
per vertex; peds re-skin every frame, so the rounding drifts continuously
-> visible PS1-style jitter. The fix folds the camera position into
u_world's translation on the CPU (float32) and zeroes u_view's translation,
so the float24 uniform only ever holds a small camera-relative delta.

This test slices the actual translation-handling lines out of
setWorldMatrix() and beginUpdate() in 3dsdevice.cpp (not hand-retyped, so
the test fails if someone reverts the fix), compiles them into
cpp/vertex_precision.cpp alongside a float24 rounding-simulation helper, and
asserts the quantization error is large for an absolute coordinate but small
for a camera-relative one.
"""
import unittest

from cpptest import between, compile_and_run, extract_function, harness, read_source

CAMERA_CAPTURE = 'cameraWorldOrigin = cam->getFrame()->getLTM()->pos;'


class VertexPrecision(unittest.TestCase):
    def test_world_translation_is_camera_relative_and_low_error(self):
        source = read_source('common/librw/src/3ds/3dsdevice.cpp')

        set_world_matrix = extract_function(source, 'setWorldMatrix(Matrix *mat, float positionScale)')
        world_translation = between(
            set_world_matrix,
            'world.r[0].w = raw.pos.x - cameraWorldOrigin.x * raw.posw;',
            'world.r[2].w = raw.pos.z - cameraWorldOrigin.z * raw.posw;', include_end=True)

        begin_update = extract_function(source, 'beginUpdate(Camera *cam)')
        self.assertIn(CAMERA_CAPTURE, begin_update)
        view_translation = between(
            begin_update,
            'view.r[0].w = 0.0f;',
            'view.r[3].w =  1.0f;', include_end=True)

        compile_and_run(harness('vertex_precision.cpp',
                                WORLD_TRANSLATION=world_translation,
                                CAMERA_CAPTURE=CAMERA_CAPTURE,
                                VIEW_TRANSLATION=view_translation))


if __name__ == '__main__':
    unittest.main()
