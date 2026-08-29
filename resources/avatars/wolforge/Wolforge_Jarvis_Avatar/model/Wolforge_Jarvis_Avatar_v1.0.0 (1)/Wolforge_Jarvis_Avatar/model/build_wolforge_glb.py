#!/usr/bin/env python3
"""Build the offline Wolforge Jarvis cyber-wolf avatar as an animated GLB.

No third-party Python packages are required. The model intentionally uses
separate hard-surface plates and named nodes so Jarvis can animate it through
standard glTF clips in WebView2/model-viewer.
"""
from __future__ import annotations

import json, math, struct
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "wolforge_jarvis_avatar.glb"

buffers = bytearray()
views, accessors, meshes, nodes, materials, animations = [], [], [], [], [], []

def align4():
    while len(buffers) % 4: buffers.append(0)

def accessor(values, kind="VEC3", component=5126, target=None):
    align4(); offset=len(buffers)
    flat=[x for row in values for x in (row if isinstance(row,(list,tuple)) else [row])]
    fmt={5126:'f',5123:'H',5125:'I'}[component]
    buffers.extend(struct.pack('<'+fmt*len(flat), *flat)); length=len(buffers)-offset
    vi=len(views); v={"buffer":0,"byteOffset":offset,"byteLength":length}
    if target: v["target"]=target
    views.append(v)
    ai=len(accessors); a={"bufferView":vi,"componentType":component,"count":len(values),"type":kind}
    if component==5126 and values:
        cols=len(values[0]) if isinstance(values[0],(list,tuple)) else 1
        a["min"]=[min(row[c] if cols>1 else row for row in values) for c in range(cols)]
        a["max"]=[max(row[c] if cols>1 else row for row in values) for c in range(cols)]
    accessors.append(a); return ai

def mat(name, color, metallic=.75, rough=.28, emissive=None):
    m={"name":name,"pbrMetallicRoughness":{"baseColorFactor":[*color,1],"metallicFactor":metallic,"roughnessFactor":rough}}
    if emissive:
        m["emissiveFactor"]=emissive; m["extensions"]={"KHR_materials_emissive_strength":{"emissiveStrength":3.0}}
    materials.append(m); return len(materials)-1

NAVY=mat("Midnight_Navy",(.025,.065,.12),.9,.24)
GUN=mat("Gunmetal",(.12,.19,.29),.88,.25)
SILVER=mat("Cool_Silver",(.52,.62,.72),.92,.2)
BLACK=mat("Muzzle_Black",(.008,.012,.018),.3,.36)
CYAN=mat("Cyan_Emission",(.02,.55,.72),.25,.18,[0,.85,1])
DARK=mat("Mouth_Interior",(.018,.008,.012),.05,.65)

def box_mesh(name, size, material, taper=(1,1)):
    x,y,z=[v/2 for v in size]; tx,ty=taper
    v=[(-x,-y,-z),(x,-y,-z),(x,y,-z),(-x,y,-z),(-x*tx,-y*ty,z),(x*tx,-y*ty,z),(x*tx,y*ty,z),(-x*tx,y*ty,z)]
    f=[0,2,1,0,3,2,4,5,6,4,6,7,0,1,5,0,5,4,1,2,6,1,6,5,2,3,7,2,7,6,3,0,4,3,4,7]
    pi=accessor(v); ni=[]
    # Flat-looking normals are sufficient for the faceted armor aesthetic.
    for p in v:
        l=math.sqrt(sum(q*q for q in p)) or 1; ni.append(tuple(q/l for q in p))
    no=accessor(ni); ix=accessor([(i,) for i in f],"SCALAR",5123,34963)
    meshes.append({"name":name,"primitives":[{"attributes":{"POSITION":pi,"NORMAL":no},"indices":ix,"material":material}]})
    return len(meshes)-1

def wedge_mesh(name, points, material):
    # Convex fan from first point; intended for thin triangular armor accents.
    v=points; faces=[]
    for i in range(1,len(v)-1): faces += [0,i,i+1]
    pi=accessor(v); normals=[]
    for p in v:
        l=math.sqrt(sum(q*q for q in p)) or 1; normals.append(tuple(q/l for q in p))
    no=accessor(normals); ix=accessor([(i,) for i in faces],"SCALAR",5123,34963)
    meshes.append({"name":name,"primitives":[{"attributes":{"POSITION":pi,"NORMAL":no},"indices":ix,"material":material,"doubleSided":True}]})
    return len(meshes)-1

def node(name, mesh=None, parent=None, t=(0,0,0), r=(0,0,0,1), s=(1,1,1), extras=None):
    n={"name":name,"translation":list(t),"rotation":list(r),"scale":list(s)}
    if mesh is not None: n["mesh"]=mesh
    if extras: n["extras"]=extras
    nodes.append(n); idx=len(nodes)-1
    if parent is not None: nodes[parent].setdefault("children",[]).append(idx)
    return idx

