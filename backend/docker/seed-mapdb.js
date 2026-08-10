/* global db, print */

// Seed one MongoDB document per valid GeoJSON Feature. This runs in mongosh
// before the legacy planner starts; it intentionally preserves unrelated rows.
const fs = require("fs");
const path = require("path");

const sourceRoot = process.env.MAP_SEED_ROOT || "/seed/rma";
const databaseName = process.env.MAP_DATABASE || "MapDB";
const collectionName = process.env.MAP_COLLECTION || "rma";
const requiredFeatureIds = (process.env.MAP_REQUIRED_FEATURE_IDS || "")
  .split(",")
  .map((value) => value.trim())
  .filter(Boolean);

const supportedGeometry = {
  objective: new Set(["Point"]),
  road: new Set(["LineString"]),
  geofence: new Set(["Polygon"]),
  workspace: new Set(["Polygon"]),
  risk: new Set(["Polygon"]),
};

function geojsonFiles(root) {
  const result = [];
  for (const entry of fs.readdirSync(root, { withFileTypes: true })) {
    const entryPath = path.join(root, entry.name);
    if (entry.isDirectory()) {
      result.push(...geojsonFiles(entryPath));
    } else if (entry.isFile() && entry.name.endsWith(".geojson")) {
      result.push(entryPath);
    }
  }
  return result.sort();
}

function unpackFeatures(document, filename) {
  if (document && document.type === "Feature") {
    return [document];
  }
  if (document && document.type === "FeatureCollection" && Array.isArray(document.features)) {
    return document.features;
  }
  throw new Error(`${filename}: expected a GeoJSON Feature or FeatureCollection`);
}

function validationError(feature) {
  if (!feature || feature.type !== "Feature") {
    return "record is not a GeoJSON Feature";
  }
  const properties = feature.properties;
  const geometry = feature.geometry;
  if (!properties || typeof properties !== "object") {
    return "properties is missing";
  }
  for (const field of ["feature_id", "feature_type", "name"]) {
    if (typeof properties[field] !== "string" || properties[field].trim() === "") {
      return `properties.${field} is missing`;
    }
  }
  if (!geometry || typeof geometry !== "object" || !Array.isArray(geometry.coordinates)) {
    return "geometry or geometry.coordinates is missing";
  }
  const allowed = supportedGeometry[properties.feature_type];
  if (!allowed || !allowed.has(geometry.type)) {
    return `unsupported ${properties.feature_type}/${geometry.type}`;
  }
  return null;
}

function loadFeatures(root) {
  if (!fs.existsSync(root) || !fs.statSync(root).isDirectory()) {
    throw new Error(`Map seed directory does not exist: ${root}`);
  }

  const featuresById = new Map();
  let skipped = 0;
  for (const filename of geojsonFiles(root)) {
    const document = JSON.parse(fs.readFileSync(filename, "utf8"));
    const features = unpackFeatures(document, filename);
    features.forEach((feature, index) => {
      const error = validationError(feature);
      const source = `${path.relative(root, filename)}#${index}`;
      if (error) {
        print(`[mapdb-seed] skipping ${source}: ${error}`);
        skipped += 1;
        return;
      }
      const featureId = feature.properties.feature_id;
      if (featuresById.has(featureId)) {
        throw new Error(`Duplicate source feature_id ${featureId}: ${featuresById.get(featureId).source} and ${source}`);
      }
      featuresById.set(featureId, { source, feature });
    });
  }

  if (featuresById.size === 0) {
    throw new Error(`No valid map features found below ${root}`);
  }
  return { featuresById, skipped };
}

const { featuresById, skipped } = loadFeatures(sourceRoot);
const mapDatabase = db.getSiblingDB(databaseName);
const collection = mapDatabase.getCollection(collectionName);

for (const featureId of featuresById.keys()) {
  const existing = collection.countDocuments({ "properties.feature_id": featureId });
  if (existing > 1) {
    throw new Error(`MapDB contains ${existing} documents for feature_id ${featureId}`);
  }
}

let matched = 0;
let modified = 0;
let upserted = 0;
for (const [featureId, item] of featuresById.entries()) {
  const result = collection.replaceOne(
    { "properties.feature_id": featureId },
    item.feature,
    { upsert: true },
  );
  matched += result.matchedCount;
  modified += result.modifiedCount;
  upserted += result.upsertedCount;
}

for (const featureId of requiredFeatureIds) {
  const count = collection.countDocuments({ "properties.feature_id": featureId });
  if (count !== 1) {
    throw new Error(`Required feature_id ${featureId} has ${count} MapDB documents after seeding`);
  }
}

print(JSON.stringify({
  database: databaseName,
  collection: collectionName,
  valid_source_features: featuresById.size,
  skipped_source_features: skipped,
  matched,
  modified,
  upserted,
  collection_documents: collection.countDocuments({}),
}));
