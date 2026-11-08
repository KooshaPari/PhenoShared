package render

import (
	"image"
	"image/color"
	"sync"
)


type Visualization struct {
	width      int
	height     int
	image      *image.RGBA
	mutex      sync.RWMutex

	
	roadColor       color.RGBA
	vehicleColor    color.RGBA
	backgroundColor color.RGBA
}


func NewVisualization(width, height int) *Visualization {
	vis := &Visualization{
		width:          width,
		height:         height,
		image:          image.NewRGBA(image.Rect(0, 0, width, height)),
		roadColor:      color.RGBA{100, 100, 100, 255},
		vehicleColor:   color.RGBA{0, 0, 255, 255},
		backgroundColor: color.RGBA{240, 240, 240, 255},
	}

	
	for x := 0; x < width; x++ {
		for y := 0; y < height; y++ {
			vis.image.Set(x, y, vis.backgroundColor)
		}
	}

	return vis
}


func (v *Visualization) Clear() {
	v.mutex.Lock()
	defer v.mutex.Unlock()

	for x := 0; x < v.width; x++ {
		for y := 0; y < v.height; y++ {
			v.image.Set(x, y, v.backgroundColor)
		}
	}
}


func (v *Visualization) DrawRoad(x1, y1, x2, y2 int, width int) {
	v.mutex.Lock()
	defer v.mutex.Unlock()

	
	dx := absInt(x2 - x1)
	dy := absInt(y2 - y1)
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
				if px >= 0 && px < v.width && py >= 0 && py < v.height {
					v.image.Set(px, py, v.roadColor)
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


func (v *Visualization) DrawVehicle(x, y int, size int, color color.RGBA) {
	v.mutex.Lock()
	defer v.mutex.Unlock()

	for dx := -size; dx <= size; dx++ {
		for dy := -size; dy <= size; dy++ {
			px, py := x+dx, y+dy
			if px >= 0 && px < v.width && py >= 0 && py < v.height {
				v.image.Set(px, py, color)
			}
		}
	}
}


func (v *Visualization) GetImage() *image.RGBA {
	v.mutex.RLock()
	defer v.mutex.RUnlock()

	
	bounds := v.image.Bounds()
	img := image.NewRGBA(bounds)

	for x := bounds.Min.X; x < bounds.Max.X; x++ {
		for y := bounds.Min.Y; y < bounds.Max.Y; y++ {
			img.Set(x, y, v.image.At(x, y))
		}
	}

	return img
}



func absInt(x int) int {
	if x < 0 {
		return -x
	}
	return x
}
