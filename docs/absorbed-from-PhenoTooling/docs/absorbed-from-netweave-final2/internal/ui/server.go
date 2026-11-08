package ui

import (
	"encoding/json"
	"fmt"
	"image/png"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"strconv"
	"sync"
	"time"

	"github.com/gorilla/websocket"
	"github.com/netweave/netweave/internal/canvas"
	"github.com/netweave/netweave/internal/graph"
	"github.com/netweave/netweave/internal/ml"
	"github.com/netweave/netweave/internal/render"
	"github.com/netweave/netweave/internal/simulation"
)


type UIServer struct {
	port           int
	staticDir      string
	upgrader       websocket.Upgrader
	clients        map[*websocket.Conn]bool
	broadcast      chan []byte
	mutex          sync.RWMutex

	
	canvasServer   *canvas.Server
	network        *graph.Network
	sim            *simulation.Simulation
	simRunner      *simulation.SimulationRunner
	renderer       *render.Image2Image

	
	isSimulationRunning bool
	simulationSpeed     time.Duration
}


func NewUIServer(port int, staticDir string) *UIServer {
	return &UIServer{
		port:           port,
		staticDir:      staticDir,
		upgrader: websocket.Upgrader{
			ReadBufferSize:  1024,
			WriteBufferSize: 1024,
			CheckOrigin: func(r *http.Request) bool {
				return true 
			},
		},
		clients:            make(map[*websocket.Conn]bool),
		broadcast:          make(chan []byte),
		isSimulationRunning: false,
		simulationSpeed:     100 * time.Millisecond,
	}
}


func (s *UIServer) Start() error {
	
	s.initializeComponents()

	
	fs := http.FileServer(http.Dir(s.staticDir))
	http.Handle("/", fs)

	
	http.HandleFunc("/ws", s.handleWebSocket)

	
	http.HandleFunc("/api/simulation/start", s.handleSimulationStart)
	http.HandleFunc("/api/simulation/stop", s.handleSimulationStop)
	http.HandleFunc("/api/simulation/speed", s.handleSimulationSpeed)
	http.HandleFunc("/api/simulation/stats", s.handleSimulationStats)
	http.HandleFunc("/api/simulation/reset", s.handleSimulationReset)
	http.HandleFunc("/api/simulation/generate", s.handleSimulationGenerate)
	http.HandleFunc("/api/simulation/process-canvas", s.handleProcessCanvas)
	http.HandleFunc("/api/simulation/add-vehicles", s.handleAddVehicles)
	http.HandleFunc("/api/map/render", s.handleMapRender)

	
	go s.handleBroadcasts()

	
	log.Printf("Starting UI server on port %d...\n", s.port)
	return http.ListenAndServe(fmt.Sprintf("0.0.0.0:%d", s.port), nil)
}


func (s *UIServer) initializeComponents() {
	
	canvasWidth, canvasHeight := 800, 600
	s.canvasServer = canvas.NewServer(s.port, s.staticDir, canvasWidth, canvasHeight)

	
	s.renderer = render.NewImage2Image(canvasWidth, canvasHeight)

	
	s.network = graph.NewNetwork()

	
	s.sim = simulation.NewSimulation()
	

	
	s.simRunner = simulation.NewSimulationRunner(s.sim)
}


func (s *UIServer) handleWebSocket(w http.ResponseWriter, r *http.Request) {
	
	conn, err := s.upgrader.Upgrade(w, r, nil)
	if err != nil {
		log.Printf("Error upgrading to WebSocket: %v\n", err)
		return
	}
	defer conn.Close()

	
	s.mutex.Lock()
	s.clients[conn] = true
	s.mutex.Unlock()

	
	s.sendInitialState(conn)

	
	for {
		_, msg, err := conn.ReadMessage()
		if err != nil {
			log.Printf("Error reading message: %v\n", err)
			s.mutex.Lock()
			delete(s.clients, conn)
			s.mutex.Unlock()
			break
		}

		
		s.processMessage(msg)
	}
}


func (s *UIServer) handleBroadcasts() {
	for {
		msg := <-s.broadcast

		s.mutex.RLock()
		for client := range s.clients {
			err := client.WriteMessage(websocket.TextMessage, msg)
			if err != nil {
				log.Printf("Error broadcasting message: %v\n", err)
				client.Close()
				s.mutex.RUnlock()
				s.mutex.Lock()
				delete(s.clients, client)
				s.mutex.Unlock()
				s.mutex.RLock()
			}
		}
		s.mutex.RUnlock()
	}
}


