import { useEffect, useMemo, useRef } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { Bounds, Center, OrbitControls } from "@react-three/drei";
import * as THREE from "three";
import type { MeshData } from "../types/cadSpec";

function CADMesh({ mesh }: { mesh: MeshData }) {
  const ref = useRef<THREE.Mesh>(null);

  const geometry = useMemo(() => {
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.BufferAttribute(mesh.vertices, 3));
    geo.setAttribute("normal", new THREE.BufferAttribute(mesh.normals, 3));
    geo.setIndex(new THREE.BufferAttribute(mesh.indices, 1));
    geo.computeBoundingSphere();
    return geo;
  }, [mesh]);

  useFrame(() => {
    ref.current?.geometry.computeBoundingSphere();
  });

  return (
    <mesh ref={ref} geometry={geometry} castShadow receiveShadow>
      <meshStandardMaterial color="#1a1a1a" metalness={0.08} roughness={0.62} />
    </mesh>
  );
}

function Scene({ mesh }: { mesh: MeshData }) {
  const gridSize = useMemo(() => {
    const box = new THREE.Box3();
    const v = mesh.vertices;
    for (let i = 0; i < v.length; i += 3) {
      box.expandByPoint(new THREE.Vector3(v[i], v[i + 1], v[i + 2]));
    }
    const size = box.getSize(new THREE.Vector3());
    const span = Math.max(size.x, size.y, size.z, 1);
    return Math.ceil((span * 2.5) / 10) * 10;
  }, [mesh]);

  return (
    <>
      <ambientLight intensity={0.72} />
      <directionalLight castShadow position={[120, 180, 80]} intensity={0.95} />
      <directionalLight position={[-80, 60, -40]} intensity={0.35} />
      <gridHelper args={[gridSize, 20, "#c4b4b4", "#e0d6d4"]} />
      <Bounds fit clip observe margin={1.45}>
        <Center>
          <CADMesh mesh={mesh} />
        </Center>
      </Bounds>
      <OrbitControls makeDefault enableDamping dampingFactor={0.08} />
    </>
  );
}

interface ModelViewerProps {
  mesh: MeshData | null;
  loading?: boolean;
  error?: string | null;
  onRebuild?: () => void;
  canRebuild?: boolean;
}

export function ModelViewer({ mesh, loading, error, onRebuild, canRebuild }: ModelViewerProps) {
  useEffect(() => {
    return () => {
      /* geometry disposed via react-three-fiber unmount */
    };
  }, []);

  return (
    <div className="viewer-panel">
      <div className="viewer-toolbar">
        <span>3D Preview</span>
        <div className="viewer-toolbar-actions">
          {loading && <span className="badge">Building model…</span>}
          {onRebuild && (
            <button type="button" className="secondary compact" disabled={!canRebuild} onClick={onRebuild}>
              Try again
            </button>
          )}
        </div>
      </div>
      <div className="viewer-canvas">
        {error && <div className="viewer-overlay error">{error}</div>}
        {!mesh && !loading && !error && (
          <div className="viewer-overlay">Upload a sketch to generate a 3D model</div>
        )}
        <Canvas
          shadows
          dpr={[1, 2]}
          style={{ width: "100%", height: "100%", display: "block", background: "#f7f2f0" }}
          camera={{ fov: 42, near: 0.1, far: 20000, position: [120, 90, 120] }}
        >
          <color attach="background" args={["#f7f2f0"]} />
          {mesh && <Scene mesh={mesh} />}
        </Canvas>
      </div>
    </div>
  );
}
