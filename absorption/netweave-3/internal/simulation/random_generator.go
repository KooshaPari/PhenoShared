package simulation

import (
	"math/rand"
	"time"

	"github.com/netweave/netweave/internal/graph"
)


type RandomNetworkGenerator struct {
	rand *rand.Rand


	width          int
	height         int
	roadDensity    float64
	intersectionDensity float64
	maxRoadLength  int
	minRoadLength  int
}


func NewRandomNetworkGenerator(width, height int) *RandomNetworkGenerator {
	return &RandomNetworkGenerator{
		rand:          rand.New(rand.NewSource(time.Now().UnixNano())),
		width:         width,
		height:        height,
		roadDensity:   0.6,
		intersectionDensity: 0.1,
		maxRoadLength: 100,
		minRoadLength: 20,
	}
}


func (g *RandomNetworkGenerator) SetParameters(roadDensity, intersectionDensity float64, minRoadLength, maxRoadLength int) {
	g.roadDensity = roadDensity
	g.intersectionDensity = intersectionDensity
	g.minRoadLength = minRoadLength
	g.maxRoadLength = maxRoadLength
}


func (g *RandomNetworkGenerator) GenerateNetwork() *graph.Network {
	network := graph.NewNetwork()


	intersections := g.generateIntersections()


	for i, pos := range intersections {
		nodeID := i + 1
		nodeType := "four_way"
		if g.rand.Float64() < 0.3 {
			nodeType = "three_way"
		}

		node := graph.NewNode(nodeID, pos, nodeType)
		network.AddNode(node)
	}


	roads := g.generateRoads(intersections)


	for i, road := range roads {
		edgeID := i + 1


		startNodeID := road.startNodeIndex + 1
		endNodeID := road.endNodeIndex + 1


		roadType := "street"
		if g.rand.Float64() < 0.2 {
			roadType = "highway"
		}


		lanes := 1
		if roadType == "highway" {
			lanes = 2 + g.rand.Intn(2)
		} else if g.rand.Float64() < 0.3 {
			lanes = 2
		}


		speedLimit := 30
		if roadType == "highway" {
			speedLimit = 60 + g.rand.Intn(40)
		} else {
			speedLimit = 20 + g.rand.Intn(20)
		}


		startPos := intersections[road.startNodeIndex]
		endPos := intersections[road.endNodeIndex]
		length := calculateDistance(startPos, endPos)


		edge := graph.NewEdge(
			edgeID,
			startNodeID,
			endNodeID,
			roadType,
			length,
			lanes,
			speedLimit,
		)

		network.AddEdge(edge)
	}


	g.generatePOIs(network)

	return network
}


type roadConnection struct {
	startNodeIndex int
	endNodeIndex   int
}


func (g *RandomNetworkGenerator) generateIntersections() [][2]int {

	area := g.width * g.height
	targetCount := int(float64(area) * g.intersectionDensity / 10000)


	if targetCount < 4 {
		targetCount = 4
	}


	positions := make([][2]int, 0, targetCount)


	gridSize := int(float64(targetCount) * 0.7)
	gridRows := int(float64(gridSize) * float64(g.height) / float64(g.width))
	if gridRows < 2 {
		gridRows = 2
	}

	gridCols := gridSize / gridRows
	if gridCols < 2 {
		gridCols = 2
	}

	rowSpacing := g.height / (gridRows + 1)
	colSpacing := g.width / (gridCols + 1)

	for row := 1; row <= gridRows; row++ {
		for col := 1; col <= gridCols; col++ {

			jitterX := g.rand.Intn(colSpacing/3) - colSpacing/6
			jitterY := g.rand.Intn(rowSpacing/3) - rowSpacing/6

			x := col * colSpacing + jitterX
			y := row * rowSpacing + jitterY


			x = clamp(x, 10, g.width-10)
			y = clamp(y, 10, g.height-10)

			positions = append(positions, [2]int{x, y})
		}
	}


	for len(positions) < targetCount {
		x := 10 + g.rand.Intn(g.width-20)
		y := 10 + g.rand.Intn(g.height-20)


		tooClose := false
		for _, pos := range positions {
			if calculateDistance([2]int{x, y}, pos) < g.minRoadLength {
				tooClose = true
				break
			}
		}

		if !tooClose {
			positions = append(positions, [2]int{x, y})
		}
	}

	return positions
}


