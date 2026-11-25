package ml

import (
	"image"
	"image/color"
	"math"
	"sort"

	"github.com/netweave/netweave/internal/graph"
)


type GraphGenerator struct {
	
	minNodeDistance     int
	maxRoadLength       int
	minRoadLength       int
	intersectionRadius  int
	roadWidthThreshold  int

	
	roadColors          []color.RGBA
	intersectionColors  []color.RGBA
	zoneColors          map[string]color.RGBA
}


func NewGraphGenerator() *GraphGenerator {
	generator := &GraphGenerator{
		minNodeDistance:    20,
		maxRoadLength:      500,
		minRoadLength:      10,
		intersectionRadius: 5,
		roadWidthThreshold: 3,

		roadColors: []color.RGBA{
			{0, 0, 0, 255},       
			{100, 100, 100, 255}, 
		},

		intersectionColors: []color.RGBA{
			{255, 0, 0, 255},     
			{255, 100, 0, 255},   
		},

		zoneColors: map[string]color.RGBA{
			"residential": {0, 255, 0, 255},    
			"commercial":  {0, 0, 255, 255},    
			"industrial":  {255, 255, 0, 255},  
		},
	}

	return generator
}


func (g *GraphGenerator) GenerateFromImage(img image.Image) *graph.Network {
	
	network := graph.NewNetwork()

	
	intersections := g.detectIntersections(img)

	
	nodeMap := make(map[Point]int) 
	for i, point := range intersections {
		nodeID := i + 1
		nodeType := g.determineIntersectionType(img, point)

		
		node := graph.NewNode(nodeID, [2]int{point.X, point.Y}, nodeType)
		network.AddNode(node)

		
		nodeMap[point] = nodeID
	}

	
	roads := g.detectRoads(img, intersections)

	
	for i, road := range roads {
		edgeID := i + 1

		
		startNodeID, startExists := nodeMap[road.Start]
		endNodeID, endExists := nodeMap[road.End]

		if !startExists || !endExists {
			continue 
		}

		
		edge := graph.NewEdge(
			edgeID,
			startNodeID,
			endNodeID,
			road.Type,
			road.Length,
			road.Lanes,
			road.SpeedLimit,
		)

		network.AddEdge(edge)
	}

	
	zones := g.detectZones(img)

	
	for _, zone := range zones {
		
		for nodeID, node := range network.Nodes {
			point := Point{node.Position[0], node.Position[1]}
			if g.isPointInRect(point, zone.Bounds) {
				
				node.SetProperty("zone_type", zone.Type)
				node.SetProperty("zone_density", zone.Density)
				network.Nodes[nodeID] = node
			}
		}
	}

	return network
}


type Point struct {
	X, Y int
}


type Road struct {
	Start      Point
	End        Point
	Type       string
	Length     int
	Lanes      int
	SpeedLimit int
	Path       []Point 
}


type Zone struct {
	Type     string
	Bounds   Rect
	Density  float64
}


type Rect struct {
	X1, Y1, X2, Y2 int
}


func (g *GraphGenerator) detectIntersections(img image.Image) []Point {
	bounds := img.Bounds()
	width, height := bounds.Max.X, bounds.Max.Y

	
	candidatePoints := make([]Point, 0)

	for y := 0; y < height; y++ {
		for x := 0; x < width; x++ {
			pixelColor := img.At(x, y)
			r, gb, bb, a := pixelColor.RGBA()
			r, gb, bb, a = r>>8, gb>>8, bb>>8, a>>8 

			
			for _, intersectionColor := range g.intersectionColors {
				if g.colorMatch(color.RGBA{uint8(r), uint8(bb), uint8(gb), uint8(a)}, intersectionColor) {
					candidatePoints = append(candidatePoints, Point{x, y})
					break
				}
			}
		}
	}

	
	intersections := g.clusterPoints(candidatePoints, g.intersectionRadius)

	return intersections
}


