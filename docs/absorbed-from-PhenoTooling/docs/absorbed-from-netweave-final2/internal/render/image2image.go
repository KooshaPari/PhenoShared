package render

import (
	"image"
	"image/color"
	"image/draw"
	"sync"

	"github.com/netweave/netweave/internal/graph"
	"github.com/netweave/netweave/internal/simulation"
)


type Image2Image struct {
	width       int
	height      int
	baseImage   *image.RGBA
	trafficImage *image.RGBA
	mutex       sync.RWMutex
	
	
	roadColor       color.RGBA
	highwayColor    color.RGBA
	intersectionColor color.RGBA
	backgroundColors map[string]color.RGBA 	
		lowTrafficColor  color.RGBA
	medTrafficColor  color.RGBA
	highTrafficColor color.RGBA
}

func NewImage2Image(width, height int) *Image2Image {
	i2i := &Image2Image{
		width:       width,
		height:      height,
		baseImage:   image.NewRGBA(image.Rect(0, 0, width, height)),
		trafficImage: image.NewRGBA(image.Rect(0, 0, width, height)),
		
		roadColor:       color.RGBA{100, 100, 100, 255},      
		highwayColor:    color.RGBA{60, 60, 60, 255},         
		intersectionColor: color.RGBA{80, 80, 80, 255},       
		backgroundColors: make(map[string]color.RGBA),
		
		lowTrafficColor:  color.RGBA{0, 255, 0, 255},         
		medTrafficColor:  color.RGBA{255, 255, 0, 255},       
		highTrafficColor: color.RGBA{255, 0, 0, 255},         
	}
	
	
	i2i.backgroundColors["residential"] = color.RGBA{240, 240, 220, 255}  
	i2i.backgroundColors["commercial"] = color.RGBA{220, 220, 240, 255}   
	i2i.backgroundColors["industrial"] = color.RGBA{240, 220, 220, 255}   
	i2i.backgroundColors["mixed"] = color.RGBA{230, 230, 230, 255}        
	i2i.backgroundColors["default"] = color.RGBA{245, 245, 245, 255}      
	
	
	draw.Draw(i2i.baseImage, i2i.baseImage.Bounds(), &image.Uniform{i2i.backgroundColors["default"]}, image.Point{}, draw.Src)
	draw.Draw(i2i.trafficImage, i2i.trafficImage.Bounds(), image.Transparent, image.Point{}, draw.Src)
	
	return i2i
}


func (i2i *Image2Image) RenderMap(network *graph.Network) {
	i2i.mutex.Lock()
	defer i2i.mutex.Unlock()
	
	
	draw.Draw(i2i.baseImage, i2i.baseImage.Bounds(), &image.Uniform{i2i.backgroundColors["default"]}, image.Point{}, draw.Src)
	
	
	i2i.renderZones(network)
	
	
	i2i.renderEdges(network)
	
	
	i2i.renderNodes(network)
}


func (i2i *Image2Image) UpdateTraffic(network *graph.Network, vehicles []*simulation.Vehicle) {
	i2i.mutex.Lock()
	defer i2i.mutex.Unlock()
	
	
	draw.Draw(i2i.trafficImage, i2i.trafficImage.Bounds(), image.Transparent, image.Point{}, draw.Src)
	
	
	i2i.renderVehicles(network, vehicles)
}


func (i2i *Image2Image) GetImage() *image.RGBA {
	i2i.mutex.RLock()
	defer i2i.mutex.RUnlock()
	
	
	result := image.NewRGBA(i2i.baseImage.Bounds())
	
	
	draw.Draw(result, result.Bounds(), i2i.baseImage, image.Point{}, draw.Src)
	
	
	draw.Draw(result, result.Bounds(), i2i.trafficImage, image.Point{}, draw.Over)
	
	return result
}


func (i2i *Image2Image) renderZones(network *graph.Network) {
	
	
	
	
	draw.Draw(i2i.baseImage, i2i.baseImage.Bounds(), &image.Uniform{i2i.backgroundColors["default"]}, image.Point{}, draw.Src)
}


func (i2i *Image2Image) renderEdges(network *graph.Network) {
	
	
	
	
	for _, edge := range network.Edges {
		fromNode, fromExists := network.GetNode(edge.FromNodeID)
		toNode, toExists := network.GetNode(edge.ToNodeID)
		
		if !fromExists || !toExists {
			continue
		}
		
		
		var roadColor color.RGBA
		if edge.Type == "highway" {
			roadColor = i2i.highwayColor
		} else {
			roadColor = i2i.roadColor
		}
		
		
		i2i.drawLine(
			fromNode.Position[0], fromNode.Position[1],
			toNode.Position[0], toNode.Position[1],
			roadColor, edge.Lanes*2, i2i.baseImage,
		)
	}
}


func (i2i *Image2Image) renderNodes(network *graph.Network) {
	
	
	
	
	for _, node := range network.Nodes {
		i2i.drawCircle(
			node.Position[0], node.Position[1],
			5, 
			i2i.intersectionColor,
			i2i.baseImage,
		)
	}
}


func (i2i *Image2Image) renderVehicles(network *graph.Network, vehicles []*simulation.Vehicle) {
	
	
	
	
	for _, vehicle := range vehicles {
		
		
		
		x, y := vehicle.Position, vehicle.Position
		
		
		var vehicleColor color.RGBA
		speedRatio := float64(vehicle.Speed) / float64(vehicle.MaxSpeed)
		
		if speedRatio < 0.3 {
			vehicleColor = i2i.highTrafficColor 
		} else if speedRatio < 0.7 {
			vehicleColor = i2i.medTrafficColor 
		} else {
			vehicleColor = i2i.lowTrafficColor 
		}
		
		
		i2i.drawCircle(x, y, 2, vehicleColor, i2i.trafficImage)
	}
}


func (i2i *Image2Image) drawLine(x1, y1, x2, y2 int, col color.RGBA, width int, img *image.RGBA) {
	
	
	
	
	dx := abs(x2 - x1)
	dy := abs(y2 - y1)
	sx, sy := 1, 1
	
	if x1 >= x2 {
		sx = -1
	}
	
	if y1 >= y2 {
		sy = -1
	}
	
	err := dx - dy
	
	for {
		
		halfWidth := width / 2
		for ox := -halfWidth; ox <= halfWidth; ox++ {
			for oy := -halfWidth; oy <= halfWidth; oy++ {
				px, py := x1+ox, y1+oy
				if px >= 0 && px < i2i.width && py >= 0 && py < i2i.height {
					img.Set(px, py, col)
				}
			}
		}
		
		if x1 == x2 && y1 == y2 {
			break
		}
		
		e2 := 2 * err
		if e2 > -dy {
			err -= dy
			x1 += sx
		}
		
		if e2 < dx {
			err += dx
			y1 += sy
		}
	}
}


func (i2i *Image2Image) drawCircle(x, y, radius int, col color.RGBA, img *image.RGBA) {
	for px := x - radius; px <= x + radius; px++ {
		for py := y - radius; py <= y + radius; py++ {
			
			if px >= 0 && px < i2i.width && py >= 0 && py < i2i.height {
				dx, dy := px-x, py-y
				if dx*dx + dy*dy <= radius*radius {
					img.Set(px, py, col)
				}
			}
		}
	}
}


func abs(x int) int {
	if x < 0 {
		return -x
	}
	return x
}
