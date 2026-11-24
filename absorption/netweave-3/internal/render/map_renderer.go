package render

import (
	"image"
	"image/color"
	"image/draw"
	"math"
	"math/rand"
	"sync"

	"github.com/llgcode/draw2d/draw2dimg"
)


type MapRenderer struct {
	width        int
	height       int
	roadColor    color.RGBA
	highwayColor color.RGBA
	nodeColor    color.RGBA
	bgColor      color.RGBA
	carColors    []color.RGBA
	mutex        sync.Mutex
	baseImage    *image.RGBA
	hasBaseMap   bool
}


func NewMapRenderer(width, height int) *MapRenderer {
	return &MapRenderer{
		width:        width,
		height:       height,
		roadColor:    color.RGBA{100, 100, 100, 255},
		highwayColor: color.RGBA{80, 80, 80, 255},
		nodeColor:    color.RGBA{50, 50, 50, 255},
		bgColor:      color.RGBA{240, 240, 240, 255},
		carColors: []color.RGBA{
			{255, 0, 0, 255},    
			{0, 0, 255, 255},    
			{0, 180, 0, 255},    
			{255, 165, 0, 255},  
			{128, 0, 128, 255},  
			{255, 192, 203, 255}, 
		},
		hasBaseMap: false,
	}
}


func (r *MapRenderer) RenderBaseMap(nodes []Node, edges []Edge) *image.RGBA {
	r.mutex.Lock()
	defer r.mutex.Unlock()

	
	img := image.NewRGBA(image.Rect(0, 0, r.width, r.height))

	
	draw.Draw(img, img.Bounds(), &image.Uniform{r.bgColor}, image.Point{}, draw.Src)

	
	gc := draw2dimg.NewGraphicContext(img)

	
	r.drawGrid(gc)

	
	for _, edge := range edges {
		r.drawRoad(gc, nodes[edge.From], nodes[edge.To], edge.Type)
	}

	
	for _, node := range nodes {
		r.drawIntersection(gc, node)
	}

	
	r.baseImage = img
	r.hasBaseMap = true

	return img
}


func (r *MapRenderer) RenderTraffic(nodes []Node, edges []Edge, vehicles []Vehicle) *image.RGBA {
	r.mutex.Lock()
	defer r.mutex.Unlock()

	var img *image.RGBA

	
	if r.hasBaseMap {
		
		img = image.NewRGBA(image.Rect(0, 0, r.width, r.height))
		draw.Draw(img, img.Bounds(), r.baseImage, image.Point{}, draw.Src)
	} else {
		img = r.RenderBaseMap(nodes, edges)
	}

	
	gc := draw2dimg.NewGraphicContext(img)

	
	for _, vehicle := range vehicles {
		r.drawVehicle(gc, nodes, edges, vehicle)
	}

	return img
}


func (r *MapRenderer) GenerateRandomNetwork(nodeCount int) ([]Node, []Edge) {
	
	nodes := r.generateStructuredNodes(nodeCount)

	
	edges := r.generateRealisticEdges(nodes)

	return nodes, edges
}


func (r *MapRenderer) generateStructuredNodes(nodeCount int) []Node {
	nodes := make([]Node, 0, nodeCount)

	
	useGrid := rand.Intn(2) == 0

	if useGrid {
		
		gridSize := int(math.Sqrt(float64(nodeCount)))
		cellWidth := r.width / (gridSize + 1)
		cellHeight := r.height / (gridSize + 1)

		for i := 0; i < nodeCount; i++ {
			row := i / gridSize
			col := i % gridSize

			
			jitterX := rand.Intn(cellWidth/2) - cellWidth/4
			jitterY := rand.Intn(cellHeight/2) - cellHeight/4

			x := (col+1)*cellWidth + jitterX
			y := (row+1)*cellHeight + jitterY

			
			x = clamp(x, 50, r.width-50)
			y = clamp(y, 50, r.height-50)

			nodes = append(nodes, Node{
				ID: i,
				X:  x,
				Y:  y,
				Type: determineNodeType(i, nodeCount),
			})
		}
	} else {
		
		centerX := r.width / 2
		centerY := r.height / 2

		
		nodes = append(nodes, Node{
			ID: 0,
			X:  centerX,
			Y:  centerY,
			Type: "major_intersection",
		})

		
		rings := 3
		nodesPerRing := (nodeCount - 1) / rings

		nodeID := 1
		for ring := 1; ring <= rings; ring++ {
			radius := float64((r.width / 2) * ring / (rings + 1))

			for i := 0; i < nodesPerRing && nodeID < nodeCount; i++ {
				angle := 2 * math.Pi * float64(i) / float64(nodesPerRing)

				
				angleJitter := (rand.Float64() - 0.5) * math.Pi / 8
				radiusJitter := (rand.Float64() - 0.5) * radius / 5

				x := centerX + int((float64(radius)+radiusJitter)*math.Cos(angle+angleJitter))
				y := centerY + int((float64(radius)+radiusJitter)*math.Sin(angle+angleJitter))

				
				x = clamp(x, 50, r.width-50)
				y = clamp(y, 50, r.height-50)

				nodes = append(nodes, Node{
					ID: nodeID,
					X:  x,
					Y:  y,
					Type: determineNodeType(nodeID, nodeCount),
				})

				nodeID++
			}
		}

		
		for nodeID < nodeCount {
			angle := rand.Float64() * 2 * math.Pi
			radius := rand.Float64() * float64(r.width/2-50)

			x := centerX + int(radius*math.Cos(angle))
			y := centerY + int(radius*math.Sin(angle))

			nodes = append(nodes, Node{
				ID: nodeID,
				X:  x,
				Y:  y,
				Type: determineNodeType(nodeID, nodeCount),
			})

			nodeID++
		}
	}

	return nodes
}


