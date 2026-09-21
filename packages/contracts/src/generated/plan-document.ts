/* AUTO-GENERATED FROM PYDANTIC JSON SCHEMA. DO NOT EDIT. */

export type AffectedEntityIds = string[];
export type Code = string;
export type ConfirmedByUser = boolean;
export type Description = string;
export type Id = string;
export type AssumptionSource =
  "USER" | "DOCUMENTED_DEFAULT" | "AI_SUGGESTED" | "SYSTEM_DERIVED";
export type Assumptions = Assumption[];
export type XMm = number;
export type YMm = number;
export type Holes = [IntPoint, IntPoint, IntPoint, ...IntPoint[]][];
/**
 * @minItems 3
 */
export type Outer = [IntPoint, IntPoint, IntPoint, ...IntPoint[]];
export type BoundaryEdgeId = string;
export type DistanceMm = number;
export type Id1 = string;
export type RegulationRuleId = string | null;
export type SourceRef = string | null;
export type Setbacks = Setback[];
export type CanonicalUnits = "mm";
export type ContentHash = string | null;
export type Category = string;
export type Id2 = string;
export type Text = string;
export type Annotations = Annotation[];
export type Id3 = string;
export type LabelOverride = string | null;
export type OffsetMm = number;
export type Dimensions = Dimension[];
export type ElevationMm = number;
export type FixtureType = string;
export type Id4 = string;
export type RotationUdeg = number;
export type Fixtures = Fixture[];
export type FloorToFloorMm = number;
export type FurnitureType = string;
export type Id5 = string;
export type RotationUdeg1 = number;
export type Furniture = Furniture1[];
export type Id6 = string;
export type Index = number;
export type Name = string;
export type HeightMm = number;
export type DoorHinge = "LEFT" | "RIGHT";
export type Id7 = string;
export type OpeningKind = "DOOR" | "WINDOW" | "OPENING";
export type OffsetFromWallStartMm = number;
export type SillHeightMm = number | null;
export type DoorSwing = "IN" | "OUT" | "SLIDING" | "NONE";
export type WallId = string;
export type WidthMm = number;
export type Openings = Opening[];
export type Id8 = string;
export type Locked = boolean;
export type Name1 = string | null;
export type RequirementId = string | null;
export type RoomType =
  | "living"
  | "drawing"
  | "dining"
  | "kitchen"
  | "utility"
  | "pantry"
  | "store"
  | "puja"
  | "master_bedroom"
  | "bedroom"
  | "parents_bedroom"
  | "guest_bedroom"
  | "children_bedroom"
  | "attached_toilet"
  | "common_toilet"
  | "powder_room"
  | "bath"
  | "dressing"
  | "wardrobe"
  | "staircase"
  | "lift"
  | "lobby"
  | "corridor"
  | "foyer"
  | "verandah"
  | "balcony"
  | "terrace"
  | "courtyard"
  | "parking"
  | "garage"
  | "home_office"
  | "servant_room"
  | "servant_toilet"
  | "laundry"
  | "study"
  | "family_lounge";
export type Rooms = RoomGeometry[];
export type Id9 = string;
export type SiteSpaceKind =
  | "LIGHTWELL"
  | "LANDSCAPE"
  | "OPEN_SPACE"
  | "UTILITY_YARD"
  | "VEHICLE_ACCESS"
  | "SHAFT"
  | "PORCH";
export type Label = string | null;
export type SiteSpaceSource = "USER" | "SYSTEM_DERIVED" | "AI_SUGGESTED";
export type SiteSpaces = PurposefulSiteSpace[];
export type DirectionUdeg = number;
export type FloorHeightMm = number;
export type HeadroomMm = number | null;
export type Id10 = string;
export type LandingDepthMm = number;
export type NumberOfRisers = number;
export type RiserMm = number;
export type StairType =
  "STRAIGHT" | "L_SHAPED" | "U_SHAPED" | "DOG_LEGGED" | "SPIRAL" | "OTHER";
