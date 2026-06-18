const express = require('express');
const mongoose = require('mongoose');
const bodyParser = require('body-parser');
const cors = require('cors');

// Express app
const app = express();

// Middleware
app.use(bodyParser.json());
app.use(cors());

// MongoDB connection for MapDB
const MapDBURI = 'mongodb://localhost:27017/MapDB'; // Adjust your connection string
const MapDBConnection = mongoose.createConnection(MapDBURI, {
  useNewUrlParser: true,
  useUnifiedTopology: true,
});
MapDBConnection.once('open', () => {
  console.log('✅ Connected to MapDB');
});

// MongoDB connection for C2DB
const missionDBURI = 'mongodb://localhost:27017/C2DB'; // Adjust your connection string
const missionDBConnection = mongoose.createConnection(missionDBURI, {
  useNewUrlParser: true,
  useUnifiedTopology: true,
});
missionDBConnection.once('open', () => {
  console.log('✅ Connected to C2DB');
});

// MongoDB connection for VehicleDB
const vehicleDBURI = 'mongodb://localhost:27017/VehicleDB'; // Adjust your connection string
const vehicleDBConnection = mongoose.createConnection(vehicleDBURI, {
  useNewUrlParser: true,
  useUnifiedTopology: true,
});
vehicleDBConnection.once('open', () => {
  console.log('✅ Connected to VehicleDB');
});

// Define the Feature schema and model
const featureSchema = new mongoose.Schema({
  type: { type: String, default: 'Feature' },
  properties: {
    feature_type: { type: String, required: true },
    name: { type: String, required: true },
    feature_id: { type: String, required: true, unique: true }
  },
  geometry: {
    type: { type: String, required: true },
    coordinates: { type: [], required: true }
  }
});

// Schema for C2DB
const MissionSchema = new mongoose.Schema({
  mission_id: String,
  behavior: Number,
  objective: {
    arrival_time: {
      earliest: String,
      latest: String,
      target: String,
    },
    geometries: [
      {
        geometry: {
          coordinates: [[Number]],
          geometry_type: String,
        },
        feature_id: { type: String, required: false },
      }
    ],
    maximize_coverage: Boolean,
  },
  transit: {
    desired_vehicle_constraints: {
      max_speed: Number,
    },
  },
  vehicles: [String],
  name: String,
});

// Schema for VehicleDB
const VehicleSchema = new mongoose.Schema({
  agent_id: String,
});

// Create models for each DB
const Mission = missionDBConnection.model('Mission', MissionSchema);
const Vehicle = vehicleDBConnection.model('Vehicle', VehicleSchema);
const Feature = MapDBConnection.model('Feature', featureSchema, 'features');

// ✅ Fetch all collection names from MapDB
app.get('/collections', async (req, res) => {
  try {
    const collections = await MapDBConnection.db.listCollections().toArray();
    const collectionNames = collections.map(col => col.name);
    res.json({ collections: collectionNames });
  } catch (error) {
    console.error("❌ Error fetching collections:", error);
    res.status(500).json({ error: "Internal Server Error" });
  }
});

// ✅ API endpoint to get all Map features from a given collection
app.get('/map-features/:collectionName', async (req, res) => {
  const { collectionName } = req.params;
  if (!collectionName) return res.status(400).json({ error: "Missing collection name" });

  try {
    const collection = MapDBConnection.collection(collectionName);
    const features = await collection.find({}).toArray();
    res.json({ features });
  } catch (error) {
    console.error("❌ Error fetching features:", error);
    res.status(500).json({ error: "Internal Server Error" });
  }
});

// ✅ API endpoint to add or update a feature
app.post('/save-feature', async (req, res) => {
  const { collectionName, feature } = req.body;
  if (!collectionName || !feature) return res.status(400).json({ error: "Missing collection name or feature data" });

  try {
    const collection = MapDBConnection.collection(collectionName);
    await collection.insertOne(feature);
    res.json({ message: "Feature saved successfully" });
  } catch (error) {
    console.error("❌ Error saving feature:", error);
    res.status(500).json({ error: "Internal Server Error" });
  }
});

// ✅ API endpoint to delete a feature by feature_id
app.delete('/delete-feature/:collectionName/:featureId', async (req, res) => {
  const { collectionName, featureId } = req.params;
  if (!collectionName || !featureId) return res.status(400).json({ error: "Missing collection name or feature ID" });

  try {
    const collection = MapDBConnection.collection(collectionName);
    await collection.deleteOne({ feature_id: featureId });
    res.json({ message: "Feature deleted successfully" });
  } catch (error) {
    console.error("❌ Error deleting feature:", error);
    res.status(500).json({ error: "Internal Server Error" });
  }
});

// ✅ Fetch all missions
app.get('/missions', async (req, res) => {
  try {
    const missions = await Mission.find({});
    res.json(missions);
  } catch (error) {
    console.error('❌ Error fetching missions:', error);
    res.status(500).send('Error fetching missions');
  }
});

// ✅ Add or update a mission
app.post('/missions', async (req, res) => {
  try {
    const mission = req.body;
    await Mission.findOneAndUpdate({ mission_id: mission.mission_id }, mission, { upsert: true });
    res.send('Mission saved successfully!');
  } catch (error) {
    console.error('❌ Error saving mission:', error);
    res.status(500).send('Error saving mission');
  }
});

// ✅ Delete a mission
app.delete('/missions/:mission_id', async (req, res) => {
  const { mission_id } = req.params;
  try {
    await Mission.findOneAndDelete({ mission_id });
    res.send('Mission deleted successfully!');
  } catch (error) {
    console.error('❌ Error deleting mission:', error);
    res.status(500).send('Error deleting mission');
  }
});

// ✅ Fetch all vehicles from VehicleDB
app.get('/Vehicles', async (req, res) => {
  try {
    const vehicles = await Vehicle.find({});
    res.json(vehicles);
  } catch (error) {
    console.error('❌ Error fetching vehicles:', error);
    res.status(500).send('Error fetching vehicles');
  }
});

// Start the server
app.listen(5000, () => {
  console.log('🚀 Server running on http://localhost:5000');
});
