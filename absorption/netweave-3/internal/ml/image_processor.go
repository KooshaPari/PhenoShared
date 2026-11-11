package ml

import (
	"errors"
	"image"
	"image/color"

	"github.com/netweave/netweave/internal/graph"
)


type ImageProcessor struct {
	
	roadColor       color.RGBA
	intersectionColor color.RGBA
	residentialZoneColor color.RGBA
	commercialZoneColor  color.RGBA
	industrialZoneColor  color.RGBA

	
	minRoadLength   int
	maxRoadCurvature float64
	nodeDetectionRadius int
}


func NewImageProcessor() *ImageProcessor {
	return &ImageProcessor{
		roadColor:       color.RGBA{0, 0, 0, 255},          
		intersectionColor: color.RGBA{255, 0, 0, 255},      
		residentialZoneColor: color.RGBA{0, 255, 0, 255},   
		commercialZoneColor: color.RGBA{0, 0, 255, 255},    
		industrialZoneColor: color.RGBA{255, 255, 0, 255},  

		minRoadLength:   10,
		maxRoadCurvature: 0.3,
		nodeDetectionRadius: 5,
	}
}


func (ip *ImageProcessor) SetColorMapping(roadColor, intersectionColor, residentialColor, commercialColor, industrialColor color.RGBA) {
	ip.roadColor = roadColor
	ip.intersectionColor = intersectionColor
	ip.residentialZoneColor = residentialColor
	ip.commercialZoneColor = commercialColor
	ip.industrialZoneColor = industrialColor
}


func (ip *ImageProcessor) ProcessImage(img image.Image) (*graph.Network, error) {
	if img == nil {
		return nil, errors.New("input image is nil")
	}

	network := graph.NewNetwork()

	
	intersections := ip.detectIntersections(img)

	
	nodeIDMap := make(map[[2]int]int) 
	for i, pos := range intersections {
		nodeID := i + 1
		nodeType := "four_way" 

		
		node := graph.NewNode(nodeID, pos, nodeType)
		network.AddNode(node)

		
		nodeIDMap[pos] = nodeID
	}

	
	roads := ip.detectRoads(img, intersections)

	
	for i, road := range roads {
		edgeID := i + 1

		
		startNodeID, exists := nodeIDMap[road.Start]
		if !exists {
			continue
		}

		endNodeID, exists := nodeIDMap[road.End]
		if !exists {
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

	
	zones := ip.detectZones(img)

	
	for _, zone := range zones {
		
		for _, node := range network.Nodes {
			if ip.isNodeInZone(node.Position, zone) {
				node.SetProperty("zone_type", zone.Type)
				node.SetProperty("zone_density", zone.Density)
			}
		}
	}

	return network, nil
}


type IPRoad struct {
	Start      [2]int
	End        [2]int
	Type       string
	Length     int
	Lanes      int
	SpeedLimit int
	Path       [][2]int 
}


type IPZone struct {
	Type     string
	Bounds   [4]int 
	Density  float64
}


func (ip *ImageProcessor) detectIntersections(img image.Image) [][2]int {
	
	
	bounds := img.Bounds()
	width, height := bounds.Max.X, bounds.Max.Y

	intersections := make([][2]int, 0)

	
	for x := 0; x < width; x++ {
		for y := 0; y < height; y++ {
			r, g, b, _ := img.At(x, y).RGBA()
			if r > 50000 && g < 10000 && b < 10000 { 
				intersections = append(intersections, [2]int{x, y})
			}
		}
	}

	return intersections
}


func (ip *ImageProcessor) detectRoads(img image.Image, intersections [][2]int) []IPRoad {
	
	
	roads := make([]IPRoad, 0)

	
	for i := 0; i < len(intersections); i++ {
		for j := i + 1; j < len(intersections); j++ {
			start := intersections[i]
			end := intersections[j]

			
			distance := abs(end[0]-start[0]) + abs(end[1]-start[1])

			
			if distance < 200 {
				road := IPRoad{
					Start:      start,
					End:        end,
					Type:       "street",
					Length:     distance,
					Lanes:      2,
					SpeedLimit: 30,
					Path:       [][2]int{start, end},
				}

				roads = append(roads, road)
			}
		}
	}

	return roads
}


func (ip *ImageProcessor) detectZones(img image.Image) []IPZone {
	
	
	bounds := img.Bounds()
	width, height := bounds.Max.X, bounds.Max.Y

	zones := make([]IPZone, 0)

	
	quadrantSize := width / 2

	
	zones = append(zones, IPZone{
		Type:    "residential",
		Bounds:  [4]int{0, 0, quadrantSize, quadrantSize},
		Density: 0.8,
	})

	
	zones = append(zones, IPZone{
		Type:    "commercial",
		Bounds:  [4]int{quadrantSize, 0, width, quadrantSize},
		Density: 0.6,
	})

	
	zones = append(zones, IPZone{
		Type:    "industrial",
		Bounds:  [4]int{0, quadrantSize, quadrantSize, height},
		Density: 0.4,
	})

	
	zones = append(zones, IPZone{
		Type:    "mixed",
		Bounds:  [4]int{quadrantSize, quadrantSize, width, height},
		Density: 0.7,
	})

	return zones
}


func (ip *ImageProcessor) isNodeInZone(position [2]int, zone IPZone) bool {
	x, y := position[0], position[1]
	return x >= zone.Bounds[0] && x <= zone.Bounds[2] && y >= zone.Bounds[1] && y <= zone.Bounds[3]
}


func abs(x int) int {
	if x < 0 {
		return -x
	}
	return x
}
