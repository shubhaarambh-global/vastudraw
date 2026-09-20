import type {
  Floor,
  IntPoint,
  IntPolygon,
  Opening,
  PlanDocument,
  RoomGeometry,
  Stair,
  Wall,
} from "@ai-vastu/contracts";

export const PLAN_CANVAS_WIDTH = 960;
export const PLAN_CANVAS_HEIGHT = 680;
const WORLD_PADDING_MM = 1_200;

export interface ScreenPoint {
  readonly x: number;
  readonly y: number;
}

export interface ScreenSegment {
  readonly start: ScreenPoint;
  readonly end: ScreenPoint;
}

export interface SiteSpaceLike {
  readonly id: string;
  readonly kind:
    | "LIGHTWELL"
    | "LANDSCAPE"
    | "OPEN_SPACE"
    | "UTILITY_YARD"
    | "VEHICLE_ACCESS"
    | "SHAFT"
    | "PORCH";
  readonly polygon: IntPolygon;
  readonly label?: string | null;
}

interface RenderableFloor extends Floor {
  readonly site_spaces?: readonly SiteSpaceLike[];
}

export interface WallGraphic extends ScreenSegment {
  readonly id: string;
  readonly category: Wall["category"];
  readonly thicknessPx: number;
}

export interface RoadGraphic {
  readonly id: string;
  readonly name: string;
  readonly segments: readonly ScreenSegment[];
  readonly widthPx: number;
  readonly primaryAccess: boolean;
}

export interface DoorGraphic {
  readonly id: string;
  readonly leaf: ScreenSegment;
  readonly arcPoints: readonly ScreenPoint[];
  readonly derivedSwing: boolean;
  readonly sliding: boolean;
}

export interface WindowGraphic {
  readonly id: string;
  readonly lines: readonly ScreenSegment[];
}

export interface RoomGraphic {
  readonly id: string;
  readonly roomType: string;
  readonly points: readonly ScreenPoint[];
  readonly labelPoint: ScreenPoint;
  readonly title: string;
  readonly dimension: string;
}

export interface StairGraphic {
  readonly id: string;
  readonly points: readonly ScreenPoint[];
  readonly treads: readonly ScreenSegment[];
  readonly landing: ScreenSegment;
  readonly divider: ScreenSegment;
  readonly arrow: ScreenSegment;
}

export interface SymbolGraphic {
  readonly roomId: string;
  readonly kind:
    | "bed"
    | "sofa"
    | "dining"
    | "sanitary"
    | "kitchen-counter"
    | "vehicle"
    | "desk";
  readonly x: number;
  readonly y: number;
  readonly width: number;
  readonly height: number;
}

export interface DimensionGraphic {
  readonly category: "site" | "building";
  readonly sourceStart: ScreenPoint;
  readonly sourceEnd: ScreenPoint;
  readonly start: ScreenPoint;
  readonly end: ScreenPoint;
  readonly label: string;
}

export interface SiteSpaceGraphic {
  readonly id: string;
  readonly kind: SiteSpaceLike["kind"];
  readonly label: string;
  readonly points: readonly ScreenPoint[];
  readonly labelPoint: ScreenPoint;
}

export interface CanonicalObjectGraphic {
  readonly id: string;
  readonly kind: string;
  readonly points: readonly ScreenPoint[];
  readonly anchor: ScreenPoint | null;
}

export interface PlanTransform {
  readonly scale: number;
  readonly point: (point: Pick<IntPoint, "x_mm" | "y_mm">) => ScreenPoint;
}

export interface FloorRenderModel {
  readonly floorId: string;
  readonly floorIndex: number;
  readonly floorName: string;
  readonly plotPoints: readonly ScreenPoint[];
  readonly buildablePoints: readonly ScreenPoint[];
  readonly floorPoints: readonly ScreenPoint[];
  readonly roads: readonly RoadGraphic[];
  readonly siteSpaces: readonly SiteSpaceGraphic[];
  readonly rooms: readonly RoomGraphic[];
  readonly walls: readonly WallGraphic[];
  readonly doors: readonly DoorGraphic[];
  readonly windows: readonly WindowGraphic[];
  readonly stairs: readonly StairGraphic[];
  readonly symbols: readonly SymbolGraphic[];
  readonly canonicalFurniture: readonly CanonicalObjectGraphic[];
  readonly canonicalFixtures: readonly CanonicalObjectGraphic[];
  readonly dimensions: readonly DimensionGraphic[];
  readonly north: ScreenSegment;
  readonly northLabel: ScreenPoint;
  readonly scaleBar: ScreenSegment;
  readonly scaleLabel: string;
  readonly transform: PlanTransform;
}

