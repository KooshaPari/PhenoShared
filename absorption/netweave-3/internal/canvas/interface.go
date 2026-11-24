package canvas

import (
	"image"
	"image/color"
	"sync"
)


type Interface struct {
	width      int
	height     int
	colorMap   *image.RGBA
	toolType   ToolType
	currentColor color.RGBA
	mutex      sync.RWMutex
}


type ToolType string

const (
	
	RoadTool ToolType = "road"
	
	IntersectionTool ToolType = "intersection"
	
	ZoneTool ToolType = "zone"
	
	EraserTool ToolType = "eraser"
)


func NewInterface(width, height int) *Interface {
	canvas := &Interface{
		width:    width,
		height:   height,
		colorMap: image.NewRGBA(image.Rect(0, 0, width, height)),
		toolType: RoadTool,
		currentColor: color.RGBA{0, 0, 0, 255}, 
	}
	
	
	for x := 0; x < width; x++ {
		for y := 0; y < height; y++ {
			canvas.colorMap.Set(x, y, color.RGBA{255, 255, 255, 255})
		}
	}
	
	return canvas
}


func (c *Interface) SetTool(tool ToolType) {
	c.mutex.Lock()
	defer c.mutex.Unlock()
	
	c.toolType = tool
	
	
	switch tool {
	case RoadTool:
		c.currentColor = color.RGBA{0, 0, 0, 255} 
	case IntersectionTool:
		c.currentColor = color.RGBA{255, 0, 0, 255} 
	case ZoneTool:
		c.currentColor = color.RGBA{0, 255, 0, 255} 
	case EraserTool:
		c.currentColor = color.RGBA{255, 255, 255, 255} 
	}
}


func (c *Interface) SetColor(r, g, b uint8) {
	c.mutex.Lock()
	defer c.mutex.Unlock()
	
	c.currentColor = color.RGBA{r, g, b, 255}
}


func (c *Interface) DrawPoint(x, y int) {
	c.mutex.Lock()
	defer c.mutex.Unlock()
	
	if x >= 0 && x < c.width && y >= 0 && y < c.height {
		c.colorMap.Set(x, y, c.currentColor)
	}
}


func (c *Interface) DrawLine(x1, y1, x2, y2 int) {
	c.mutex.Lock()
	defer c.mutex.Unlock()
	
	
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
		if x1 >= 0 && x1 < c.width && y1 >= 0 && y1 < c.height {
			c.colorMap.Set(x1, y1, c.currentColor)
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


func (c *Interface) FillRect(x1, y1, x2, y2 int) {
	c.mutex.Lock()
	defer c.mutex.Unlock()
	
	
	if x1 > x2 {
		x1, x2 = x2, x1
	}
	
	if y1 > y2 {
		y1, y2 = y2, y1
	}
	
	
	x1 = max(0, min(c.width-1, x1))
	y1 = max(0, min(c.height-1, y1))
	x2 = max(0, min(c.width-1, x2))
	y2 = max(0, min(c.height-1, y2))
	
	
	for x := x1; x <= x2; x++ {
		for y := y1; y <= y2; y++ {
			c.colorMap.Set(x, y, c.currentColor)
		}
	}
}


func (c *Interface) GetImage() *image.RGBA {
	c.mutex.RLock()
	defer c.mutex.RUnlock()
	
	
	bounds := c.colorMap.Bounds()
	img := image.NewRGBA(bounds)
	
	for x := bounds.Min.X; x < bounds.Max.X; x++ {
		for y := bounds.Min.Y; y < bounds.Max.Y; y++ {
			img.Set(x, y, c.colorMap.At(x, y))
		}
	}
	
	return img
}


func (c *Interface) Clear() {
	c.mutex.Lock()
	defer c.mutex.Unlock()
	
	for x := 0; x < c.width; x++ {
		for y := 0; y < c.height; y++ {
			c.colorMap.Set(x, y, color.RGBA{255, 255, 255, 255})
		}
	}
}


func abs(x int) int {
	if x < 0 {
		return -x
	}
	return x
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}

func max(a, b int) int {
	if a > b {
		return a
	}
	return b
}
