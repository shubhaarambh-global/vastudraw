import assert from "node:assert/strict";
import test from "node:test";

import type { PlanDocument } from "@ai-vastu/contracts";

import {
  buildFloorRenderModel,
  createPlanRenderModels,
  createPlanTransform,
} from "./professional-plan-model.ts";

function must<T>(value: T | undefined): T {
  assert.notEqual(value, undefined);
  return value as T;
}

function rectangle(x0: number, y0: number, x1: number, y1: number) {
  return {
    outer: [
      { x_mm: x0, y_mm: y0 },
      { x_mm: x1, y_mm: y0 },
      { x_mm: x1, y_mm: y1 },
      { x_mm: x0, y_mm: y1 },
    ],
    holes: [],
  };
}

function floor(index: number) {
  return {
    id: `floor-${String(index)}`,
    index,
    name: index === 0 ? "Ground Floor" : "First Floor",
    elevation_mm: index * 3_000,
    floor_to_floor_mm: 3_000,
    boundary: rectangle(1_000, 1_000, 9_000, 7_000),
    rooms: [
      {
        id: `living-${String(index)}`,
        room_type: "living",
        name: "Living",
        polygon: rectangle(1_000, 1_000, 5_000, 4_000),
      },
      {
        id: `kitchen-${String(index)}`,
        room_type: "kitchen",
        name: null,
        polygon: rectangle(5_000, 1_000, 7_000, 4_000),
      },
      {
        id: `toilet-${String(index)}`,
        room_type: "common_toilet",
        name: null,
        polygon: rectangle(7_000, 1_000, 9_000, 4_000),
      },
      {
        id: `parking-${String(index)}`,
        room_type: "parking",
        name: "Parking",
        polygon: rectangle(1_000, 4_000, 4_000, 7_000),
      },
      {
        id: `stair-${String(index)}`,
        room_type: "staircase",
        name: "Stair",
        polygon: rectangle(4_000, 4_000, 6_300, 7_000),
      },
    ],
    site_spaces: [
      {
        id: `landscape-${String(index)}`,
        kind: "LANDSCAPE",
        polygon: rectangle(0, 0, 1_000, 8_000),
        label: "Garden",
        source: "SYSTEM_DERIVED",
      },
      {
        id: `access-${String(index)}`,
        kind: "VEHICLE_ACCESS",
        polygon: rectangle(1_000, 0, 4_000, 1_000),
        label: null,
        source: "SYSTEM_DERIVED",
      },
    ],
    walls: [
      {
        id: `wall-ext-${String(index)}`,
        axis: {
          start: { x_mm: 1_000, y_mm: 1_000 },
          end: { x_mm: 9_000, y_mm: 1_000 },
        },
        thickness_mm: 230,
        height_mm: 3_000,
        category: "EXTERNAL",
        construction_type: null,
      },
      {
        id: `wall-int-${String(index)}`,
        axis: {
          start: { x_mm: 5_000, y_mm: 1_000 },
          end: { x_mm: 5_000, y_mm: 4_000 },
        },
        thickness_mm: 115,
        height_mm: 3_000,
        category: "INTERNAL",
        construction_type: null,
      },
      {
        id: `wall-window-${String(index)}`,
        axis: {
          start: { x_mm: 1_000, y_mm: 7_000 },
          end: { x_mm: 9_000, y_mm: 7_000 },
        },
        thickness_mm: 230,
        height_mm: 3_000,
        category: "EXTERNAL",
        construction_type: null,
      },
    ],
    openings: [
      {
        id: `door-${String(index)}`,
        wall_id: `wall-int-${String(index)}`,
        kind: "DOOR",
        offset_from_wall_start_mm: 900,
        width_mm: 900,
        height_mm: 2_100,
        sill_height_mm: 0,
        hinge: null,
        swing: "NONE",
      },
      {
        id: `window-${String(index)}`,
        wall_id: `wall-window-${String(index)}`,
        kind: "WINDOW",
        offset_from_wall_start_mm: 2_000,
        width_mm: 1_500,
        height_mm: 1_200,
        sill_height_mm: 900,
        hinge: null,
        swing: null,
      },
    ],
    stairs: [
      {
        id: `canonical-stair-${String(index)}`,
        stair_type: "DOG_LEGGED",
        footprint: rectangle(4_000, 4_000, 6_300, 7_000),
        width_mm: 1_000,
        riser_mm: 150,
        tread_mm: 270,
        number_of_risers: 20,
        floor_height_mm: 3_000,
        landing_depth_mm: 1_000,
        direction_udeg: 0,
        headroom_mm: 2_100,
      },
    ],
    fixtures: [],
    furniture: [],
    dimensions: [],
    annotations: [],
  };
}