interface Bounds {
  readonly minX: number;
  readonly minY: number;
  readonly maxX: number;
  readonly maxY: number;
}

function required<T>(value: T | undefined, message: string): T {
  if (value === undefined) {
    throw new Error(message);
  }
  return value;
}

const SANITARY_TYPES = new Set([
  "attached_toilet",
  "common_toilet",
  "powder_room",
  "bath",
  "servant_toilet",
]);
const BEDROOM_TYPES = new Set([
  "master_bedroom",
  "bedroom",
  "parents_bedroom",
  "guest_bedroom",
  "children_bedroom",
  "servant_room",
]);

function polygonBounds(polygon: IntPolygon): Bounds {
  const xs = polygon.outer.map((point) => point.x_mm);
  const ys = polygon.outer.map((point) => point.y_mm);
  return {
    minX: Math.min(...xs),
    minY: Math.min(...ys),
    maxX: Math.max(...xs),
    maxY: Math.max(...ys),
  };
}

export function createPlanTransform(plot: IntPolygon): PlanTransform {
  const bounds = polygonBounds(plot);
  const minX = bounds.minX - WORLD_PADDING_MM;
  const minY = bounds.minY - WORLD_PADDING_MM;
  const maxX = bounds.maxX + WORLD_PADDING_MM;
  const maxY = bounds.maxY + WORLD_PADDING_MM;
  const scale = Math.min(
    (PLAN_CANVAS_WIDTH - 48) / Math.max(1, maxX - minX),
    (PLAN_CANVAS_HEIGHT - 48) / Math.max(1, maxY - minY),
  );
  const drawnWidth = (maxX - minX) * scale;
  const drawnHeight = (maxY - minY) * scale;
  const left = (PLAN_CANVAS_WIDTH - drawnWidth) / 2;
  const top = (PLAN_CANVAS_HEIGHT - drawnHeight) / 2;
  return {
    scale,
    point: (point) => ({
      x: left + (point.x_mm - minX) * scale,
      y: top + (maxY - point.y_mm) * scale,
    }),
  };
}

function pointAt(wall: Wall, offsetMm: number): IntPoint {
  const dx = wall.axis.end.x_mm - wall.axis.start.x_mm;
  const dy = wall.axis.end.y_mm - wall.axis.start.y_mm;
  const length = Math.hypot(dx, dy);
  const ratio = offsetMm / length;
  return {
    x_mm: wall.axis.start.x_mm + dx * ratio,
    y_mm: wall.axis.start.y_mm + dy * ratio,
  };
}

function openingEnds(
  opening: Opening,
  wall: Wall,
): readonly [IntPoint, IntPoint] {
  return [
    pointAt(wall, opening.offset_from_wall_start_mm),
    pointAt(wall, opening.offset_from_wall_start_mm + opening.width_mm),
  ];
}

function wallSegments(
  wall: Wall,
  openings: readonly Opening[],
  transform: PlanTransform,
): WallGraphic[] {
  const length = Math.hypot(
    wall.axis.end.x_mm - wall.axis.start.x_mm,
    wall.axis.end.y_mm - wall.axis.start.y_mm,
  );
  const ordered = openings
    .filter((opening) => opening.wall_id === wall.id)
    .sort(
      (first, second) =>
        first.offset_from_wall_start_mm - second.offset_from_wall_start_mm ||
        first.id.localeCompare(second.id),
    );
  const ranges: Array<readonly [number, number]> = [];
  let cursor = 0;
  for (const opening of ordered) {
    if (opening.offset_from_wall_start_mm > cursor) {
      ranges.push([cursor, opening.offset_from_wall_start_mm]);
    }
    cursor = opening.offset_from_wall_start_mm + opening.width_mm;
  }
  if (cursor < length) {
    ranges.push([cursor, length]);
  }
  return ranges.map(([start, end], index) => ({
    id: `${wall.id}:${String(index)}`,
    category: wall.category,
    thicknessPx: Math.max(2, wall.thickness_mm * transform.scale),
    start: transform.point(pointAt(wall, start)),
    end: transform.point(pointAt(wall, end)),
  }));
}