func (r *MapRenderer) generateRealisticEdges(nodes []Node) []Edge {
	edges := make([]Edge, 0)
	nodeCount := len(nodes)

	
	edges = append(edges, r.createMinimumSpanningTree(nodes)...)

	
	for i := 0; i < nodeCount; i++ {
		
		for j := 0; j < nodeCount; j++ {
			if i == j {
				continue
			}

			
			alreadyConnected := false
			for _, edge := range edges {
				if (edge.From == i && edge.To == j) || (edge.From == j && edge.To == i) {
					alreadyConnected = true
					break
				}
			}

			if alreadyConnected {
				continue
			}

			
			dist := distance(nodes[i].X, nodes[i].Y, nodes[j].X, nodes[j].Y)

			
			maxDist := r.width / 4
			if dist < maxDist && rand.Float64() < (1.0-float64(dist)/float64(maxDist)) {
				
				roadType := determineRoadType(nodes[i], nodes[j], dist)

				
				edges = append(edges, Edge{
					From: i,
					To:   j,
					Type: roadType,
				})
			}
		}
	}

	return edges
}


func (r *MapRenderer) createMinimumSpanningTree(nodes []Node) []Edge {
	nodeCount := len(nodes)
	edges := make([]Edge, 0, nodeCount-1)

	
	included := make([]bool, nodeCount)
	included[0] = true

	for len(edges) < nodeCount-1 {
		minDist := math.MaxInt32
		var minFrom, minTo int

		for i := 0; i < nodeCount; i++ {
			if !included[i] {
				continue
			}

			for j := 0; j < nodeCount; j++ {
				if included[j] {
					continue
				}

				dist := distance(nodes[i].X, nodes[i].Y, nodes[j].X, nodes[j].Y)
				if dist < minDist {
					minDist = dist
					minFrom = i
					minTo = j
				}
			}
		}

		
		roadType := determineRoadType(nodes[minFrom], nodes[minTo], minDist)
		edges = append(edges, Edge{
			From: minFrom,
			To:   minTo,
			Type: roadType,
		})

		included[minTo] = true
	}

	return edges
}


func (r *MapRenderer) drawGrid(gc *draw2dimg.GraphicContext) {
	gc.SetStrokeColor(color.RGBA{220, 220, 220, 255})
	gc.SetLineWidth(1)

	
	for y := 0; y < r.height; y += 50 {
		gc.MoveTo(0, float64(y))
		gc.LineTo(float64(r.width), float64(y))
		gc.Stroke()
	}

	
	for x := 0; x < r.width; x += 50 {
		gc.MoveTo(float64(x), 0)
		gc.LineTo(float64(x), float64(r.height))
		gc.Stroke()
	}
}


