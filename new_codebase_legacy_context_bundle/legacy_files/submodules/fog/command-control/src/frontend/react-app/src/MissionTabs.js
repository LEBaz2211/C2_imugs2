import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Tabs, Tab, Button, Box } from '@mui/material';
import { v4 as uuidv4 } from 'uuid';

// Function to create a default mission config
const defaultMissionConfig = (missionNumber) => ({
  name: `Mission_${missionNumber}`, // Auto-generate the mission name
  mission_id: uuidv4(), // Generate a unique mission ID
  behavior: 0,
  objective: {
    arrival_time: {
      earliest: '2021-11-22T11:02:54Z',
      latest: '2023-11-22T11:02:54Z',
      target: '2023-11-22T11:02:54Z',
    },
    geometries: [
      {
        feature_id: 'b3b6ead4-14d6-4777-baa1-52bae998744c', // Example feature ID
      },
      {
        geometry: {
          coordinates: [
            [25.861999592381864, 59.4391728521982],
            [25.86392125671736, 59.44157945093596],
            [25.856700125217003, 59.441533688416854],
          ],
          geometry_type: 'MultiPoint',
        },
      },
    ].filter((g) => g.geometry || g.feature_id), // Remove empty geometries
  },
  transit: {
    desired_vehicle_constraints: {
      max_speed: 3,
    },
  },
  vehicles: [
    '4dd12623-3fb6-4ae4-91c2-1f4b10d2327d',
    '2b4a887b-95af-451d-bd85-e0dcacb72524',
    'f9992bb3-9871-451f-90a0-9207eb9fe6c5',
  ],
});


