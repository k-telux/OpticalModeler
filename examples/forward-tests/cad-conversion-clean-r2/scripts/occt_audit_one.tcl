# Deterministic OCCT/XCAF audit and OBJ handoff for one locked STEP file.
# Inputs are relative paths supplied through the environment by run_occt_conversion.py.

proc block {name value} {
  puts "__PHASE2_BEGIN__:$name"
  puts $value
  puts "__PHASE2_END__:$name"
}

foreach required {PHASE2_STEP PHASE2_OBJ PHASE2_SKU} {
  if {![info exists ::env($required)] || $::env($required) eq ""} {
    puts stderr "missing environment input: $required"
    exit 64
  }
}

set step [string map {\\ /} $::env(PHASE2_STEP)]
set obj [string map {\\ /} $::env(PHASE2_OBJ)]
set sku $::env(PHASE2_SKU)

pload ALL
block RUN_SKU $sku
block STEP_INPUT $step

if {[catch {stepfileunits $step} units]} {
  block STEP_UNITS_ERROR $units
  exit 65
}
block STEP_UNITS $units

if {[catch {ReadStep D $step} readResult]} {
  block READ_STEP_ERROR $readResult
  exit 66
}
block READ_STEP $readResult
block DOCUMENT_LENGTH_UNIT [XGetLengthUnit D]
block DOCUMENT_LENGTH_SCALE_TO_M [XGetLengthUnit D -scale]

if {[catch {XGetFreeShapes D freeShapes} freeResult]} {
  block FREE_SHAPES_ERROR $freeResult
} else {
  block FREE_SHAPES $freeResult
}
set topLabels [XGetTopLevelShapes D]
block TOP_LEVEL_LABELS $topLabels

if {[catch {XDumpAssemblyTree D -names} treeResult]} {
  block XCAF_ASSEMBLY_TREE_ERROR $treeResult
} else {
  block XCAF_ASSEMBLY_TREE $treeResult
}
if {[catch {XDumpAssemblyGraph D -names} graphResult]} {
  block XCAF_ASSEMBLY_GRAPH_ERROR $graphResult
} else {
  block XCAF_ASSEMBLY_GRAPH $graphResult
}
if {[catch {XDumpNomenclature D -names} nomenResult]} {
  block XCAF_NOMENCLATURE_ERROR $nomenResult
} else {
  block XCAF_NOMENCLATURE $nomenResult
}
if {[catch {XStat D} statResult]} {
  block XCAF_STAT_ERROR $statResult
} else {
  block XCAF_STAT $statResult
}
if {[catch {XGetAllColors D} colorsResult]} {
  block XCAF_COLORS_ERROR $colorsResult
} else {
  block XCAF_COLORS $colorsResult
}
if {[catch {XGetAllVisMaterials D -labels} materialsResult]} {
  block XCAF_VIS_MATERIALS_ERROR $materialsResult
} else {
  block XCAF_VIS_MATERIALS $materialsResult
}

set topIndex 0
foreach label $topLabels {
  incr topIndex
  block TOP_LABEL_${topIndex}_ENTRY $label
  if {[catch {XGetShape top_${topIndex} D $label} getShapeResult]} {
    block TOP_LABEL_${topIndex}_GET_SHAPE_ERROR $getShapeResult
  } else {
    block TOP_LABEL_${topIndex}_GET_SHAPE $getShapeResult
    catch {XLabelInfo D $label} labelInfoResult
    block TOP_LABEL_${topIndex}_INFO $labelInfoResult
    catch {XDumpLocation D $label} locationResult
    block TOP_LABEL_${topIndex}_LOCATION $locationResult
    catch {nbshapes top_${topIndex} -t} topTopologyResult
    block TOP_LABEL_${topIndex}_TOPOLOGY $topTopologyResult
    catch {checkshape top_${topIndex}} topValidityResult
    block TOP_LABEL_${topIndex}_BREP_VALIDITY $topValidityResult
  }
}
block TOP_LEVEL_COUNT $topIndex