function document(): PlanDocument {
  return {
    schema_version: "1.1.0",
    project_id: "project",
    revision_id: "revision",
    canonical_units: "mm",
    plot: {
      id: "plot",
      geometry_type: "RECTANGLE",
      boundary: rectangle(0, 0, 10_000, 8_000),
      edge_ids: ["a", "b", "c", "d"],
      input_source: "MANUAL",
      verification_status: "USER_VERIFIED",
      declared_measurements: [],
    },
    orientation: {
      north_rotation_udeg: 90_000_000,
      source: "USER",
      verified: true,
    },
    roads: [
      {
        id: "east-road",
        name: "East Road",
        plot_edge_ids: ["b"],
        width_mm: 6_000,
        primary_access: true,
      },
    ],
    buildable_area: {
      polygon: rectangle(1_000, 1_000, 9_000, 7_000),
      setbacks: [],
    },
    room_requirements: [],
    floors: [floor(0), floor(1)],
    vastu_spec_version: "test",
    regulation_spec_version: null,
    vastu_analysis: {
      spec_version: "test",
      results: [],
      overall_basis_points: null,
      major_violations: 0,
      minor_compromises: 0,
    },
    validation: { valid: true, errors: [], warnings: [], informational: [] },
    scoring: { mode: "test", overall_basis_points: 0, components: [] },
    assumptions: [],
    generation_metadata: { solver_parameters: [] },
    content_hash: "a".repeat(64),
  } as unknown as PlanDocument;
}

void test("professional render model preserves orientation and line hierarchy", () => {
  const plan = document();
  const model = buildFloorRenderModel(plan, must(plan.floors[0]));
  const external = model.walls.find((wall) => wall.category === "EXTERNAL");
  const internal = model.walls.find((wall) => wall.category === "INTERNAL");
  assert.ok(external);
  assert.ok(internal);
  assert.ok(external.thicknessPx > internal.thicknessPx);
  const transform = createPlanTransform(plan.plot.boundary);
  assert.ok(
    transform.point({ x_mm: 0, y_mm: 8_000 }).y <
      transform.point({ x_mm: 0, y_mm: 0 }).y,
  );
  assert.ok(model.north.end.x > model.north.start.x);
  assert.ok(Math.abs(model.north.end.y - model.north.start.y) < 0.001);
});

void test("canonical openings alone produce deterministic door and window symbols", () => {
  const first = must(createPlanRenderModels(document())[0]);
  const second = must(createPlanRenderModels(document())[0]);
  assert.equal(first.doors.length, 1);
  assert.equal(first.windows.length, 1);
  assert.equal(must(first.windows[0]).lines.length, 3);
  assert.ok(must(first.doors[0]).arcPoints.length > 4);
  assert.equal(must(first.doors[0]).derivedSwing, true);
  assert.deepEqual(first.doors, second.doors);
  const withoutOpenings = document();
  const floorWithoutOpenings = {
    ...must(withoutOpenings.floors[0]),
    openings: [],
  };
  const model = buildFloorRenderModel(withoutOpenings, floorWithoutOpenings);
  assert.deepEqual(model.doors, []);
  assert.deepEqual(model.windows, []);
});