function roomsTouchingWall(
  wall: Wall,
  rooms: readonly RoomGeometry[],
): RoomGeometry[] {
  const wallMinX = Math.min(wall.axis.start.x_mm, wall.axis.end.x_mm);
  const wallMaxX = Math.max(wall.axis.start.x_mm, wall.axis.end.x_mm);
  const wallMinY = Math.min(wall.axis.start.y_mm, wall.axis.end.y_mm);
  const wallMaxY = Math.max(wall.axis.start.y_mm, wall.axis.end.y_mm);
  return [...rooms]
    .filter((room) => {
      const bounds = polygonBounds(room.polygon);
      if (wallMinX === wallMaxX) {
        return (
          (wallMinX === bounds.minX || wallMinX === bounds.maxX) &&
          Math.min(wallMaxY, bounds.maxY) - Math.max(wallMinY, bounds.minY) > 0
        );
      }
      return (
        wallMinY === wallMaxY &&
        (wallMinY === bounds.minY || wallMinY === bounds.maxY) &&
        Math.min(wallMaxX, bounds.maxX) - Math.max(wallMinX, bounds.minX) > 0
      );
    })
    .sort((first, second) => first.id.localeCompare(second.id));
}

function normalIntoRoom(
  wall: Wall,
  rooms: readonly RoomGeometry[],
): ScreenPoint {
  const dx = wall.axis.end.x_mm - wall.axis.start.x_mm;
  const dy = wall.axis.end.y_mm - wall.axis.start.y_mm;
  const length = Math.hypot(dx, dy);
  let normal = { x: -dy / length, y: dx / length };
  const candidates = roomsTouchingWall(wall, rooms);
  const room =
    candidates.find((candidate) => SANITARY_TYPES.has(candidate.room_type)) ??
    candidates[0];
  if (!room) {
    return normal;
  }
  const bounds = polygonBounds(room.polygon);
  const roomX = (bounds.minX + bounds.maxX) / 2;
  const roomY = (bounds.minY + bounds.maxY) / 2;
  const wallX = (wall.axis.start.x_mm + wall.axis.end.x_mm) / 2;
  const wallY = (wall.axis.start.y_mm + wall.axis.end.y_mm) / 2;
  if ((roomX - wallX) * normal.x + (roomY - wallY) * normal.y < 0) {
    normal = { x: -normal.x, y: -normal.y };
  }
  return normal;
}

function interpolateArc(
  center: IntPoint,
  start: IntPoint,
  end: IntPoint,
  transform: PlanTransform,
): ScreenPoint[] {
  const radius = Math.hypot(start.x_mm - center.x_mm, start.y_mm - center.y_mm);
  const startAngle = Math.atan2(
    start.y_mm - center.y_mm,
    start.x_mm - center.x_mm,
  );
  const endAngle = Math.atan2(end.y_mm - center.y_mm, end.x_mm - center.x_mm);
  let delta = ((endAngle - startAngle + Math.PI) % (2 * Math.PI)) - Math.PI;
  if (delta < -Math.PI) {
    delta += 2 * Math.PI;
  }
  return Array.from({ length: 9 }, (_, index) => {
    const angle = startAngle + (delta * index) / 8;
    return transform.point({
      x_mm: center.x_mm + Math.cos(angle) * radius,
      y_mm: center.y_mm + Math.sin(angle) * radius,
    });
  });
}