func (s *UIServer) sendInitialState(conn *websocket.Conn) {
	
	simState := map[string]interface{}{
		"type":     "simulation_state",
		"running":  s.isSimulationRunning,
		"speed":    s.simulationSpeed.Milliseconds(),
		"vehicles": len(s.sim.GetVehicles()),
	}

	simStateJSON, err := json.Marshal(simState)
	if err != nil {
		log.Printf("Error encoding simulation state: %v\n", err)
		return
	}

	err = conn.WriteMessage(websocket.TextMessage, simStateJSON)
	if err != nil {
		log.Printf("Error sending simulation state: %v\n", err)
	}

	
	networkState := map[string]interface{}{
		"type":  "network_state",
		"nodes": len(s.network.Nodes),
		"edges": len(s.network.Edges),
	}

	networkStateJSON, err := json.Marshal(networkState)
	if err != nil {
		log.Printf("Error encoding network state: %v\n", err)
		return
	}

	err = conn.WriteMessage(websocket.TextMessage, networkStateJSON)
	if err != nil {
		log.Printf("Error sending network state: %v\n", err)
	}
}


func (s *UIServer) processMessage(msg []byte) {
	
	var baseMsg struct {
		Type string `json:"type"`
	}
	if err := json.Unmarshal(msg, &baseMsg); err != nil {
		log.Printf("Error parsing message: %v\n", err)
		return
	}

	
	switch baseMsg.Type {
	case "simulation_command":
		var cmdMsg struct {
			Type    string `json:"type"`
			Command string `json:"command"`
			Value   string `json:"value,omitempty"`
		}
		if err := json.Unmarshal(msg, &cmdMsg); err != nil {
			log.Printf("Error parsing command message: %v\n", err)
			return
		}

		s.handleSimulationCommand(cmdMsg.Command, cmdMsg.Value)

	default:
		log.Printf("Unknown message type: %s\n", baseMsg.Type)
	}
}


func (s *UIServer) handleSimulationCommand(command, value string) {
	switch command {
	case "start":
		s.startSimulation()

	case "stop":
		s.stopSimulation()

	case "speed":
		if speed, err := strconv.Atoi(value); err == nil {
			s.setSimulationSpeed(time.Duration(speed) * time.Millisecond)
		}

	case "reset":
		s.resetSimulation()

	case "generate":
		s.generateRandomNetwork()

	case "add_vehicles":
		if count, err := strconv.Atoi(value); err == nil {
			s.addRandomVehicles(count)
		}

	default:
		log.Printf("Unknown simulation command: %s\n", command)
	}
}


func (s *UIServer) handleSimulationStart(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	s.startSimulation()

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]string{
		"status": "success",
	})
}


func (s *UIServer) handleSimulationStop(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	s.stopSimulation()

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]string{
		"status": "success",
	})
}


func (s *UIServer) handleSimulationSpeed(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	speedStr := r.FormValue("speed")
	speed, err := strconv.Atoi(speedStr)
	if err != nil {
		http.Error(w, "Invalid speed value", http.StatusBadRequest)
		return
	}

	s.setSimulationSpeed(time.Duration(speed) * time.Millisecond)

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]string{
		"status": "success",
		"speed":  speedStr,
	})
}


func (s *UIServer) handleSimulationStats(w http.ResponseWriter, r *http.Request) {
	avgSpeed, vehicleCount, congestionLevel := s.sim.GetStatistics()

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"status":          "success",
		"average_speed":   avgSpeed,
		"vehicle_count":   vehicleCount,
		"congestion_level": congestionLevel,
	})
}


func (s *UIServer) handleSimulationReset(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	s.resetSimulation()

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]string{
		"status": "success",
	})
}


func (s *UIServer) handleSimulationGenerate(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	s.generateRandomNetwork()

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"status": "success",
		"nodes":  len(s.network.Nodes),
		"edges":  len(s.network.Edges),
	})
}


func (s *UIServer) handleProcessCanvas(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	
	canvasPath := r.FormValue("canvas_path")
	if canvasPath == "" {
		http.Error(w, "Canvas path is required", http.StatusBadRequest)
		return
	}

	
	err := s.processCanvasToNetwork(canvasPath)
	if err != nil {
		http.Error(w, fmt.Sprintf("Error processing canvas: %v", err), http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"status": "success",
		"nodes":  len(s.network.Nodes),
		"edges":  len(s.network.Edges),
	})
}


func (s *UIServer) handleAddVehicles(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	countStr := r.FormValue("count")
	count, err := strconv.Atoi(countStr)
	if err != nil {
		http.Error(w, "Invalid count value", http.StatusBadRequest)
		return
	}

	s.addRandomVehicles(count)

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]string{
		"status": "success",
		"count":  countStr,
	})
}


