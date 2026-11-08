package canvas

import (
	"encoding/json"
	"fmt"
	"image"
	"image/png"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"sync"

	"github.com/gorilla/websocket"
)


type Server struct {
	port           int
	staticDir      string
	upgrader       websocket.Upgrader
	clients        map[*websocket.Conn]bool
	broadcast      chan []byte
	mutex          sync.RWMutex
	canvasInstance *Interface
}


func NewServer(port int, staticDir string, canvasWidth, canvasHeight int) *Server {
	return &Server{
		port:      port,
		staticDir: staticDir,
		upgrader: websocket.Upgrader{
			ReadBufferSize:  1024,
			WriteBufferSize: 1024,
			CheckOrigin: func(r *http.Request) bool {
				return true 
			},
		},
		clients:        make(map[*websocket.Conn]bool),
		broadcast:      make(chan []byte),
		canvasInstance: NewInterface(canvasWidth, canvasHeight),
	}
}


func (s *Server) Start() error {
	
	fs := http.FileServer(http.Dir(s.staticDir))
	http.Handle("/", fs)

	
	http.HandleFunc("/ws", s.handleWebSocket)

	
	http.HandleFunc("/api/canvas/image", s.handleCanvasImage)
	http.HandleFunc("/api/canvas/save", s.handleCanvasSave)
	http.HandleFunc("/api/canvas/load", s.handleCanvasLoad)
	http.HandleFunc("/api/canvas/clear", s.handleCanvasClear)

	
	go s.handleBroadcasts()

	
	log.Printf("Starting canvas server on port %d...\n", s.port)
	return http.ListenAndServe(fmt.Sprintf("0.0.0.0:%d", s.port), nil)
}


func (s *Server) handleWebSocket(w http.ResponseWriter, r *http.Request) {
	
	conn, err := s.upgrader.Upgrade(w, r, nil)
	if err != nil {
		log.Printf("Error upgrading to WebSocket: %v\n", err)
		return
	}
	defer conn.Close()

	
	s.mutex.Lock()
	s.clients[conn] = true
	s.mutex.Unlock()

	
	s.sendCanvasState(conn)

	
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

		
		s.broadcast <- msg
	}
}


func (s *Server) handleBroadcasts() {
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


func (s *Server) handleCanvasImage(w http.ResponseWriter, r *http.Request) {
	img := s.canvasInstance.GetImage()

	w.Header().Set("Content-Type", "image/png")
	err := png.Encode(w, img)
	if err != nil {
		http.Error(w, "Failed to encode image", http.StatusInternalServerError)
		return
	}
}


func (s *Server) handleCanvasSave(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	filename := r.FormValue("filename")
	if filename == "" {
		filename = "canvas.png"
	}

	
	if filepath.Ext(filename) != ".png" {
		filename += ".png"
	}

	
	outputDir := filepath.Join(s.staticDir, "saved")
	err := os.MkdirAll(outputDir, 0755)
	if err != nil {
		http.Error(w, "Failed to create output directory", http.StatusInternalServerError)
		return
	}

	
	outputPath := filepath.Join(outputDir, filename)
	file, err := os.Create(outputPath)
	if err != nil {
		http.Error(w, "Failed to create file", http.StatusInternalServerError)
		return
	}
	defer file.Close()

	img := s.canvasInstance.GetImage()
	err = png.Encode(file, img)
	if err != nil {
		http.Error(w, "Failed to encode image", http.StatusInternalServerError)
		return
	}

	
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]string{
		"status":   "success",
		"filename": filename,
		"path":     "/saved/" + filename,
	})
}


func (s *Server) handleCanvasLoad(w http.ResponseWriter, r *http.Request) {
	filename := r.FormValue("filename")
	if filename == "" {
		http.Error(w, "Filename is required", http.StatusBadRequest)
		return
	}

	
	if filepath.Ext(filename) != ".png" {
		filename += ".png"
	}

	
	inputPath := filepath.Join(s.staticDir, "saved", filename)
	file, err := os.Open(inputPath)
	if err != nil {
		http.Error(w, "Failed to open file", http.StatusNotFound)
		return
	}
	defer file.Close()

	img, err := png.Decode(file)
	if err != nil {
		http.Error(w, "Failed to decode image", http.StatusInternalServerError)
		return
	}

	
	rgba, ok := img.(*image.RGBA)
	if !ok {
		
		bounds := img.Bounds()
		rgba = image.NewRGBA(bounds)
		for y := bounds.Min.Y; y < bounds.Max.Y; y++ {
			for x := bounds.Min.X; x < bounds.Max.X; x++ {
				rgba.Set(x, y, img.At(x, y))
			}
		}
	}

	
	s.canvasInstance.mutex.Lock()
	s.canvasInstance.colorMap = rgba
	s.canvasInstance.mutex.Unlock()

	
	s.broadcastCanvasState()

	
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]string{
		"status":   "success",
		"filename": filename,
	})
}