function doorGraphic(
  opening: Opening,
  wall: Wall,
  rooms: readonly RoomGeometry[],
  transform: PlanTransform,
): DoorGraphic {
  const [start, end] = openingEnds(opening, wall);
  const hingeIsStart = opening.hinge !== "RIGHT";
  const hinge = hingeIsStart ? start : end;
  const closedEnd = hingeIsStart ? end : start;
  let normal = normalIntoRoom(wall, rooms);
  if (opening.swing === "OUT") {
    normal = { x: -normal.x, y: -normal.y };
  }
  const openEnd = {
    x_mm: hinge.x_mm + normal.x * opening.width_mm,
    y_mm: hinge.y_mm + normal.y * opening.width_mm,
  };
  const sliding = opening.swing === "SLIDING";
  return {
    id: opening.id,
    leaf: {
      start: transform.point(hinge),
      end: transform.point(sliding ? closedEnd : openEnd),
    },
    arcPoints: sliding
      ? []
      : interpolateArc(hinge, closedEnd, openEnd, transform),
    derivedSwing:
      opening.hinge === null ||
      opening.hinge === undefined ||
      opening.swing === null ||
      opening.swing === undefined ||
      opening.swing === "NONE",
    sliding,
  };
}

function windowGraphic(
  opening: Opening,
  wall: Wall,
  transform: PlanTransform,
): WindowGraphic {
  const [start, end] = openingEnds(opening, wall);
  const length = Math.hypot(end.x_mm - start.x_mm, end.y_mm - start.y_mm);
  const normal = {
    x: -(end.y_mm - start.y_mm) / length,
    y: (end.x_mm - start.x_mm) / length,
  };
  return {
    id: opening.id,
    lines: [-0.28, 0, 0.28].map((factor) => ({
      start: transform.point({
        x_mm: start.x_mm + normal.x * wall.thickness_mm * factor,
        y_mm: start.y_mm + normal.y * wall.thickness_mm * factor,
      }),
      end: transform.point({
        x_mm: end.x_mm + normal.x * wall.thickness_mm * factor,
        y_mm: end.y_mm + normal.y * wall.thickness_mm * factor,
      }),
    })),
  };
}

function formatDimension(mm: number): string {
  return `${(mm / 1_000).toFixed(mm % 1_000 === 0 ? 1 : 2)} m`;
}

function roomGraphic(
  room: RoomGeometry,
  transform: PlanTransform,
): RoomGraphic {
  const bounds = polygonBounds(room.polygon);
  const rectangular =
    room.polygon.outer.length === 4 &&
    room.polygon.outer.every(
      (point) =>
        (point.x_mm === bounds.minX || point.x_mm === bounds.maxX) &&
        (point.y_mm === bounds.minY || point.y_mm === bounds.maxY),
    );
  return {
    id: room.id,
    roomType: room.room_type,
    points: room.polygon.outer.map(transform.point),
    labelPoint: transform.point({
      x_mm: (bounds.minX + bounds.maxX) / 2,
      y_mm: (bounds.minY + bounds.maxY) / 2,
    }),
    title: (room.name ?? room.room_type).replaceAll("_", " ").toUpperCase(),
    dimension: `${rectangular ? "" : "MAX "}${formatDimension(bounds.maxX - bounds.minX)} × ${formatDimension(bounds.maxY - bounds.minY)}`,
  };
}