func (s *UIServer) handleMapRender(w http.ResponseWriter, r *http.Request) {
	
	if s.network != nil {
		s.renderer.RenderMap(s.network)
		vehicles := s.sim.GetVehicles()
		if vehicles != nil {
			s.renderer.UpdateTraffic(s.network, vehicles)
		}
	}
	img := s.renderer.GetImage()

	w.Header().Set("Content-Type", "image/png")
	err := png.Encode(w, img)
	if err != nil {
		http.Error(w, "Failed to encode image", http.StatusInternalServerError)
		return
	}
}


func (s *UIServer) startSimulation() {
	s.mutex.Lock()
	defer s.mutex.Unlock()

	if s.isSimulationRunning {
		return
	}

	s.simRunner.Start(s.simulationSpeed)
	s.isSimulationRunning = true

	
	s.broadcastSimulationState()
}


func (s *UIServer) stopSimulation() {
	s.mutex.Lock()
	defer s.mutex.Unlock()

	if !s.isSimulationRunning {
		return
	}

	s.simRunner.Stop()
	s.isSimulationRunning = false

	
	s.broadcastSimulationState()
}


func (s *UIServer) setSimulationSpeed(speed time.Duration) {
	s.mutex.Lock()
	defer s.mutex.Unlock()

	s.simulationSpeed = speed

	if s.isSimulationRunning {
		s.simRunner.SetStepInterval(speed)
	}

	
	s.broadcastSimulationState()
}


func (s *UIServer) resetSimulation() {
	s.mutex.Lock()
	defer s.mutex.Unlock()

	
	if s.isSimulationRunning {
		s.simRunner.Stop()
		s.isSimulationRunning = false
	}

	
	s.sim = simulation.NewSimulation()
	
	if s.network != nil {
		s.sim.LoadNetwork(s.network)
	}
	s.simRunner = simulation.NewSimulationRunner(s.sim)

	
	s.broadcastSimulationState()
}


func (s *UIServer) generateRandomNetwork() {
	s.mutex.Lock()
	defer s.mutex.Unlock()

	
	if s.isSimulationRunning {
		s.simRunner.Stop()
		s.isSimulationRunning = false
	}

	
	generator := simulation.NewRandomNetworkGenerator(800, 600)

	
	s.network = generator.GenerateNetwork()

	
	s.sim = simulation.NewSimulation()
	
	if s.network != nil {
		s.sim.LoadNetwork(s.network)
	}
	s.simRunner = simulation.NewSimulationRunner(s.sim)

	
	s.renderer.RenderMap(s.network)

	
	s.broadcastNetworkState()
	s.broadcastSimulationState()
}


func (s *UIServer) processCanvasToNetwork(canvasPath string) error {
	s.mutex.Lock()
	defer s.mutex.Unlock()

	
	if s.isSimulationRunning {
		s.simRunner.Stop()
		s.isSimulationRunning = false
	}

	
	file, err := os.Open(filepath.Join(s.staticDir, canvasPath))
	if err != nil {
		return fmt.Errorf("failed to open canvas image: %v", err)
	}
	defer file.Close()

	
	img, err := png.Decode(file)
	if err != nil {
		return fmt.Errorf("failed to decode canvas image: %v", err)
	}

	
	s.network = ml.ProcessImageToNetwork(img)

	
	s.sim = simulation.NewSimulation()
	
	if s.network != nil {
		s.sim.LoadNetwork(s.network)
	}
	s.simRunner = simulation.NewSimulationRunner(s.sim)

	
	s.renderer.RenderMap(s.network)

	
	s.broadcastNetworkState()
	s.broadcastSimulationState()

	return nil
}


func (s *UIServer) addRandomVehicles(count int) {
	s.mutex.Lock()
	defer s.mutex.Unlock()

	s.simRunner.AddRandomVehicles(count)

	
	s.broadcastSimulationState()
}


func (s *UIServer) broadcastSimulationState() {
	simState := map[string]interface{}{
		"type":     "simulation_state",
		"running":  s.isSimulationRunning,
		"speed":    s.simulationSpeed.Milliseconds(),
		"vehicles": len(s.sim.GetVehicles()),
	}

	simStateJSON, err := json.Marshal(simState)
	if err != nil {
		log.Printf("Error encoding simulation state: %v\n", err)
		return
	}

	s.broadcast <- simStateJSON
}


func (s *UIServer) broadcastNetworkState() {
	networkState := map[string]interface{}{
		"type":  "network_state",
		"nodes": len(s.network.Nodes),
		"edges": len(s.network.Edges),
	}

	networkStateJSON, err := json.Marshal(networkState)
	if err != nil {
		log.Printf("Error encoding network state: %v\n", err)
		return
	}

	s.broadcast <- networkStateJSON
}