def qx(a): return (math.sin(a/2),0,0,math.cos(a/2))
def qy(a): return (0,math.sin(a/2),0,math.cos(a/2))
def qz(a): return (0,0,math.sin(a/2),math.cos(a/2))

root=node("AvatarRoot",extras={"avatar":"Wolforge Jarvis","version":"1.0.0","units":"meters"})
neck=node("Neck",box_mesh("NeckMesh",(2.35,1.45,1.25),NAVY,(.72,.7)),root,t=(0,-2.05,0))
head=node("Head",box_mesh("Cranium",(2.65,2.65,1.55),GUN,(.82,.86)),neck,t=(0,1.75,.02))

# Ears are separate animation targets.
ear_mesh=box_mesh("EarArmor",(.58,1.85,.62),SILVER,(.18,.08))
ear_l=node("Ear.L",ear_mesh,head,t=(-.94,1.72,.03),r=qz(-.12))
ear_r=node("Ear.R",ear_mesh,head,t=(.94,1.72,.03),r=qz(.12))
inner=box_mesh("EarInner",(.3,1.35,.25),NAVY,(.12,.06))
node("EarInner.L",inner,ear_l,t=(0,-.02,-.34)); node("EarInner.R",inner,ear_r,t=(0,-.02,-.34))

# Brow, cheek and forehead plates mirror the icon's sharp chevrons.
brow=box_mesh("BrowPlate",(1.28,.52,.28),GUN,(.65,.82))
node("Brow.L",brow,head,t=(-.67,.42,-.91),r=qz(-.28)); node("Brow.R",brow,head,t=(.67,.42,-.91),r=qz(.28))
cheek=box_mesh("CheekPlate",(1.05,1.15,.28),SILVER,(.72,.62))
node("Cheek.L",cheek,head,t=(-1.02,-.48,-.92),r=qz(-.32)); node("Cheek.R",cheek,head,t=(1.02,-.48,-.92),r=qz(.32))
side=box_mesh("SideManePlate",(.72,1.18,.62),NAVY,(.35,.55))
node("Mane.L",side,head,t=(-1.47,-.55,-.1),r=qz(-.34)); node("Mane.R",side,head,t=(1.47,-.55,-.1),r=qz(.34))

# Cyan eyes can be blinked by scaling their local Y axis.
eye=box_mesh("EyeLens",(.64,.20,.12),CYAN,(.7,.8))
eye_l=node("Eye.L",eye,head,t=(-.59,.03,-1.48),r=qz(-.16),extras={"control":"blink"})
eye_r=node("Eye.R",eye,head,t=(.59,.03,-1.48),r=qz(.16),extras={"control":"blink"})

# Long articulated muzzle and jaw.
upper=node("UpperMuzzle",box_mesh("UpperMuzzleMesh",(1.46,1.65,.92),SILVER,(.66,.48)),head,t=(0,-.78,-1.18),r=qx(-.06))
nose=node("Nose",box_mesh("NoseMesh",(.78,.48,.38),BLACK,(.75,.72)),upper,t=(0,-.67,-.54))
mouth=node("MouthInterior",box_mesh("MouthInteriorMesh",(1.08,.42,.5),DARK,(.78,.82)),head,t=(0,-1.53,-1.28))
jaw=node("Jaw",box_mesh("LowerJawMesh",(1.14,.58,.7),SILVER,(.72,.62)),head,t=(0,-1.53,-1.18),extras={"control":"jaw","visemes":["rest","MBP","FV","A","E","I","O","U","L","SZ"]})
node("ChinCyan",box_mesh("ChinAccent",(.52,.08,.10),CYAN),jaw,t=(0,-.27,-.39))

# Icon-specific cyan forehead and cheek circuits.
line=box_mesh("CircuitLine",(.055,1.5,.055),CYAN)
node("ForeheadCircuit",line,head,t=(0,.75,-1.49))
accent=box_mesh("CheekCyan",(.07,.76,.07),CYAN)
node("CheekCircuit.L",accent,head,t=(-1.14,-.47,-1.11),r=qz(-.73)); node("CheekCircuit.R",accent,head,t=(1.14,-.47,-1.11),r=qz(.73))

# Shoulder/bust armor.
shoulder=box_mesh("ShoulderArmor",(1.75,.68,1.6),GUN,(.6,.72))
node("Shoulder.L",shoulder,root,t=(-1.35,-2.75,.25),r=qz(-.18)); node("Shoulder.R",shoulder,root,t=(1.35,-2.75,.25),r=qz(.18))
chest=node("Chest",box_mesh("ChestMesh",(1.5,1.0,1.15),NAVY,(.72,.76)),root,t=(0,-2.75,.25))
node("ChestCircuit",line,chest,t=(0,0,-.61),s=(1,.55,1))

