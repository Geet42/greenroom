import { convertToExcalidrawElements } from "@excalidraw/excalidraw";

// Recognizable system-design icon shapes, loaded into the Excalidraw library
// sidebar (SystemDesignBoard.jsx calls excalidrawAPI.updateLibrary with
// these) so candidates can drag a labeled "Database"/"Load Balancer"/etc.
// onto the canvas instead of building everything from generic
// rectangles/ellipses. Built from convertToExcalidrawElements skeletons
// (handles id/seed/version generation) rather than hand-crafted element
// JSON, which is fragile to get right by hand.
//
// Multi-element icons (e.g. the database cylinder) share a groupId so
// dragging the library item onto the canvas moves/resizes them as one unit.

const W = 140;
const H = 90;

function makeCylinder(name, label, backgroundColor) {
  const groupId = `lib-${name}-group`;
  // Cylinder illusion: body rectangle first (drawn underneath), then a top
  // and bottom ellipse drawn ON TOP to cover the rectangle's flat edges —
  // Excalidraw draws array entries in order, later = on top.
  const capH = H * 0.22;
  return convertToExcalidrawElements([
    {
      type: "rectangle", x: 0, y: capH / 2, width: W, height: H - capH,
      backgroundColor, strokeColor: "#1e1e1e", fillStyle: "solid", roundness: null,
      groupIds: [groupId],
    },
    {
      type: "ellipse", x: 0, y: 0, width: W, height: capH,
      backgroundColor, strokeColor: "#1e1e1e", fillStyle: "solid",
      groupIds: [groupId],
    },
    {
      type: "ellipse", x: 0, y: H - capH, width: W, height: capH,
      backgroundColor, strokeColor: "#1e1e1e", fillStyle: "solid",
      groupIds: [groupId],
    },
    {
      type: "text", x: 0, y: H + 6, width: W, text: label,
      fontSize: 14, textAlign: "center", strokeColor: "#1e1e1e",
      groupIds: [groupId],
    },
  ]);
}

function makeContainer(name, label, { type = "rectangle", backgroundColor, note } = {}) {
  const groupId = `lib-${name}-group`;
  const elements = [
    {
      type, x: 0, y: 0, width: W, height: H,
      backgroundColor, strokeColor: "#1e1e1e", fillStyle: "solid",
      label: { text: label, fontSize: 14 },
      groupIds: [groupId],
    },
  ];
  if (note) {
    elements.push({
      type: "text", x: 0, y: H + 6, width: W, text: note,
      fontSize: 11, textAlign: "center", strokeColor: "#5c5c5c",
      groupIds: [groupId],
    });
  }
  return convertToExcalidrawElements(elements);
}

function makeQueue(name, label, backgroundColor) {
  // Three stacked segments read as "a queue of items" at a glance, more so
  // than a single labeled box would.
  const groupId = `lib-${name}-group`;
  const segH = H / 3;
  const elements = [0, 1, 2].map((i) => ({
    type: "rectangle", x: 0, y: i * segH, width: W, height: segH,
    backgroundColor, strokeColor: "#1e1e1e", fillStyle: "solid", roundness: null,
    groupIds: [groupId],
  }));
  elements.push({
    type: "text", x: 0, y: H + 6, width: W, text: label,
    fontSize: 14, textAlign: "center", strokeColor: "#1e1e1e",
    groupIds: [groupId],
  });
  return convertToExcalidrawElements(elements);
}

function makeCloud(name, label, backgroundColor) {
  // No native cloud primitive — three overlapping ellipses plus a base
  // rectangle reads as a cloud silhouette well enough for a quick icon.
  const groupId = `lib-${name}-group`;
  return convertToExcalidrawElements([
    { type: "ellipse", x: 20, y: 10, width: 60, height: 45, backgroundColor, strokeColor: "#1e1e1e", fillStyle: "solid", groupIds: [groupId] },
    { type: "ellipse", x: 55, y: 0, width: 65, height: 55, backgroundColor, strokeColor: "#1e1e1e", fillStyle: "solid", groupIds: [groupId] },
    { type: "ellipse", x: 5, y: 25, width: 55, height: 45, backgroundColor, strokeColor: "#1e1e1e", fillStyle: "solid", groupIds: [groupId] },
    { type: "rectangle", x: 5, y: 40, width: 130, height: 30, backgroundColor, strokeColor: "#1e1e1e", fillStyle: "solid", roundness: { type: 3 }, groupIds: [groupId] },
    { type: "text", x: 0, y: H + 6, width: W, text: label, fontSize: 14, textAlign: "center", strokeColor: "#1e1e1e", groupIds: [groupId] },
  ]);
}

// Each entry drives one button in the board's own shape strip (see
// SystemDesignBoard.jsx) — clicking inserts a fresh copy of `build()` onto
// the canvas directly, rather than routing through Excalidraw's built-in
// library sidebar, which mixes in an always-visible (and here always-empty)
// "Personal Library" section and a "Browse libraries" link to an external
// site — both irrelevant clutter for a fixed, curated shape set.
export const SYSTEM_DESIGN_SHAPES = [
  { name: "database", label: "Database", build: () => makeCylinder("database", "Database", "#a5d8ff") },
  { name: "cache", label: "Cache", build: () => makeContainer("cache", "Cache", { backgroundColor: "#ffec99", note: "e.g. Redis" }) },
  { name: "load-balancer", label: "Load Balancer", build: () => makeContainer("load-balancer", "Load Balancer", { type: "diamond", backgroundColor: "#b2f2bb" }) },
  { name: "queue", label: "Queue", build: () => makeQueue("queue", "Message Queue", "#eebefa") },
  { name: "cdn", label: "CDN", build: () => makeCloud("cdn", "CDN", "#99e9f2") },
  { name: "api-service", label: "API Service", build: () => makeContainer("api-service", "API Service", { backgroundColor: "#ffc9c9" }) },
];
