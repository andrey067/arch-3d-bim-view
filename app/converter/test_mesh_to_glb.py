"""Smoke tests for DAE/OBJ → GLB (requires Blender when run)."""

from __future__ import annotations

import os
import shutil
import tempfile

import pytest

from mesh_to_glb import MeshConversionFailure, convert_mesh_to_glb

MINIMAL_DAE = """<?xml version="1.0" encoding="utf-8"?>
<COLLADA xmlns="http://www.collada.org/2005/11/COLLADASchema" version="1.4.1">
  <asset><up_axis>Z_UP</up_axis></asset>
  <library_geometries>
    <geometry id="cube-mesh" name="cube">
      <mesh>
        <source id="cube-mesh-positions">
          <float_array id="cube-mesh-positions-array" count="24">
            -0.5 -0.5 0.5 0.5 -0.5 0.5 0.5 0.5 0.5 -0.5 0.5 0.5
            -0.5 -0.5 -0.5 0.5 -0.5 -0.5 0.5 0.5 -0.5 -0.5 0.5 -0.5
          </float_array>
          <technique_common>
            <accessor source="#cube-mesh-positions-array" count="8" stride="3">
              <param name="X" type="float"/>
              <param name="Y" type="float"/>
              <param name="Z" type="float"/>
            </accessor>
          </technique_common>
        </source>
        <vertices id="cube-mesh-vertices">
          <input semantic="POSITION" source="#cube-mesh-positions"/>
        </vertices>
        <triangles count="12">
          <input semantic="VERTEX" source="#cube-mesh-vertices" offset="0"/>
          <p>0 1 2 0 2 3 4 6 5 4 7 6 0 4 5 0 5 1 2 6 7 2 5 6 0 3 7 0 7 4 1 5 6 1 6 2</p>
        </triangles>
      </mesh>
    </geometry>
  </library_geometries>
  <library_visual_scenes>
    <visual_scene id="Scene" name="Scene">
      <node id="Cube" name="Cube" type="NODE">
        <instance_geometry url="#cube-mesh"/>
      </node>
    </visual_scene>
  </library_visual_scenes>
  <scene>
    <instance_visual_scene url="#Scene"/>
  </scene>
</COLLADA>
"""


@pytest.mark.skipif(shutil.which("blender") is None, reason="Blender not installed")
def test_convert_dae_to_glb_produces_non_empty_glb() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        dae = os.path.join(tmp, "test.dae")
        glb = os.path.join(tmp, "out.glb")
        with open(dae, "w", encoding="utf-8") as f:
            f.write(MINIMAL_DAE)
        convert_mesh_to_glb(dae, glb, mesh_format="dae", timeout_s=120)
        assert os.path.isfile(glb)
        assert os.path.getsize(glb) > 0


def test_convert_mesh_missing_blender_raises() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        dae = os.path.join(tmp, "test.dae")
        glb = os.path.join(tmp, "out.glb")
        with open(dae, "w", encoding="utf-8") as f:
            f.write(MINIMAL_DAE)
        with pytest.raises(MeshConversionFailure):
            convert_mesh_to_glb(
                dae,
                glb,
                mesh_format="dae",
                blender_path="/nonexistent/blender",
                timeout_s=5,
            )


CADEIRA_FIXTURE = os.path.join(
    os.path.dirname(__file__), "fixtures", "CADEIRA.dae"
)


@pytest.mark.skipif(
    not os.path.isfile(CADEIRA_FIXTURE),
    reason="CADEIRA.dae fixture not present",
)
@pytest.mark.skipif(shutil.which("blender") is None, reason="Blender not installed")
def test_cadeira_dae_to_glb_produces_non_empty_glb() -> None:
    """Smoke test against the real SketchUp chair export under files/."""
    with tempfile.TemporaryDirectory() as tmp:
        glb = os.path.join(tmp, "cadeira.glb")
        convert_mesh_to_glb(
            CADEIRA_FIXTURE, glb, mesh_format="dae", timeout_s=180
        )
        assert os.path.isfile(glb)
        assert os.path.getsize(glb) > 1024