void test("room labels, dimensions, north, scale, site spaces, and parking are present", () => {
  const model = must(createPlanRenderModels(document())[0]);
  assert.ok(
    model.rooms.every(
      (room) => room.title.length > 0 && room.dimension.includes("m"),
    ),
  );
  assert.equal(
    model.dimensions.filter((item) => item.category === "site").length,
    2,
  );
  assert.equal(
    model.siteSpaces.map((space) => space.kind).join(","),
    "LANDSCAPE,VEHICLE_ACCESS",
  );
  assert.equal(model.scaleLabel, "5 m");
  assert.ok(model.scaleBar.end.x > model.scaleBar.start.x);
  assert.equal(model.roads.length, 1);
  assert.equal(must(model.roads[0]).primaryAccess, true);
  assert.ok(model.symbols.some((symbol) => symbol.kind === "vehicle"));
});

void test("derived fixtures and furniture remain inside their canonical rooms", () => {
  const model = must(createPlanRenderModels(document())[0]);
  for (const symbol of model.symbols) {
    const room = model.rooms.find(
      (candidate) => candidate.id === symbol.roomId,
    );
    assert.ok(room);
    const xs = room.points.map((point) => point.x);
    const ys = room.points.map((point) => point.y);
    assert.ok(symbol.x >= Math.min(...xs));
    assert.ok(symbol.y >= Math.min(...ys));
    assert.ok(symbol.x + symbol.width <= Math.max(...xs));
    assert.ok(symbol.y + symbol.height <= Math.max(...ys));
  }
  assert.ok(model.symbols.some((symbol) => symbol.kind === "sanitary"));
  assert.ok(model.symbols.some((symbol) => symbol.kind === "kitchen-counter"));
});

void test("canonical fixtures and furniture take presentation precedence", () => {
  const plan = document();
  const source = must(plan.floors[0]);
  const canonicalFloor = {
    ...source,
    furniture: [
      {
        id: "canonical-bed",
        furniture_type: "bed",
        footprint: rectangle(1_200, 1_200, 2_700, 3_200),
        rotation_udeg: 0,
      },
    ],
    fixtures: [
      {
        id: "canonical-wc",
        fixture_type: "wc",
        footprint: rectangle(7_300, 1_300, 8_100, 2_200),
        anchor: null,
        rotation_udeg: 0,
      },
    ],
  } as unknown as (typeof plan.floors)[number];
  const model = buildFloorRenderModel(plan, canonicalFloor);
  assert.equal(model.canonicalFurniture.length, 1);
  assert.equal(model.canonicalFixtures.length, 1);
  assert.ok(!model.symbols.some((symbol) => symbol.kind === "sofa"));
  assert.ok(!model.symbols.some((symbol) => symbol.kind === "sanitary"));
  assert.ok(model.symbols.some((symbol) => symbol.kind === "vehicle"));
});

void test("multi-floor models are separate and aligned canonical stairs stay aligned", () => {
  const models = createPlanRenderModels(document());
  assert.deepEqual(
    models.map((model) => model.floorName),
    ["Ground Floor", "First Floor"],
  );
  assert.notEqual(must(models[0]).floorId, must(models[1]).floorId);
  assert.deepEqual(
    must(must(models[0]).stairs[0]).points,
    must(must(models[1]).stairs[0]).points,
  );
  assert.ok(models.every((model) => must(model.stairs[0]).treads.length >= 4));
  assert.ok(
    models.every(
      (model) =>
        must(model.stairs[0]).arrow.end.y < must(model.stairs[0]).arrow.start.y,
    ),
  );
});

void test("rendering is deterministic, candidate-specific, and cannot mutate content", () => {
  const plan = document();
  const before = JSON.stringify(plan);
  const first = createPlanRenderModels(plan);
  const second = createPlanRenderModels(plan);
  assert.equal(JSON.stringify(first), JSON.stringify(second));
  assert.equal(JSON.stringify(plan), before);
  const changed = document();
  const changedFloor = {
    ...must(changed.floors[0]),
    rooms: must(changed.floors[0]).rooms?.map((room) =>
      room.id === "living-0"
        ? { ...room, polygon: rectangle(1_000, 1_000, 4_500, 4_000) }
        : room,
    ),
  } as unknown as (typeof changed.floors)[number];
  const changedModel = buildFloorRenderModel(changed, changedFloor);
  assert.notDeepEqual(
    must(must(first[0]).rooms[0]).points,
    must(changedModel.rooms[0]).points,
  );
});
