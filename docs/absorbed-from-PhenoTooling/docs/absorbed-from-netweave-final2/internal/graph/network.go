package graph

import (
	"sync"
)


type Network struct {
	Nodes map[int]*Node
	Edges map[int]*Edge
	POIs  map[int]*POI
	mutex sync.RWMutex
}


func NewNetwork() *Network {
	return &Network{
		Nodes: make(map[int]*Node),
		Edges: make(map[int]*Edge),
		POIs:  make(map[int]*POI),
	}
}


func (n *Network) AddNode(node *Node) {
	n.mutex.Lock()
	defer n.mutex.Unlock()

	n.Nodes[node.ID] = node
}


func (n *Network) AddEdge(edge *Edge) {
	n.mutex.Lock()
	defer n.mutex.Unlock()

	n.Edges[edge.ID] = edge


	if fromNode, exists := n.Nodes[edge.FromNodeID]; exists {
		fromNode.OutgoingEdges = append(fromNode.OutgoingEdges, edge.ID)
	}

	if toNode, exists := n.Nodes[edge.ToNodeID]; exists {
		toNode.IncomingEdges = append(toNode.IncomingEdges, edge.ID)
	}
}


func (n *Network) GetNode(id int) (*Node, bool) {
	n.mutex.RLock()
	defer n.mutex.RUnlock()

	node, exists := n.Nodes[id]
	return node, exists
}


func (n *Network) GetEdge(id int) (*Edge, bool) {
	n.mutex.RLock()
	defer n.mutex.RUnlock()

	edge, exists := n.Edges[id]
	return edge, exists
}


func (n *Network) GetOutgoingEdges(nodeID int) []*Edge {
	n.mutex.RLock()
	defer n.mutex.RUnlock()

	node, exists := n.Nodes[nodeID]
	if !exists {
		return []*Edge{}
	}

	edges := make([]*Edge, 0, len(node.OutgoingEdges))
	for _, edgeID := range node.OutgoingEdges {
		if edge, exists := n.Edges[edgeID]; exists {
			edges = append(edges, edge)
		}
	}

	return edges
}


func (n *Network) GetIncomingEdges(nodeID int) []*Edge {
	n.mutex.RLock()
	defer n.mutex.RUnlock()

	node, exists := n.Nodes[nodeID]
	if !exists {
		return []*Edge{}
	}

	edges := make([]*Edge, 0, len(node.IncomingEdges))
	for _, edgeID := range node.IncomingEdges {
		if edge, exists := n.Edges[edgeID]; exists {
			edges = append(edges, edge)
		}
	}

	return edges
}


func (n *Network) FindPath(startNodeID, endNodeID int) []int {
	n.mutex.RLock()
	defer n.mutex.RUnlock()


	if _, exists := n.Nodes[startNodeID]; !exists {
		return []int{}
	}
	if _, exists := n.Nodes[endNodeID]; !exists {
		return []int{}
	}


	if startNodeID == endNodeID {
		return []int{}
	}


	dist := make(map[int]int)
	prev := make(map[int]int)
	visited := make(map[int]bool)


	for nodeID := range n.Nodes {
		dist[nodeID] = int(^uint(0) >> 1)
		prev[nodeID] = -1
	}


	dist[startNodeID] = 0


	for len(visited) < len(n.Nodes) {

		minDist := int(^uint(0) >> 1)
		var current int
		for nodeID, d := range dist {
			if !visited[nodeID] && d < minDist {
				minDist = d
				current = nodeID
			}
		}


		if minDist == int(^uint(0) >> 1) {
			break
		}


		visited[current] = true


		if current == endNodeID {
			break
		}


		for _, edgeID := range n.Nodes[current].OutgoingEdges {
			edge, exists := n.Edges[edgeID]
			if !exists {
				continue
			}

			neighbor := edge.ToNodeID

			
			
			speedLimit := edge.SpeedLimit
			if speedLimit <= 0 {
				speedLimit = 1
			}

			
			travelTime := float64(edge.Length) / float64(speedLimit)

			
			
			roadFactor := 1.0
			switch edge.Type {
			case "highway":
				roadFactor = 0.7  
			case "major":
				roadFactor = 0.8  
			case "minor":
				roadFactor = 1.2  
			case "local":
				roadFactor = 1.5  
			}

			
			newDist := dist[current] + int(travelTime * roadFactor)

			if newDist < dist[neighbor] {
				dist[neighbor] = newDist
				prev[neighbor] = current
			}
		}
	}


	if prev[endNodeID] == -1 {
		return []int{}
	}


	path := make([]int, 0)
	for at := endNodeID; at != startNodeID; at = prev[at] {

		for _, edgeID := range n.Nodes[prev[at]].OutgoingEdges {
			edge, exists := n.Edges[edgeID]
			if exists && edge.ToNodeID == at {
				path = append([]int{edgeID}, path...)
				break
			}
		}
	}

	return path
}


func (n *Network) Validate() bool {

	return true
}


func (n *Network) AddPOI(poi *POI) {
	n.mutex.Lock()
	defer n.mutex.Unlock()

	n.POIs[poi.ID] = poi


	if node, exists := n.Nodes[poi.NodeID]; exists {
		AttachPOI(node, poi)
	}
}


func (n *Network) GetPOI(id int) (*POI, bool) {
	n.mutex.RLock()
	defer n.mutex.RUnlock()

	poi, exists := n.POIs[id]
	return poi, exists
}


func (n *Network) GetPOIsByType(poiType POIType) []*POI {
	n.mutex.RLock()
	defer n.mutex.RUnlock()

	pois := make([]*POI, 0)
	for _, poi := range n.POIs {
		if poi.Type == poiType {
			pois = append(pois, poi)
		}
	}

	return pois
}


func (n *Network) GetAllPOIs() []*POI {
	n.mutex.RLock()
	defer n.mutex.RUnlock()

	pois := make([]*POI, 0, len(n.POIs))
	for _, poi := range n.POIs {
		pois = append(pois, poi)
	}

	return pois
}


func (n *Network) FindPathBetweenPOIs(startPOIID, endPOIID int) []int {
	n.mutex.RLock()
	defer n.mutex.RUnlock()

	startPOI, startExists := n.POIs[startPOIID]
	endPOI, endExists := n.POIs[endPOIID]

	if !startExists || !endExists {
		return []int{}
	}


	return n.FindPath(startPOI.NodeID, endPOI.NodeID)
}
