package graph


type Node struct {
	ID            int
	Position      [2]int 
	Type          string 
	IncomingEdges []int  
	OutgoingEdges []int  
	Properties    map[string]interface{}
}


func NewNode(id int, position [2]int, nodeType string) *Node {
	return &Node{
		ID:            id,
		Position:      position,
		Type:          nodeType,
		IncomingEdges: make([]int, 0),
		OutgoingEdges: make([]int, 0),
		Properties:    make(map[string]interface{}),
	}
}


func (n *Node) AddIncomingEdge(edgeID int) {
	
	for _, id := range n.IncomingEdges {
		if id == edgeID {
			return
		}
	}
	
	n.IncomingEdges = append(n.IncomingEdges, edgeID)
}


func (n *Node) AddOutgoingEdge(edgeID int) {
	
	for _, id := range n.OutgoingEdges {
		if id == edgeID {
			return
		}
	}
	
	n.OutgoingEdges = append(n.OutgoingEdges, edgeID)
}


func (n *Node) RemoveIncomingEdge(edgeID int) {
	for i, id := range n.IncomingEdges {
		if id == edgeID {
			n.IncomingEdges = append(n.IncomingEdges[:i], n.IncomingEdges[i+1:]...)
			return
		}
	}
}


func (n *Node) RemoveOutgoingEdge(edgeID int) {
	for i, id := range n.OutgoingEdges {
		if id == edgeID {
			n.OutgoingEdges = append(n.OutgoingEdges[:i], n.OutgoingEdges[i+1:]...)
			return
		}
	}
}


func (n *Node) SetProperty(key string, value interface{}) {
	n.Properties[key] = value
}


func (n *Node) GetProperty(key string) (interface{}, bool) {
	value, exists := n.Properties[key]
	return value, exists
}