if {[catch {XGetOneShape aggregate D} aggregateResult]} {
  block AGGREGATE_SHAPE_ERROR $aggregateResult
  exit 67
}
block AGGREGATE_SHAPE $aggregateResult
block AGGREGATE_TOPOLOGY [nbshapes aggregate -t]

if {[catch {bounding aggregate -noTriangulation -optimal -finitePart -noDraw -save bxmin bymin bzmin bxmax bymax bzmax} bboxResult]} {
  block NATIVE_BBOX_ERROR $bboxResult
  exit 68
}
set xmin [dval bxmin]
set ymin [dval bymin]
set zmin [dval bzmin]
set xmax [dval bxmax]
set ymax [dval bymax]
set zmax [dval bzmax]
block NATIVE_BBOX_MM "$xmin $ymin $zmin $xmax $ymax $zmax"
set bboxBounded 1
foreach coordinate [list $xmin $ymin $zmin $xmax $ymax $zmax] {
  if {abs($coordinate) >= 1.0e50} {
    set bboxBounded 0
  }
}
if {$bboxBounded} {
  set dx [expr {$xmax - $xmin}]
  set dy [expr {$ymax - $ymin}]
  set dz [expr {$zmax - $zmin}]
  set diagonal [expr {sqrt($dx*$dx + $dy*$dy + $dz*$dz)}]
  block NATIVE_BBOX_STATUS BOUNDED
  block NATIVE_BBOX_DIAGONAL_MM $diagonal
} else {
  set diagonal -1
  block NATIVE_BBOX_STATUS UNBOUNDED_SENTINEL
  block NATIVE_BBOX_DIAGONAL_MM UNVERIFIED
}

if {[catch {checkshape aggregate} validityResult]} {
  block AGGREGATE_BREP_VALIDITY_ERROR $validityResult
} else {
  block AGGREGATE_BREP_VALIDITY $validityResult
}
if {[catch {tolerance aggregate} toleranceResult]} {
  block AGGREGATE_TOLERANCE_ERROR $toleranceResult
} else {
  block AGGREGATE_TOLERANCE $toleranceResult
}

# ponytail: a single fixed formula is sufficient for this bounded smoke test;
# a future full-catalog run can introduce per-risk meshing profiles.
if {$bboxBounded} {
  set linearDeflection [expr {max(0.01, $diagonal * 0.0001)}]
  set meshPolicySource bounded_native_bbox
} else {
  set linearDeflection 0.01
  set meshPolicySource fixed_mm_fallback_for_unbounded_native_bbox
}
set minimumSize [expr {$linearDeflection * 0.1}]
block MESH_POLICY "linear_deflection_mm=$linearDeflection angular_deflection_deg=10 minimum_size_mm=$minimumSize relative=0 parallel=0 algorithm=watson interior_angle_deg=10 force_remesh=1 source=$meshPolicySource"
if {[catch {trinfo aggregate} preMeshInfo]} {
  block PRE_MESH_INFO_ERROR $preMeshInfo
} else {
  block PRE_MESH_INFO $preMeshInfo
}
if {[catch {incmesh aggregate $linearDeflection -angular 10 -relative 0 -parallel 0 -min $minimumSize -algo watson -ai 10 -int_vert_off 0 -surf_def_off 0 -adjust_min 0 -force_face_def 0 -decrease 1} meshResult]} {
  block SERIAL_MESH_ERROR $meshResult
  exit 69
}
block SERIAL_MESH $meshResult
block POST_MESH_INFO [trinfo aggregate]

if {[catch {WriteObj D $obj -fileCoordSys Zup -fileUnit m -systemCoordSys Zup -comments deterministic-phase2-smoke -author OpticalModeler-public-audit} objResult]} {
  block WRITE_OBJ_ERROR $objResult
  exit 70
}
block WRITE_OBJ $objResult
block OBJ_OUTPUT $obj
block RUN_COMPLETE PASS
exit