export type TreadMm = number;
export type WidthMm1 = number;
export type Stairs = Stair[];
export type WallCategory = "EXTERNAL" | "INTERNAL" | "SHAFT" | "PARAPET";
export type ConstructionType = string | null;
export type HeightMm1 = number;
export type Id11 = string;
export type ThicknessMm = number;
export type Walls = Wall[];
export type Floors = Floor[];
export type CompletedAt = string | null;
export type InputHash = string | null;
export type RuleBundleHash = string | null;
export type Seed = number | null;
export type SolverName = string | null;
export type Key = string;
export type Value = string;
export type SolverParameters = MetadataItem[];
export type SolverStepMm = number | null;
export type SolverVersion = string | null;
export type StartedAt = string | null;
export type NorthRotationUdeg = number;
export type OrientationSource =
  "USER" | "SURVEY" | "DOCUMENT_EXTRACTION" | "IMPORT";
export type Verified = boolean;
export type Accepted = boolean;
export type ClosureErrorMm = number;
export type ToleranceMm = number;
export type ExactMmDecimal = string;
export type LengthUnit = "mm" | "cm" | "m" | "in" | "ft";
export type InputValue = string;
export type Label1 = string;
export type QuantizedMm = number;
export type RoundingDeltaMmDecimal = string;
export type DeclaredMeasurements = DeclaredMeasurement[];
export type EdgeIds = string[];
export type PlotGeometryType = "RECTANGLE" | "POLYGON";
export type Id12 = string;
export type PlotInputSource =
  "MANUAL" | "INTERACTIVE" | "SURVEY" | "DOCUMENT_EXTRACTION" | "IMPORT";
export type VerificationStatus =
  "UNVERIFIED" | "USER_VERIFIED" | "SURVEY_VERIFIED";
export type ProjectId = string;
export type RegulationSpecVersion = string | null;
export type RevisionId = string;
export type Id13 = string;
export type Name2 = string | null;
export type PlotEdgeIds = string[];
export type PrimaryAccess = boolean;
export type WidthMm2 = number | null;
export type Roads = Road[];
export type MaxGapMm = number | null;
export type MinSharedLengthMm = number | null;
export type Weight = number;
export type AdjacencyPreferences = AdjacencyPreference[];
export type Hard = boolean;
export type AdjacencyProhibitions = AdjacencyProhibition[];
export type MaxRatioMilli = number;
export type MinRatioMilli = number;
export type DaylightPriority = number;
export type FloorPreference = number[];
export type Id14 = string;
export type Locked1 = boolean;
export type MaxAreaMm2 = number | null;
export type MaxDepthMm = number | null;
export type MaxWidthMm = number | null;
export type MinAreaMm2 = number;
export type MinDepthMm = number;
export type MinWidthMm = number;
export type PreferredAreaMm2 = number | null;
export type PreferredDepthMm = number | null;
export type PreferredWidthMm = number | null;
export type PrivacyPriority = number;
export type Quantity = number;
export type UserPriority = number;
export type VastuProfileRefs = string[];
export type VentilationPriority = number;
export type RoomRequirements = RoomRequirement[];
export type SchemaVersion = "1.1.0";
export type Key1 = string;
export type ScoreBasisPoints = number;
export type WeightBasisPoints = number;
export type Components = ScoreComponent[];
export type Mode = string;
export type OverallBasisPoints = number;
export type CheckId = string;
export type EntityRefs = string[];
export type Key2 = string;
export type Value1 = string;
export type Evidence = EvidenceItem[];
export type MessageCode = string;
export type ValidationSeverity = "ERROR" | "WARNING" | "INFO";
export type ValidatorVersion = string;
export type Errors = ValidationResult[];
export type Informational = ValidationResult[];
export type Valid = boolean;
export type Warnings = ValidationResult[];
export type MajorViolations = number;
export type MinorCompromises = number;
export type OverallBasisPoints1 = number | null;
export type EarnedWeight = number;
export type EntityRefs1 = string[];
export type GeometryEvidence = EvidenceItem[];
export type MeasuredEvidence = EvidenceItem[];
export type RawWeight = number;
export type RuleId = string;
export type RuleVersion = string;
export type VastuStatus =
  "PASS" | "PARTIAL" | "COMPROMISE" | "FAIL" | "NOT_APPLICABLE";
export type Results = VastuResult[];
export type SpecVersion = string;
export type VastuSpecVersion = string;

