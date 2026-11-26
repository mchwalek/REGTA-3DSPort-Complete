#!/usr/bin/env python3
"""Regression test: the Shoreside tunnel lights keep their glows, not their mesh.

The Shoreside Vale northern tunnel has three light models in suburb.ipl
(Trans_lights01-03). PS2 GAME.DTZ keeps these instances as buildings and
gives them the same 30 coronastar glows as suburb.ide, but SUBURB.LVZ has no
mesh for them. On 3DS the mesh drew as a black or grey slab between the
tunnel walls. Skipping the instances at load time removed the slab and the
glows together.

Extracts the real IsLCSMeshlessLightModel from Renderer.cpp and compiles it
into cpp/tunnel_light_meshes.cpp, then checks that every 3DS draw site uses
the mesh gate and that the loader keeps the instances.
"""
import unittest

from cpptest import between, compile_and_run, extract_function, harness, read_source

RENDERER = "stories/src/renderer/Renderer.cpp"


class TestTunnelLightMeshes(unittest.TestCase):
    def test_only_the_tunnel_light_models_are_meshless(self):
        func = between(read_source(RENDERER), "static int gLCSMeshlessLightModels[",
                       "\nbool\nCRenderer::ShouldRenderEntityMesh3DS")
        compile_and_run(harness("tunnel_light_meshes.cpp", FUNCTION=func))

    def test_init_resolves_the_tunnel_light_models(self):
        init = extract_function(read_source(RENDERER), "void\nCRenderer::Init(void)")
        for name in ("Trans_lights01", "Trans_lights02", "Trans_lights03"):
            self.assertIn(f'"{name}"', init)

    def test_mesh_gate_keeps_the_window_light_rule(self):
        gate = extract_function(read_source(RENDERER), "bool\nCRenderer::ShouldRenderEntityMesh3DS(CEntity *ent)")
        self.assertIn("IsLCSMeshlessLightModel(", gate)
        self.assertIn("ShouldRenderAttachedWindowLights(ent)", gate)

    def test_every_draw_site_uses_the_mesh_gate(self):
        sites = {
            RENDERER: 3,  # gate definition, RenderOneNonRoad, RenderOneBuilding
            "stories/src/rw/VisibilityPlugins.cpp": 1,  # RenderFadingEntities
        }
        for path, count in sites.items():
            source = read_source(path)
            self.assertEqual(source.count("ShouldRenderEntityMesh3DS("), count, path)
        # The window light rule is now reached only through the mesh gate.
        self.assertEqual(read_source("stories/src/rw/VisibilityPlugins.cpp").count("ShouldRenderAttachedWindowLights("), 0)
        self.assertEqual(read_source(RENDERER).count("ShouldRenderAttachedWindowLights("), 2)

    def test_loader_keeps_the_instances(self):
        # The coronastar glows come from these instances (CCoronas via PreRender).
        func = extract_function(read_source("stories/src/core/FileLoader.cpp"),
                                "void\nCFileLoader::LoadObjectInstance(const char *line)")
        self.assertNotIn("IsInstanceAbsentOnPS2(", func)


if __name__ == "__main__":
    unittest.main()
