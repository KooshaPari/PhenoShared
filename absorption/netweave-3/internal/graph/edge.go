package graph


type Edge struct {
	ID         int
	FromNodeID int
	ToNodeID   int
	Type       string 
	Length     int    
	Lanes      int    
	SpeedLimit int    
	Properties map[string]interface{}
}


func NewEdge(id, fromNodeID, toNodeID int, edgeType string, length, lanes, speedLimit int) *Edge {
	return &Edge{
		ID:         id,
		FromNodeID: fromNodeID,
		ToNodeID:   toNodeID,
		Type:       edgeType,
		Length:     length,
		Lanes:      lanes,
		SpeedLimit: speedLimit,
		Properties: make(map[string]interface{}),
	}
}


func (e *Edge) SetProperty(key string, value interface{}) {
	e.Properties[key] = value
}


func (e *Edge) GetProperty(key string) (interface{}, bool) {
	value, exists := e.Properties[key]
	return value, exists
}



func (e *Edge) GetWeight() float64 {
	if e.SpeedLimit <= 0 {
		return float64(e.Length)
	}
	return float64(e.Length) / float64(e.SpeedLimit)
}


func (e *Edge) IsConnectedTo(nodeID int) bool {
	return e.FromNodeID == nodeID || e.ToNodeID == nodeID
}


func (e *Edge) GetOtherNode(nodeID int) int {
	if e.FromNodeID == nodeID {
		return e.ToNodeID
	}
	if e.ToNodeID == nodeID {
		return e.FromNodeID
	}
	return -1 
}