func (g *RandomNetworkGenerator) generateRoads(intersections [][2]int) []roadConnection {
	roads := make([]roadConnection, 0)



	mstRoads := g.generateMinimumSpanningTree(intersections)
	roads = append(roads, mstRoads...)


	maxPossibleRoads := len(intersections) * (len(intersections) - 1) / 2
	targetRoadCount := int(float64(maxPossibleRoads) * g.roadDensity)


	if targetRoadCount > maxPossibleRoads {
		targetRoadCount = maxPossibleRoads
	}


	for len(roads) < targetRoadCount {

		start := g.rand.Intn(len(intersections))
		end := g.rand.Intn(len(intersections))


		if start == end {
			continue
		}


		roadExists := false
		for _, road := range roads {
			if (road.startNodeIndex == start && road.endNodeIndex == end) ||
			   (road.startNodeIndex == end && road.endNodeIndex == start) {
				roadExists = true
				break
			}
		}

		if !roadExists {

			startPos := intersections[start]
			endPos := intersections[end]
			distance := calculateDistance(startPos, endPos)

			if distance >= g.minRoadLength && distance <= g.maxRoadLength {
				roads = append(roads, roadConnection{start, end})
			}
		}
	}

	return roads
}


func (g *RandomNetworkGenerator) generateMinimumSpanningTree(intersections [][2]int) []roadConnection {



	type edge struct {
		start  int
		end    int
		weight int
	}

	edges := make([]edge, 0)
	for i := 0; i < len(intersections); i++ {
		for j := i + 1; j < len(intersections); j++ {
			distance := calculateDistance(intersections[i], intersections[j])
			if distance <= g.maxRoadLength {
				edges = append(edges, edge{i, j, distance})
			}
		}
	}


	for i := 0; i < len(edges); i++ {
		for j := i + 1; j < len(edges); j++ {
			if edges[i].weight > edges[j].weight {
				edges[i], edges[j] = edges[j], edges[i]
			}
		}
	}


	parent := make([]int, len(intersections))
	for i := range parent {
		parent[i] = i
	}


	var find func(int) int
	find = func(x int) int {
		if parent[x] != x {
			parent[x] = find(parent[x])
		}
		return parent[x]
	}


	union := func(x, y int) {
		parent[find(x)] = find(y)
	}


	mst := make([]roadConnection, 0)
	for _, e := range edges {
		if find(e.start) != find(e.end) {
			union(e.start, e.end)
			mst = append(mst, roadConnection{e.start, e.end})
		}
	}

	return mst
}


func (g *RandomNetworkGenerator) generatePOIs(network *graph.Network) {

	nodeCount := len(network.Nodes)
	poiCount := nodeCount / 3
	if poiCount < 3 {
		poiCount = 3
	}


	poiTypes := []graph.POIType{
		graph.POIResidential,
		graph.POICommercial,
	}


	nodeIDs := make([]int, 0, nodeCount)
	for id := range network.Nodes {
		nodeIDs = append(nodeIDs, id)
	}


	g.shuffleInts(nodeIDs)


	for i := 0; i < poiCount && i < len(nodeIDs); i++ {
		nodeID := nodeIDs[i]
		node := network.Nodes[nodeID]


		poiType := poiTypes[i%len(poiTypes)]


		poi := graph.NewPOI(
			i+1,
			nodeID,
			poiType,
			node.Position,
		)


		network.AddPOI(poi)
	}
}


func (g *RandomNetworkGenerator) shuffleInts(a []int) {
	for i := len(a) - 1; i > 0; i-- {
		j := g.rand.Intn(i + 1)
		a[i], a[j] = a[j], a[i]
	}
}


func calculateDistance(a, b [2]int) int {
	dx := a[0] - b[0]
	dy := a[1] - b[1]
	return int(float64(dx*dx+dy*dy) + 0.5)
}

func clamp(value, min, max int) int {
	if value < min {
		return min
	}
	if value > max {
		return max
	}
	return value
}