func (g *GraphGenerator) detectRoads(img image.Image, intersections []Point) []Road {
	roads := make([]Road, 0)

	
	for i := 0; i < len(intersections); i++ {
		for j := i + 1; j < len(intersections); j++ {
			start := intersections[i]
			end := intersections[j]

			
			distance := g.distance(start, end)

			
			if int(distance) > g.maxRoadLength {
				continue
			}

			
			if int(distance) < g.minRoadLength {
				continue
			}

			
			road := g.traceRoad(img, start, end)
			if road != nil {
				roads = append(roads, *road)
			}
		}
	}

	return roads
}


func (g *GraphGenerator) traceRoad(img image.Image, start, end Point) *Road {
	
	

	
	distance := g.distance(start, end)
	sampleCount := int(distance / 5) 
	if sampleCount < 2 {
		sampleCount = 2
	}

	
	roadPixelCount := 0
	nonRoadPixelCount := 0

	for i := 0; i <= sampleCount; i++ {
		t := float64(i) / float64(sampleCount)
		x := int(float64(start.X)*(1-t) + float64(end.X)*t)
		y := int(float64(start.Y)*(1-t) + float64(end.Y)*t)

		
		if g.isRoadPixel(img, x, y) {
			roadPixelCount++
		} else {
			nonRoadPixelCount++
		}
	}

	
	if roadPixelCount > nonRoadPixelCount {
		
		roadType, lanes, speedLimit := g.determineRoadProperties(img, start, end)

		return &Road{
			Start:      start,
			End:        end,
			Type:       roadType,
			Length:     int(distance),
			Lanes:      lanes,
			SpeedLimit: speedLimit,
			Path:       []Point{start, end},
		}
	}

	return nil
}


func (g *GraphGenerator) detectZones(img image.Image) []Zone {
	bounds := img.Bounds()
	width, height := bounds.Max.X, bounds.Max.Y

	
	

	
	zones := make([]Zone, 0)

	
	quadrants := []Rect{
		{0, 0, width/2, height/2},                
		{width/2, 0, width, height/2},            
		{0, height/2, width/2, height},           
		{width/2, height/2, width, height},       
	}

	for _, quadrant := range quadrants {
		
		zoneCounts := make(map[string]int)
		totalPixels := 0

		for y := quadrant.Y1; y < quadrant.Y2; y++ {
			for x := quadrant.X1; x < quadrant.X2; x++ {
				pixelColor := img.At(x, y)
				r, gb, bb, a := pixelColor.RGBA()
				r, gb, bb, a = r>>8, gb>>8, bb>>8, a>>8 

				
				for zoneType, zoneColor := range g.zoneColors {
					if g.colorMatch(color.RGBA{uint8(r), uint8(bb), uint8(gb), uint8(a)}, zoneColor) {
						zoneCounts[zoneType]++
						totalPixels++
						break
					}
				}
			}
		}

		
		if totalPixels > 0 {
			dominantType := ""
			maxCount := 0

			for zoneType, count := range zoneCounts {
				if count > maxCount {
					maxCount = count
					dominantType = zoneType
				}
			}

			if dominantType != "" {
				
				density := float64(maxCount) / float64(totalPixels)

				zones = append(zones, Zone{
					Type:    dominantType,
					Bounds:  quadrant,
					Density: density,
				})
			}
		}
	}

	return zones
}




func (g *GraphGenerator) clusterPoints(points []Point, radius int) []Point {
	if len(points) == 0 {
		return []Point{}
	}

	
	sort.Slice(points, func(i, j int) bool {
		return points[i].X < points[j].X
	})

	
	clusters := make([][]Point, 0)

	for _, point := range points {
		
		added := false

		for i, cluster := range clusters {
			
			for _, clusterPoint := range cluster {
				if g.distance(point, clusterPoint) <= float64(radius) {
					clusters[i] = append(clusters[i], point)
					added = true
					break
				}
			}

			if added {
				break
			}
		}

		
		if !added {
			clusters = append(clusters, []Point{point})
		}
	}

	
	centroids := make([]Point, len(clusters))

	for i, cluster := range clusters {
		sumX, sumY := 0, 0

		for _, point := range cluster {
			sumX += point.X
			sumY += point.Y
		}

		centroids[i] = Point{
			X: sumX / len(cluster),
			Y: sumY / len(cluster),
		}
	}

	return centroids
}