export interface PlanDocument {
  assumptions?: Assumptions;
  buildable_area: BuildableArea;
  canonical_units: CanonicalUnits;
  content_hash?: ContentHash;
  floors: Floors;
  generation_metadata: GenerationMetadata;
  orientation: Orientation;
  plot: Plot;
  project_id: ProjectId;
  regulation_spec_version?: RegulationSpecVersion;
  revision_id: RevisionId;
  roads?: Roads;
  room_requirements?: RoomRequirements;
  schema_version: SchemaVersion;
  scoring: ScoringSummary;
  validation: ValidationReport;
  vastu_analysis: VastuAnalysis;
  vastu_spec_version: VastuSpecVersion;
}
export interface Assumption {
  affected_entity_ids?: AffectedEntityIds;
  code: Code;
  confirmed_by_user: ConfirmedByUser;
  description: Description;
  id: Id;
  source: AssumptionSource;
}
export interface BuildableArea {
  polygon: IntPolygon;
  setbacks?: Setbacks;
}
/**
 * Canonical integer-mm polygon storage.
 *
 * Topological validity is intentionally not proven in Phase 1; that belongs to the
 * geometry/validation phases. Rings are open: callers must not repeat the first point.
 */
export interface IntPolygon {
  holes?: Holes;
  outer: Outer;
}
export interface IntPoint {
  x_mm: XMm;
  y_mm: YMm;
}
export interface Setback {
  boundary_edge_id: BoundaryEdgeId;
  distance_mm: DistanceMm;
  id: Id1;
  regulation_rule_id?: RegulationRuleId;
  source_ref?: SourceRef;
}
export interface Floor {
  annotations?: Annotations;
  boundary?: IntPolygon | null;
  dimensions?: Dimensions;
  elevation_mm: ElevationMm;
  fixtures?: Fixtures;
  floor_to_floor_mm: FloorToFloorMm;
  furniture?: Furniture;
  id: Id6;
  index: Index;
  name: Name;
  openings?: Openings;
  rooms?: Rooms;
  site_spaces?: SiteSpaces;
  stairs?: Stairs;
  walls?: Walls;
}
export interface Annotation {
  anchor: IntPoint;
  category: Category;
  id: Id2;
  text: Text;
}
export interface Dimension {
  end: IntPoint;
  id: Id3;
  label_override?: LabelOverride;
  offset_mm?: OffsetMm;
  start: IntPoint;
}
export interface Fixture {
  anchor?: IntPoint | null;
  fixture_type: FixtureType;
  footprint?: IntPolygon | null;
  id: Id4;
  rotation_udeg?: RotationUdeg;
}
export interface Furniture1 {
  footprint: IntPolygon;
  furniture_type: FurnitureType;
  id: Id5;
  rotation_udeg?: RotationUdeg1;
}
export interface Opening {
  height_mm: HeightMm;
  hinge?: DoorHinge | null;
  id: Id7;
  kind: OpeningKind;
  offset_from_wall_start_mm: OffsetFromWallStartMm;
  sill_height_mm?: SillHeightMm;
  swing?: DoorSwing | null;
  wall_id: WallId;
  width_mm: WidthMm;
}
export interface RoomGeometry {
  id: Id8;
  locked?: Locked;
  name?: Name1;
  polygon: IntPolygon;
  requirement_id?: RequirementId;
  room_type: RoomType;
}
/**
 * Explicit non-room site geometry with a declared architectural purpose.
 */