def clip(name, channels):
    samplers=[]; chans=[]
    for target,path,times,values,kind in channels:
        ti=accessor([(x,) for x in times],"SCALAR")
        vo=accessor(values,kind)
        samplers.append({"input":ti,"output":vo,"interpolation":"LINEAR"})
        chans.append({"sampler":len(samplers)-1,"target":{"node":target,"path":path}})
    animations.append({"name":name,"samplers":samplers,"channels":chans})

clip("Idle",[(head,"rotation",[0,2,4,6],[(0,0,0,1),qy(.025),qy(-.018),(0,0,0,1)],"VEC4"),
             (neck,"scale",[0,3,6],[(1,1,1),(1.012,1.018,1.012),(1,1,1)],"VEC3")])
clip("Blink",[(eye_l,"scale",[0,.08,.16],[(1,1,1),(1,.05,1),(1,1,1)],"VEC3"),(eye_r,"scale",[0,.08,.16],[(1,1,1),(1,.05,1),(1,1,1)],"VEC3")])
clip("JawOpen",[(jaw,"rotation",[0,.18,.4],[(0,0,0,1),qx(-.42),(0,0,0,1)],"VEC4")])
clip("Speaking",[(jaw,"rotation",[0,.12,.24,.36,.5,.64,.78,1],[(0,0,0,1),qx(-.22),qx(-.06),qx(-.34),qx(-.12),qx(-.27),qx(-.08),(0,0,0,1)],"VEC4")])
clip("Listening",[(ear_l,"rotation",[0,.35], [qz(-.12),qz(.04)],"VEC4"),(ear_r,"rotation",[0,.35],[qz(.12),qz(-.04)],"VEC4"),(head,"rotation",[0,.35],[(0,0,0,1),qx(.07)],"VEC4")])
clip("Thinking",[(head,"rotation",[0,.8,1.6],[qy(0),qy(-.12),qy(.08)],"VEC4"),(ear_l,"rotation",[0,.8,1.6],[qz(-.12),qz(-.22),qz(-.1)],"VEC4")])
clip("Success",[(head,"rotation",[0,.25,.5],[(0,0,0,1),qx(.09),(0,0,0,1)],"VEC4"),(ear_l,"rotation",[0,.25],[qz(-.12),qz(.06)],"VEC4"),(ear_r,"rotation",[0,.25],[qz(.12),qz(-.06)],"VEC4")])
clip("Warning",[(ear_l,"rotation",[0,.2],[qz(-.12),qz(.1)],"VEC4"),(ear_r,"rotation",[0,.2],[qz(.12),qz(-.1)],"VEC4"),(head,"rotation",[0,.2],[(0,0,0,1),qx(-.05)],"VEC4")])
clip("Error",[(head,"rotation",[0,.25,.5,.75],[qy(0),qy(-.065),qy(.065),qy(0)],"VEC4"),(ear_l,"rotation",[0,.35],[qz(-.12),qz(-.28)],"VEC4"),(ear_r,"rotation",[0,.35],[qz(.12),qz(.28)],"VEC4")])

gltf={"asset":{"version":"2.0","generator":"Wolforge Jarvis Avatar Builder 1.0"},
      "extensionsUsed":["KHR_materials_emissive_strength"],"extensionsRequired":[],
      "scene":0,"scenes":[{"name":"Wolforge Avatar","nodes":[root]}],"nodes":nodes,"meshes":meshes,
      "materials":materials,"animations":animations,"accessors":accessors,"bufferViews":views,
      "buffers":[{"byteLength":len(buffers)}],
      "extras":{"license":"Original user-owned Wolforge-derived asset","animationClips":[a["name"] for a in animations]}}

js=json.dumps(gltf,separators=(',',':')).encode(); js += b' ' * ((4-len(js)%4)%4)
align4(); bin_chunk=bytes(buffers); bin_chunk += b'\0' * ((4-len(bin_chunk)%4)%4)
total=12+8+len(js)+8+len(bin_chunk)
with OUT.open('wb') as f:
    f.write(struct.pack('<III',0x46546C67,2,total)); f.write(struct.pack('<I4s',len(js),b'JSON')); f.write(js)
    f.write(struct.pack('<I4s',len(bin_chunk),b'BIN\0')); f.write(bin_chunk)
print(f"Created {OUT} ({OUT.stat().st_size:,} bytes), {len(nodes)} nodes, {len(animations)} animations")