func (r *MapRenderer) drawRoad(gc *draw2dimg.GraphicContext, from, to Node, roadType string) {
	
	var roadWidth float64

	switch roadType {
	case "highway":
		gc.SetStrokeColor(r.highwayColor)
		roadWidth = 8.0
	case "major":
		gc.SetStrokeColor(r.roadColor)
		roadWidth = 6.0
	case "minor":
		gc.SetStrokeColor(r.roadColor)
		roadWidth = 4.0
	default:
		gc.SetStrokeColor(r.roadColor)
		roadWidth = 3.0
	}

	gc.SetLineWidth(roadWidth)
	
	gc.SetLineCap(1) 
	gc.SetLineJoin(1) 

	
	gc.MoveTo(float64(from.X), float64(from.Y))
	gc.LineTo(float64(to.X), float64(to.Y))
	gc.Stroke()

	
	if roadType == "highway" || roadType == "major" {
		
		dx := float64(to.X - from.X)
		dy := float64(to.Y - from.Y)
		length := math.Sqrt(dx*dx + dy*dy)

		
		if length < 20 {
			return
		}

		
		dx /= length
		dy /= length

		
		gc.SetStrokeColor(color.RGBA{255, 255, 255, 200})
		gc.SetLineWidth(1.0)
		gc.SetLineDash([]float64{10, 10}, 0)

		gc.MoveTo(float64(from.X), float64(from.Y))
		gc.LineTo(float64(to.X), float64(to.Y))
		gc.Stroke()

		
		gc.SetLineDash(nil, 0)
	}
}


func (r *MapRenderer) drawIntersection(gc *draw2dimg.GraphicContext, node Node) {
	var radius float64

	
	switch node.Type {
	case "major_intersection":
		radius = 8.0
		gc.SetFillColor(color.RGBA{80, 80, 80, 255})
	case "traffic_light":
		radius = 6.0
		gc.SetFillColor(color.RGBA{100, 100, 100, 255})
	default:
		radius = 4.0
		gc.SetFillColor(r.nodeColor)
	}

	
	gc.SetLineWidth(1.0)
	gc.SetStrokeColor(color.RGBA{50, 50, 50, 255})

	gc.BeginPath()
	gc.ArcTo(float64(node.X), float64(node.Y), radius, radius, 0, 2*math.Pi)
	gc.Close()
	gc.FillStroke()
}


func (r *MapRenderer) drawVehicle(gc *draw2dimg.GraphicContext, nodes []Node, edges []Edge, vehicle Vehicle) {
	
	if vehicle.EdgeID >= len(edges) {
		return
	}

	edge := edges[vehicle.EdgeID]
	from := nodes[edge.From]
	to := nodes[edge.To]

	
	progress := float64(vehicle.Position) / 100.0 
	x := from.X + int(float64(to.X-from.X)*progress)
	y := from.Y + int(float64(to.Y-from.Y)*progress)

	
	angle := math.Atan2(float64(to.Y-from.Y), float64(to.X-from.X))

	
	colorIndex := vehicle.ID % len(r.carColors)
	gc.SetFillColor(r.carColors[colorIndex])

	
	gc.Save()
	gc.Translate(float64(x), float64(y))
	gc.Rotate(angle)

	
	gc.SetLineWidth(1.0)
	gc.SetStrokeColor(color.RGBA{0, 0, 0, 255})

	
	carLength := 10.0 + float64(vehicle.Speed)/2.0
	carWidth := 6.0

	gc.BeginPath()
	gc.MoveTo(-carLength/2, -carWidth/2)
	gc.LineTo(carLength/2, -carWidth/2)
	gc.LineTo(carLength/2, carWidth/2)
	gc.LineTo(-carLength/2, carWidth/2)
	gc.Close()
	gc.FillStroke()

	
	gc.SetFillColor(color.RGBA{200, 200, 255, 255})
	windowInset := 2.0

	gc.BeginPath()
	gc.MoveTo(-carLength/2+windowInset, -carWidth/2+windowInset)
	gc.LineTo(carLength/2-windowInset, -carWidth/2+windowInset)
	gc.LineTo(carLength/2-windowInset, carWidth/2-windowInset)
	gc.LineTo(-carLength/2+windowInset, carWidth/2-windowInset)
	gc.Close()
	gc.Fill()

	gc.Restore()
}




type Node struct {
	ID   int
	X    int
	Y    int
	Type string
}


type Edge struct {
	From int
	To   int
	Type string
}


type Vehicle struct {
	ID       int
	EdgeID   int
	Position int 
	Speed    int
}


func distance(x1, y1, x2, y2 int) int {
	dx := x2 - x1
	dy := y2 - y1
	return int(math.Sqrt(float64(dx*dx + dy*dy)))
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


func determineNodeType(id, totalNodes int) string {
	
	if id == 0 || id == totalNodes/2 || id == totalNodes-1 {
		return "major_intersection"
	}

	
	if id%5 == 0 {
		return "traffic_light"
	}

	
	return "intersection"
}


func determineRoadType(from, to Node, distance int) string {
	
	if (from.Type == "major_intersection" && to.Type == "major_intersection") ||
		distance > 200 {
		return "highway"
	}

	
	if from.Type == "traffic_light" || to.Type == "traffic_light" ||
		distance > 100 {
		return "major"
	}

	
	if distance > 50 {
		return "minor"
	}

	
	return "local"
}