export interface PurposefulSiteSpace {
  id: Id9;
  kind: SiteSpaceKind;
  label?: Label;
  polygon: IntPolygon;
  source?: SiteSpaceSource;
}
export interface Stair {
  direction_udeg: DirectionUdeg;
  floor_height_mm: FloorHeightMm;
  footprint: IntPolygon;
  headroom_mm?: HeadroomMm;
  id: Id10;
  landing_depth_mm: LandingDepthMm;
  number_of_risers: NumberOfRisers;
  riser_mm: RiserMm;
  stair_type: StairType;
  tread_mm: TreadMm;
  width_mm: WidthMm1;
}
export interface Wall {
  axis: AxisSegment;
  category: WallCategory;
  construction_type?: ConstructionType;
  height_mm: HeightMm1;
  id: Id11;
  thickness_mm: ThicknessMm;
}
export interface AxisSegment {
  end: IntPoint;
  start: IntPoint;
}
export interface GenerationMetadata {
  completed_at?: CompletedAt;
  input_hash?: InputHash;
  rule_bundle_hash?: RuleBundleHash;
  seed?: Seed;
  solver_name?: SolverName;
  solver_parameters?: SolverParameters;
  solver_step_mm?: SolverStepMm;
  solver_version?: SolverVersion;
  started_at?: StartedAt;
}
export interface MetadataItem {
  key: Key;
  value: Value;
}
export interface Orientation {
  north_rotation_udeg: NorthRotationUdeg;
  source: OrientationSource;
  verified: Verified;
}
export interface Plot {
  boundary: IntPolygon;
  closure_report?: ClosureReport | null;
  declared_measurements?: DeclaredMeasurements;
  edge_ids: EdgeIds;
  geometry_type: PlotGeometryType;
  id: Id12;
  input_source: PlotInputSource;
  verification_status: VerificationStatus;
}
export interface ClosureReport {
  accepted: Accepted;
  closure_error_mm: ClosureErrorMm;
  tolerance_mm: ToleranceMm;
}
export interface DeclaredMeasurement {
  exact_mm_decimal: ExactMmDecimal;
  input_unit: LengthUnit;
  input_value: InputValue;
  label: Label1;
  quantized_mm: QuantizedMm;
  rounding_delta_mm_decimal: RoundingDeltaMmDecimal;
}
export interface Road {
  id: Id13;
  name?: Name2;
  plot_edge_ids: PlotEdgeIds;
  primary_access?: PrimaryAccess;
  width_mm?: WidthMm2;
}
export interface RoomRequirement {
  adjacency_preferences?: AdjacencyPreferences;
  adjacency_prohibitions?: AdjacencyProhibitions;
  aspect_ratio?: AspectRatioRange | null;
  daylight_priority?: DaylightPriority;
  floor_preference?: FloorPreference;
  id: Id14;
  locked?: Locked1;
  max_area_mm2?: MaxAreaMm2;
  max_depth_mm?: MaxDepthMm;
  max_width_mm?: MaxWidthMm;
  min_area_mm2: MinAreaMm2;
  min_depth_mm: MinDepthMm;
  min_width_mm: MinWidthMm;
  preferred_area_mm2?: PreferredAreaMm2;
  preferred_depth_mm?: PreferredDepthMm;
  preferred_width_mm?: PreferredWidthMm;
  privacy_priority?: PrivacyPriority;
  quantity?: Quantity;
  room_type: RoomType;
  user_priority?: UserPriority;
  vastu_profile_refs?: VastuProfileRefs;
  ventilation_priority?: VentilationPriority;
}
export interface AdjacencyPreference {
  max_gap_mm?: MaxGapMm;
  min_shared_length_mm?: MinSharedLengthMm;
  target_room_type: RoomType;
  weight: Weight;
}
export interface AdjacencyProhibition {
  hard?: Hard;
  target_room_type: RoomType;
}
export interface AspectRatioRange {
  max_ratio_milli: MaxRatioMilli;
  min_ratio_milli: MinRatioMilli;
}
export interface ScoringSummary {
  components?: Components;
  mode: Mode;
  overall_basis_points: OverallBasisPoints;
}
export interface ScoreComponent {
  key: Key1;
  score_basis_points: ScoreBasisPoints;
  weight_basis_points: WeightBasisPoints;
}
export interface ValidationReport {
  errors?: Errors;
  informational?: Informational;
  valid: Valid;
  warnings?: Warnings;
}
export interface ValidationResult {
  check_id: CheckId;
  entity_refs?: EntityRefs;
  evidence?: Evidence;
  message_code: MessageCode;
  severity: ValidationSeverity;
  validator_version: ValidatorVersion;
}
export interface EvidenceItem {
  key: Key2;
  value: Value1;
}
export interface VastuAnalysis {
  major_violations?: MajorViolations;
  minor_compromises?: MinorCompromises;
  overall_basis_points?: OverallBasisPoints1;
  results?: Results;
  spec_version: SpecVersion;
}
export interface VastuResult {
  earned_weight?: EarnedWeight;
  entity_refs?: EntityRefs1;
  geometry_evidence?: GeometryEvidence;
  measured_evidence?: MeasuredEvidence;
  raw_weight?: RawWeight;
  rule_id: RuleId;
  rule_version: RuleVersion;
  status: VastuStatus;
}