function symbolGraphic(
  room: RoomGeometry,
  transform: PlanTransform,
): SymbolGraphic | null {
  const bounds = polygonBounds(room.polygon);
  const inner = {
    minX: bounds.minX + 220,
    minY: bounds.minY + 220,
    maxX: bounds.maxX - 220,
    maxY: bounds.maxY - 220,
  };
  const width = inner.maxX - inner.minX;
  const depth = inner.maxY - inner.minY;
  if (width <= 500 || depth <= 500 || room.room_type === "staircase") {
    return null;
  }
  let kind: SymbolGraphic["kind"] | null = null;
  let symbolWidth = width * 0.7;
  let symbolDepth = depth * 0.58;
  if (BEDROOM_TYPES.has(room.room_type)) {
    kind = "bed";
    symbolWidth = Math.min(1_800, width * 0.68);
    symbolDepth = Math.min(2_100, depth * 0.7);
  } else if (["living", "drawing", "family_lounge"].includes(room.room_type)) {
    kind = "sofa";
    symbolWidth = Math.min(2_400, width * 0.74);
    symbolDepth = Math.min(850, depth * 0.3);
  } else if (room.room_type === "dining") {
    kind = "dining";
    symbolWidth = Math.min(1_800, width * 0.58);
    symbolDepth = Math.min(1_000, depth * 0.42);
  } else if (SANITARY_TYPES.has(room.room_type)) {
    kind = "sanitary";
    symbolWidth = Math.min(1_200, width * 0.72);
    symbolDepth = Math.min(1_500, depth * 0.68);
  } else if (room.room_type === "kitchen") {
    kind = "kitchen-counter";
    symbolWidth = Math.min(width, Math.max(900, width * 0.9));
    symbolDepth = Math.min(600, depth * 0.28);
  } else if (["parking", "garage"].includes(room.room_type)) {
    kind = "vehicle";
    symbolWidth = Math.min(1_800, width * 0.72);
    symbolDepth = Math.min(4_500, depth * 0.8);
  } else if (["study", "home_office"].includes(room.room_type)) {
    kind = "desk";
    symbolWidth = Math.min(1_500, width * 0.62);
    symbolDepth = Math.min(700, depth * 0.3);
  }
  if (!kind) {
    return null;
  }
  let centerX = (inner.minX + inner.maxX) / 2;
  let centerY = (inner.minY + inner.maxY) / 2;
  if (kind === "bed") {
    centerX = inner.minX + symbolWidth / 2;
    centerY = inner.maxY - symbolDepth / 2;
  } else if (
    ["sofa", "dining", "sanitary", "kitchen-counter", "desk"].includes(kind)
  ) {
    centerX = inner.minX + symbolWidth / 2;
    centerY = inner.minY + symbolDepth / 2;
  } else if (kind === "vehicle") {
    centerX = inner.minX + symbolWidth / 2;
  }
  const first = transform.point({
    x_mm: centerX - symbolWidth / 2,
    y_mm: centerY - symbolDepth / 2,
  });
  const second = transform.point({
    x_mm: centerX + symbolWidth / 2,
    y_mm: centerY + symbolDepth / 2,
  });
  return {
    roomId: room.id,
    kind,
    x: Math.min(first.x, second.x),
    y: Math.min(first.y, second.y),
    width: Math.abs(second.x - first.x),
    height: Math.abs(second.y - first.y),
  };
}

function stairGraphic(stair: Stair, transform: PlanTransform): StairGraphic {
  const bounds = polygonBounds(stair.footprint);
  const horizontal = bounds.maxX - bounds.minX >= bounds.maxY - bounds.minY;
  const runMin = horizontal ? bounds.minX : bounds.minY;
  const runMax = horizontal ? bounds.maxX : bounds.maxY;
  const crossMin = horizontal ? bounds.minY : bounds.minX;
  const crossMax = horizontal ? bounds.maxY : bounds.maxX;
  const landingAt = (runMin + runMax) / 2;
  const landingDepth = Math.min(
    stair.landing_depth_mm,
    (runMax - runMin) * 0.35,
  );
  const leftEnd = landingAt - landingDepth / 2;
  const rightStart = landingAt + landingDepth / 2;
  const count = Math.max(
    2,
    Math.min(
      Math.floor(stair.number_of_risers / 2),
      Math.floor((runMax - runMin - landingDepth) / stair.tread_mm),
    ),
  );
  const toSegment = (position: number): ScreenSegment => ({
    start: transform.point(
      horizontal
        ? { x_mm: position, y_mm: crossMin }
        : { x_mm: crossMin, y_mm: position },
    ),
    end: transform.point(
      horizontal
        ? { x_mm: position, y_mm: crossMax }
        : { x_mm: crossMax, y_mm: position },
    ),
  });
  const treads: ScreenSegment[] = [];
  for (let index = 1; index <= count; index += 1) {
    const ratio = index / (count + 1);
    treads.push(toSegment(runMin + (leftEnd - runMin) * ratio));
    treads.push(toSegment(rightStart + (runMax - rightStart) * ratio));
  }
  const center = {
    x_mm: (bounds.minX + bounds.maxX) / 2,
    y_mm: (bounds.minY + bounds.maxY) / 2,
  };
  const theta = (stair.direction_udeg / 1_000_000) * (Math.PI / 180);
  const length =
    Math.min(bounds.maxX - bounds.minX, bounds.maxY - bounds.minY) * 0.7;
  const direction = { x: Math.sin(theta), y: Math.cos(theta) };
  return {
    id: stair.id,
    points: stair.footprint.outer.map(transform.point),
    treads,
    landing: toSegment(landingAt),
    divider: {
      start: transform.point(
        horizontal
          ? { x_mm: runMin, y_mm: (crossMin + crossMax) / 2 }
          : { x_mm: (crossMin + crossMax) / 2, y_mm: runMin },
      ),
      end: transform.point(
        horizontal
          ? { x_mm: runMax, y_mm: (crossMin + crossMax) / 2 }
          : { x_mm: (crossMin + crossMax) / 2, y_mm: runMax },
      ),
    },
    arrow: {
      start: transform.point({
        x_mm: center.x_mm - direction.x * length * 0.5,
        y_mm: center.y_mm - direction.y * length * 0.5,
      }),
      end: transform.point({
        x_mm: center.x_mm + direction.x * length * 0.5,
        y_mm: center.y_mm + direction.y * length * 0.5,
      }),
    },
  };
}