func (g *GraphGenerator) distance(p1, p2 Point) float64 {
	dx := p1.X - p2.X
	dy := p1.Y - p2.Y
	return math.Sqrt(float64(dx*dx + dy*dy))
}


func (g *GraphGenerator) colorMatch(c1, c2 color.RGBA) bool {
	
	threshold := 30

	rDiff := int(c1.R) - int(c2.R)
	gDiff := int(c1.G) - int(c2.G)
	bDiff := int(c1.B) - int(c2.B)

	return (rDiff*rDiff + gDiff*gDiff + bDiff*bDiff) <= threshold*threshold
}


func (g *GraphGenerator) isRoadPixel(img image.Image, x, y int) bool {
	bounds := img.Bounds()
	if x < bounds.Min.X || x >= bounds.Max.X || y < bounds.Min.Y || y >= bounds.Max.Y {
		return false
	}

	pixelColor := img.At(x, y)
	r, gb, bb, a := pixelColor.RGBA()
	r, gb, bb, a = r>>8, gb>>8, bb>>8, a>>8 

	
	for _, roadColor := range g.roadColors {
		if g.colorMatch(color.RGBA{uint8(r), uint8(bb), uint8(gb), uint8(a)}, roadColor) {
			return true
		}
	}

	return false
}


func (g *GraphGenerator) determineRoadProperties(img image.Image, start, end Point) (string, int, int) {
	
	

	
	roadType := "street"
	lanes := 1
	speedLimit := 30

	
	width := g.estimateRoadWidth(img, start, end)

	
	if width > g.roadWidthThreshold {
		roadType = "highway"
		lanes = 2
		speedLimit = 60
	}

	return roadType, lanes, speedLimit
}


func (g *GraphGenerator) estimateRoadWidth(img image.Image, start, end Point) int {
	
	dx := float64(end.X - start.X)
	dy := float64(end.Y - start.Y)
	length := math.Sqrt(dx*dx + dy*dy)

	if length == 0 {
		return 0
	}

	
	dx /= length
	dy /= length

	
	perpX := -dy
	perpY := dx

	
	midX := (start.X + end.X) / 2
	midY := (start.Y + end.Y) / 2

	
	width := 0
	maxSampleDistance := 20

	
	for i := 1; i <= maxSampleDistance; i++ {
		sampleX := int(float64(midX) + float64(i)*perpX)
		sampleY := int(float64(midY) + float64(i)*perpY)

		if !g.isRoadPixel(img, sampleX, sampleY) {
			break
		}

		width++
	}

	
	for i := 1; i <= maxSampleDistance; i++ {
		sampleX := int(float64(midX) - float64(i)*perpX)
		sampleY := int(float64(midY) - float64(i)*perpY)

		if !g.isRoadPixel(img, sampleX, sampleY) {
			break
		}

		width++
	}

	
	return width + 1
}


func (g *GraphGenerator) determineIntersectionType(img image.Image, point Point) string {
	
	

	
	directions := 0

	
	for angle := 0; angle < 360; angle += 45 {
		radians := float64(angle) * math.Pi / 180.0

		
		hasRoad := false

		for distance := 5; distance <= 15; distance += 5 {
			sampleX := int(float64(point.X) + float64(distance)*math.Cos(radians))
			sampleY := int(float64(point.Y) + float64(distance)*math.Sin(radians))

			if g.isRoadPixel(img, sampleX, sampleY) {
				hasRoad = true
				break
			}
		}

		if hasRoad {
			directions++
		}
	}

	
	if directions >= 4 {
		return "four_way"
	} else if directions >= 3 {
		return "three_way"
	} else if directions == 0 {
		
		pixelColor := img.At(point.X, point.Y)
		r, gb, bb, a := pixelColor.RGBA()
		r, gb, bb, a = r>>8, gb>>8, bb>>8, a>>8

		if g.colorMatch(color.RGBA{uint8(r), uint8(bb), uint8(gb), uint8(a)}, g.intersectionColors[1]) {
			return "roundabout"
		}
	}

	return "three_way" 
}


func (g *GraphGenerator) isPointInRect(point Point, rect Rect) bool {
	return point.X >= rect.X1 && point.X < rect.X2 && point.Y >= rect.Y1 && point.Y < rect.Y2
}