function MissionTabs() {
  const [missions, setMissions] = useState([]); // Holds the list of existing missions from the backend
  const [newMissions, setNewMissions] = useState([]); // Holds mission IDs of newly created missions
  const [selectedTab, setSelectedTab] = useState(0); // Tracks which tab is selected
  const [currentMission, setCurrentMission] = useState(null); // Holds the currently active mission for editing
  const [missionJsonInput, setMissionJsonInput] = useState(''); // Tracks JSON input for the mission being edited

  useEffect(() => {
    fetchMissions(); // Fetch the missions on component mount
  }, []);

  // Fetch missions from the backend
  const fetchMissions = async () => {
    try {
      const response = await axios.get('http://localhost:5000/missions');
      setMissions(response.data); // Set the missions to state
      if (response.data.length > 0) {
        // Set the first mission as the default selected tab
        setCurrentMission(response.data[0]);
        setMissionJsonInput(JSON.stringify(response.data[0], null, 2));
      }
    } catch (error) {
      console.error('Error fetching missions', error);
    }
  };

  // Handle tab change
  const handleTabChange = (event, newValue) => {
    setSelectedTab(newValue);
    if (newValue < missions.length) {
      const selectedMission = missions[newValue];
      setCurrentMission(selectedMission);
      setMissionJsonInput(JSON.stringify(selectedMission, null, 2));
    }
  };

  // Handle JSON input change for mission config
  const handleJsonInputChange = (event) => {
    setMissionJsonInput(event.target.value); // Update the JSON input box value
    try {
      const parsedJson = JSON.parse(event.target.value); // Attempt to parse the input
      setCurrentMission(parsedJson); // If valid, update the currentMission
    } catch (error) {
      console.error('Invalid JSON format');
    }
  };


  const handleSaveMission = async () => {
    try {
      const missionToSave = { ...currentMission, mission_id: currentMission.mission_id || uuidv4() }; // Ensure mission_id is present
      await axios.post('http://localhost:5000/missions', missionToSave);
      
      alert('Mission saved successfully!');
  
      // Save the selected mission index before fetching the missions again
      const savedMissionId = missionToSave.mission_id;
  
      await fetchMissions(); // Refresh missions after save
  
      // Find the index of the newly saved mission in the refreshed list
      const newIndex = missions.findIndex(m => m.mission_id === savedMissionId);
  
      // Ensure the tab stays on the saved mission
      if (newIndex !== -1) {
        setSelectedTab(newIndex);
      } else {
        setSelectedTab(missions.length - 1); // Fallback to the last mission if not found
      }
  
      // Update currentMission with the recently saved mission
      setCurrentMission(missionToSave);
      
      // Update the JSON input with the latest saved mission config
      setMissionJsonInput(JSON.stringify(missionToSave, null, 2)); // Keep the JSON input up to date
  
    } catch (error) {
      console.error('Error saving mission', error);
    }
  };
  
  

  // Add a new mission tab
  const handleAddMission = () => {
    const newMission = defaultMissionConfig(missions.length + 1);
    setMissions([...missions, newMission]);
    setSelectedTab(missions.length); // Switch to the new tab
    setCurrentMission(newMission); // Set new mission as the current mission
    setMissionJsonInput(JSON.stringify(newMission, null, 2)); // Update JSON input with new mission config
    setNewMissions([...newMissions, newMission.mission_id]); // Add the new mission ID to the list of new missions
  };

  // Delete the current mission with confirmation
  const handleDeleteMission = async () => {
    if (!currentMission || !currentMission.mission_id) return;

    if (window.confirm('Are you sure you want to delete this mission?')) {
      try {
        const missionId = currentMission.mission_id;
        await axios.delete(`http://localhost:5000/missions/${missionId}`);
        alert('Mission deleted successfully!');
        setMissions(missions.filter((mission, index) => index !== selectedTab)); // Remove the deleted mission
        setSelectedTab(0); // Reset to first tab after deletion
        if (missions.length > 1) {
          setCurrentMission(missions[0]);
          setMissionJsonInput(JSON.stringify(missions[0], null, 2));
        }
        setNewMissions(newMissions.filter(id => id !== missionId)); // Remove from new missions if deleted
      } catch (error) {
        console.error('Error deleting mission', error);
      }
    }
  };

  // Function to initialize the mission by sending a request to the C++ backend
  const handleInitializeMission = async () => {
    // Ensure there is a mission ID, and if not, send an empty object
    const payload = {
      action: "initialize",
      mission_id: currentMission && currentMission.mission_id ? currentMission.mission_id : null,
      mission_config: currentMission && missionJsonInput ? missionJsonInput : {}
    };
    console.info('payload:', payload);

    try {
      // Send request to the C++ backend to initialize the mission
      await axios.post('http://localhost:5001/mission_control', payload, {
        headers: {
          'Content-Type': 'application/json', // Set the correct Content-Type header
        },
      });

      alert('Mission initialized successfully!');
    } catch (error) {
      console.error('Error initializing mission:', error);
      // alert('Failed to initialize the mission.');
    }
  };

  // Function to handle mission status changes (start, pause, stop)
  const handleChangeMissionStatus = async (status) => {
    if (!currentMission || !currentMission.mission_id) {
      alert('No mission selected for status change.');
      return;
    }

    const payload = {
      action: "change_status",
      mission_id: currentMission.mission_id,
      requested_state: status,  // This could be an enum or integer representing the status (e.g., 0 = Start, 1 = Pause, 2 = Stop)
    };

    try {
      // Send request to change the mission status
      await axios.post('http://localhost:5001/mission_control', payload, {
        headers: {
          'Content-Type': 'application/json',
        },
      });

      alert(`Mission status changed to ${status === 1 ? 'Approve' : status === 2 ? 'Start' : 'Pause'} successfully!`);
    } catch (error) {
      console.error('Error changing mission status:', error);
      // alert('Failed to change the mission status.');
    }
  };



  return (
    <Box>
      <Tabs value={selectedTab} onChange={handleTabChange}>
        {missions.map((mission, index) => (
          <Tab key={mission.mission_id} label={mission.name || `Mission ${index + 1}`} />
        ))}
        <Tab label="+" onClick={handleAddMission} />
      </Tabs>

      {currentMission && (
        <Box p={3}>
          <h3>Mission ID: {currentMission.mission_id}</h3>

          {/* Textarea for mission JSON input */}
          <textarea
            value={missionJsonInput}
            onChange={handleJsonInputChange}
            rows={15}
            style={{
              width: '100%',
              backgroundColor: 'black',
              color: 'white',
              fontFamily: 'monospace',
              fontSize: '14px',
              padding: '10px',
              borderRadius: '5px',
              border: '1px solid #ccc',
            }}
          />

          {/* Buttons for saving and deleting */}
          <Box mt={2}>
            <Button
              variant="contained"
              color="primary"
              onClick={handleSaveMission}
              style={{ marginRight: '10px' }}
            >
              {newMissions.includes(currentMission.mission_id) ? 'Create Mission' : 'Save Mission'}
            </Button>
            <Button
              variant="contained"
              color="error"
              onClick={handleDeleteMission}
              disabled={newMissions.includes(currentMission.mission_id)} // Disable delete button for new missions
            >
              Delete Mission
            </Button>
          </Box>

          {/* Mission controls */}
          <Box mt={3}>
          <Button
              variant="contained"
              color="primary"
              onClick={handleInitializeMission}
              style={{ marginRight: '10px' }}
            >
              Submit Mission
            </Button>
            <Button 
              variant="contained" 
              // color="success" 
              onClick={() => handleChangeMissionStatus(1)} // Approve Mission
              style={{ marginRight: '10px' }}
            >
              Approve Mission
            </Button>
            <Button 
              variant="contained" 
              color="success" 
              onClick={() => handleChangeMissionStatus(2)} // Start Mission
              style={{ marginRight: '10px' }}
            >
              Start Mission
            </Button>
            <Button 
              variant="contained" 
              color="warning"
              onClick={() => handleChangeMissionStatus(3)} // Pause Mission
              style={{ marginRight: '10px' }}
            >
              Pause Mission
            </Button>
            <Button 
              variant="contained" 
              color="error"
              onClick={() => handleChangeMissionStatus(5)} // Delete Mission from active missions
              style={{ marginRight: '10px' }}
            >
              Stop Mission
            </Button>
            <Button 
              variant="contained" 
              // color="success" 
              onClick={() => handleChangeMissionStatus(0)} // Approve Mission
              style={{ marginRight: '10px' }}
            >
              Reinitialize Mission
            </Button>

          </Box>
        </Box>
      )}
    </Box>
  );
}

export default MissionTabs;