function dimensionGraphic(
  start: IntPoint,
  end: IntPoint,
  offset: IntPoint,
  category: DimensionGraphic["category"],
  transform: PlanTransform,
): DimensionGraphic {
  return {
    category,
    sourceStart: transform.point(start),
    sourceEnd: transform.point(end),
    start: transform.point({
      x_mm: start.x_mm + offset.x_mm,
      y_mm: start.y_mm + offset.y_mm,
    }),
    end: transform.point({
      x_mm: end.x_mm + offset.x_mm,
      y_mm: end.y_mm + offset.y_mm,
    }),
    label: formatDimension(
      Math.hypot(end.x_mm - start.x_mm, end.y_mm - start.y_mm),
    ),
  };
}

function siteSpaceGraphic(
  space: SiteSpaceLike,
  transform: PlanTransform,
): SiteSpaceGraphic {
  const bounds = polygonBounds(space.polygon);
  return {
    id: space.id,
    kind: space.kind,
    label: (space.label ?? space.kind.replaceAll("_", " ")).toUpperCase(),
    points: space.polygon.outer.map(transform.point),
    labelPoint: transform.point({
      x_mm: (bounds.minX + bounds.maxX) / 2,
      y_mm: (bounds.minY + bounds.maxY) / 2,
    }),
  };
}