func (s *Server) handleCanvasClear(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	s.canvasInstance.Clear()
	s.broadcastCanvasState()

	
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]string{
		"status": "success",
	})
}


const (
	MsgTypeDraw        = "draw"
	MsgTypeSetTool     = "set_tool"
	MsgTypeSetColor    = "set_color"
	MsgTypeCanvasState = "canvas_state"
)


type DrawMessage struct {
	Type   string `json:"type"`
	Action string `json:"action"` 
	X1     int    `json:"x1"`
	Y1     int    `json:"y1"`
	X2     int    `json:"x2,omitempty"`
	Y2     int    `json:"y2,omitempty"`
}


type ToolMessage struct {
	Type     string `json:"type"`
	Tool     string `json:"tool"`
	Size     int    `json:"size,omitempty"`
	ColorR   uint8  `json:"colorR,omitempty"`
	ColorG   uint8  `json:"colorG,omitempty"`
	ColorB   uint8  `json:"colorB,omitempty"`
	Property string `json:"property,omitempty"` 
	Value    string `json:"value,omitempty"`    
}


func (s *Server) processMessage(msg []byte) {
	
	var baseMsg struct {
		Type string `json:"type"`
	}
	if err := json.Unmarshal(msg, &baseMsg); err != nil {
		log.Printf("Error parsing message: %v\n", err)
		return
	}

	switch baseMsg.Type {
	case MsgTypeDraw:
		var drawMsg DrawMessage
		if err := json.Unmarshal(msg, &drawMsg); err != nil {
			log.Printf("Error parsing draw message: %v\n", err)
			return
		}
		s.handleDrawMessage(drawMsg)

	case MsgTypeSetTool:
		var toolMsg ToolMessage
		if err := json.Unmarshal(msg, &toolMsg); err != nil {
			log.Printf("Error parsing tool message: %v\n", err)
			return
		}
		s.handleToolMessage(toolMsg)

	default:
		log.Printf("Unknown message type: %s\n", baseMsg.Type)
	}
}


func (s *Server) handleDrawMessage(msg DrawMessage) {
	switch msg.Action {
	case "point":
		s.canvasInstance.DrawPoint(msg.X1, msg.Y1)
	case "line":
		s.canvasInstance.DrawLine(msg.X1, msg.Y1, msg.X2, msg.Y2)
	case "rect":
		s.canvasInstance.FillRect(msg.X1, msg.Y1, msg.X2, msg.Y2)
	default:
		log.Printf("Unknown draw action: %s\n", msg.Action)
	}
}


func (s *Server) handleToolMessage(msg ToolMessage) {
	
	var toolType ToolType
	switch msg.Tool {
	case "road":
		toolType = RoadTool
	case "intersection":
		toolType = IntersectionTool
	case "zone":
		toolType = ZoneTool
	case "eraser":
		toolType = EraserTool
	default:
		log.Printf("Unknown tool type: %s\n", msg.Tool)
		return
	}

	
	s.canvasInstance.SetTool(toolType)

	
	if msg.ColorR > 0 || msg.ColorG > 0 || msg.ColorB > 0 {
		s.canvasInstance.SetColor(msg.ColorR, msg.ColorG, msg.ColorB)
	}

	
	if msg.Property != "" && msg.Value != "" {
		
	}
}


func (s *Server) sendCanvasState(conn *websocket.Conn) {
	
	
	
	
	
	_ = s.canvasInstance.GetImage()

	
	stateMsg := map[string]string{
		"type":    MsgTypeCanvasState,
		"message": "Canvas state updated",
	}

	jsonMsg, err := json.Marshal(stateMsg)
	if err != nil {
		log.Printf("Error encoding canvas state: %v\n", err)
		return
	}

	err = conn.WriteMessage(websocket.TextMessage, jsonMsg)
	if err != nil {
		log.Printf("Error sending canvas state: %v\n", err)
	}
}


func (s *Server) broadcastCanvasState() {
	stateMsg := map[string]string{
		"type":    MsgTypeCanvasState,
		"message": "Canvas state updated",
	}

	jsonMsg, err := json.Marshal(stateMsg)
	if err != nil {
		log.Printf("Error encoding canvas state: %v\n", err)
		return
	}

	s.broadcast <- jsonMsg
}
