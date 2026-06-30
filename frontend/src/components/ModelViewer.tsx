import { useEffect, useMemo, useRef } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { OrbitControls, PerspectiveCamera } from "@react-three/drei";
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
        <Canvas shadows style={{ background: "#f7f2f0" }}>
          <color attach="background" args={["#f7f2f0"]} />
          <PerspectiveCamera makeDefault position={[180, 120, 180]} fov={45} />
          <ambientLight intensity={0.72} />
          <directionalLight castShadow position={[120, 180, 80]} intensity={0.95} />
          <gridHelper args={[400, 20, "#c4b4b4", "#e0d6d4"]} />
          {mesh && <CADMesh mesh={mesh} />}
          <OrbitControls makeDefault enableDamping />
        </Canvas>
      </div>
    </div>
  );
}