export function buildFloorRenderModel(
  document: PlanDocument,
  sourceFloor: Floor,
): FloorRenderModel {
  const floor = sourceFloor as RenderableFloor;
  const transform = createPlanTransform(document.plot.boundary);
  const rooms = floor.rooms ?? [];
  const walls = floor.walls ?? [];
  const openings = floor.openings ?? [];
  const wallIndex = new Map(walls.map((wall) => [wall.id, wall]));
  const plotBounds = polygonBounds(document.plot.boundary);
  const floorBoundary = floor.boundary ?? document.buildable_area.polygon;
  const floorBounds = polygonBounds(floorBoundary);
  const wallsGraphic = walls.flatMap((wall) =>
    wallSegments(wall, openings, transform),
  );
  const doors = openings
    .filter((opening) => opening.kind === "DOOR")
    .map((opening) =>
      doorGraphic(
        opening,
        required(
          wallIndex.get(opening.wall_id),
          "Door references an unknown wall.",
        ),
        rooms,
        transform,
      ),
    );
  const windows = openings
    .filter((opening) => opening.kind === "WINDOW")
    .map((opening) =>
      windowGraphic(
        opening,
        required(
          wallIndex.get(opening.wall_id),
          "Window references an unknown wall.",
        ),
        transform,
      ),
    );
  const derivedSymbols = rooms
    .map((room) => symbolGraphic(room, transform))
    .filter((symbol): symbol is SymbolGraphic => symbol !== null);
  const hasCanonicalFurniture = (floor.furniture ?? []).length > 0;
  const hasCanonicalFixtures = (floor.fixtures ?? []).length > 0;
  const symbols = derivedSymbols.filter((symbol) => {
    if (
      hasCanonicalFurniture &&
      ["bed", "sofa", "dining", "desk"].includes(symbol.kind)
    ) {
      return false;
    }
    if (
      hasCanonicalFixtures &&
      ["sanitary", "kitchen-counter"].includes(symbol.kind)
    ) {
      return false;
    }
    return true;
  });
  const dimensions: DimensionGraphic[] = [
    dimensionGraphic(
      { x_mm: plotBounds.minX, y_mm: plotBounds.minY },
      { x_mm: plotBounds.maxX, y_mm: plotBounds.minY },
      { x_mm: 0, y_mm: -900 },
      "site",
      transform,
    ),
    dimensionGraphic(
      { x_mm: plotBounds.maxX, y_mm: plotBounds.minY },
      { x_mm: plotBounds.maxX, y_mm: plotBounds.maxY },
      { x_mm: 900, y_mm: 0 },
      "site",
      transform,
    ),
  ];
  if (
    floorBounds.minX !== plotBounds.minX ||
    floorBounds.minY !== plotBounds.minY ||
    floorBounds.maxX !== plotBounds.maxX ||
    floorBounds.maxY !== plotBounds.maxY
  ) {
    dimensions.push(
      dimensionGraphic(
        { x_mm: floorBounds.minX, y_mm: floorBounds.maxY },
        { x_mm: floorBounds.maxX, y_mm: floorBounds.maxY },
        { x_mm: 0, y_mm: 550 },
        "building",
        transform,
      ),
    );
  }
  const northAngle =
    (document.orientation.north_rotation_udeg / 1_000_000) * (Math.PI / 180);
  const northStart = { x: PLAN_CANVAS_WIDTH - 74, y: 78 };
  const northEnd = {
    x: northStart.x + Math.sin(northAngle) * 42,
    y: northStart.y - Math.cos(northAngle) * 42,
  };
  const scaleStart = { x: 46, y: PLAN_CANVAS_HEIGHT - 32 };
  const plotEdges = new Map(
    document.plot.edge_ids.map((id, index) => [
      id,
      {
        start: required(
          document.plot.boundary.outer[index],
          "Plot edge start is missing.",
        ),
        end: required(
          document.plot.boundary.outer[
            (index + 1) % document.plot.boundary.outer.length
          ],
          "Plot edge end is missing.",
        ),
      },
    ]),
  );
  return {
    floorId: floor.id,
    floorIndex: floor.index,
    floorName: floor.name,
    plotPoints: document.plot.boundary.outer.map(transform.point),
    buildablePoints: document.buildable_area.polygon.outer.map(transform.point),
    floorPoints: floorBoundary.outer.map(transform.point),
    roads: (document.roads ?? []).map((road) => ({
      id: road.id,
      name: road.name ?? "Road",
      segments: road.plot_edge_ids.map((edgeId) => {
        const edge = required(
          plotEdges.get(edgeId),
          "Road references an unknown plot edge.",
        );
        return {
          start: transform.point(edge.start),
          end: transform.point(edge.end),
        };
      }),
      widthPx: Math.max(3, (road.width_mm ?? 900) * transform.scale),
      primaryAccess: road.primary_access === true,
    })),
    siteSpaces: (floor.site_spaces ?? []).map((space) =>
      siteSpaceGraphic(space, transform),
    ),
    rooms: rooms.map((room) => roomGraphic(room, transform)),
    walls: wallsGraphic,
    doors,
    windows,
    stairs: (floor.stairs ?? []).map((stair) => stairGraphic(stair, transform)),
    symbols,
    canonicalFurniture: (floor.furniture ?? []).map((item) => ({
      id: item.id,
      kind: item.furniture_type,
      points: item.footprint.outer.map(transform.point),
      anchor: null,
    })),
    canonicalFixtures: (floor.fixtures ?? []).map((item) => ({
      id: item.id,
      kind: item.fixture_type,
      points: item.footprint?.outer.map(transform.point) ?? [],
      anchor: item.anchor ? transform.point(item.anchor) : null,
    })),
    dimensions,
    north: { start: northStart, end: northEnd },
    northLabel: { x: northEnd.x, y: northEnd.y - 12 },
    scaleBar: {
      start: scaleStart,
      end: { x: scaleStart.x + 5_000 * transform.scale, y: scaleStart.y },
    },
    scaleLabel: "5 m",
    transform,
  };
}

export function createPlanRenderModels(
  document: PlanDocument,
): readonly FloorRenderModel[] {
  return [...document.floors]
    .sort((first, second) => first.index - second.index)
    .map((floor) => buildFloorRenderModel(document, floor));
}
