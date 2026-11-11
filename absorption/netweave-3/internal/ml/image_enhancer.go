package ml

import (
	"image"
	"image/color"
	"image/draw"
	"math/rand"
	"time"

	"github.com/netweave/netweave/internal/graph"
)


type ImageEnhancer struct {
	
	noiseReduction    float64
	contrastEnhancement float64
	edgeDetectionThreshold int

	
	rand *rand.Rand
}


func NewImageEnhancer() *ImageEnhancer {
	return &ImageEnhancer{
		noiseReduction:    0.8,
		contrastEnhancement: 1.2,
		edgeDetectionThreshold: 30,
		rand: rand.New(rand.NewSource(time.Now().UnixNano())),
	}
}


func (e *ImageEnhancer) EnhanceImage(img image.Image) image.Image {
	
	bounds := img.Bounds()
	rgba := image.NewRGBA(bounds)
	draw.Draw(rgba, bounds, img, bounds.Min, draw.Src)

	
	e.reduceNoise(rgba)
	e.enhanceContrast(rgba)
	e.detectEdges(rgba)

	return rgba
}


func (e *ImageEnhancer) reduceNoise(img *image.RGBA) {
	bounds := img.Bounds()
	width, height := bounds.Max.X, bounds.Max.Y

	
	temp := image.NewRGBA(bounds)
	draw.Draw(temp, bounds, img, bounds.Min, draw.Src)

	
	for y := 1; y < height-1; y++ {
		for x := 1; x < width-1; x++ {
			
			if e.rand.Float64() > e.noiseReduction {
				continue
			}

			
			neighbors := make([]color.RGBA, 0, 9)
			for dy := -1; dy <= 1; dy++ {
				for dx := -1; dx <= 1; dx++ {
					r, g, b, a := temp.At(x+dx, y+dy).RGBA()
					neighbors = append(neighbors, color.RGBA{
						uint8(r >> 8),
						uint8(g >> 8),
						uint8(b >> 8),
						uint8(a >> 8),
					})
				}
			}

			
			medianColor := e.medianColor(neighbors)
			img.Set(x, y, medianColor)
		}
	}
}


func (e *ImageEnhancer) enhanceContrast(img *image.RGBA) {
	bounds := img.Bounds()
	width, height := bounds.Max.X, bounds.Max.Y

	for y := 0; y < height; y++ {
		for x := 0; x < width; x++ {
			r, g, b, a := img.At(x, y).RGBA()
			r, g, b, a = r>>8, g>>8, b>>8, a>>8

			
			r = e.adjustContrast(r, e.contrastEnhancement)
			g = e.adjustContrast(g, e.contrastEnhancement)
			b = e.adjustContrast(b, e.contrastEnhancement)

			img.Set(x, y, color.RGBA{uint8(r), uint8(g), uint8(b), uint8(a)})
		}
	}
}


func (e *ImageEnhancer) detectEdges(img *image.RGBA) {
	bounds := img.Bounds()
	width, height := bounds.Max.X, bounds.Max.Y

	
	temp := image.NewRGBA(bounds)
	draw.Draw(temp, bounds, img, bounds.Min, draw.Src)

	
	for y := 1; y < height-1; y++ {
		for x := 1; x < width-1; x++ {
			
			gx := e.sobelX(temp, x, y)
			gy := e.sobelY(temp, x, y)

			
			magnitude := int(gx*gx + gy*gy)

			
			if magnitude > e.edgeDetectionThreshold*e.edgeDetectionThreshold {
				
				r, g, b, a := img.At(x, y).RGBA()
				r, g, b, a = r>>8, g>>8, b>>8, a>>8

				
				r = uint32(float64(r) * 0.7)
				g = uint32(float64(g) * 0.7)
				b = uint32(float64(b) * 0.7)

				img.Set(x, y, color.RGBA{uint8(r), uint8(g), uint8(b), uint8(a)})
			}
		}
	}
}




func (e *ImageEnhancer) medianColor(colors []color.RGBA) color.RGBA {
	if len(colors) == 0 {
		return color.RGBA{0, 0, 0, 255}
	}

	
	luminances := make([]struct {
		color color.RGBA
		lum   float64
	}, len(colors))

	for i, c := range colors {
		luminances[i].color = c
		luminances[i].lum = 0.299*float64(c.R) + 0.587*float64(c.G) + 0.114*float64(c.B)
	}

	
	for i := 0; i < len(luminances); i++ {
		for j := i + 1; j < len(luminances); j++ {
			if luminances[i].lum > luminances[j].lum {
				luminances[i], luminances[j] = luminances[j], luminances[i]
			}
		}
	}

	
	return luminances[len(luminances)/2].color
}


func (e *ImageEnhancer) adjustContrast(value uint32, factor float64) uint32 {
	
	adjusted := 128 + factor*(float64(value)-128)

	
	if adjusted < 0 {
		adjusted = 0
	} else if adjusted > 255 {
		adjusted = 255
	}

	return uint32(adjusted)
}


func (e *ImageEnhancer) sobelX(img *image.RGBA, x, y int) float64 {
	
	
	
	

	
	lum00 := e.luminance(img.At(x-1, y-1))
	
	lum02 := e.luminance(img.At(x+1, y-1))
	lum10 := e.luminance(img.At(x-1, y))
	lum12 := e.luminance(img.At(x+1, y))
	lum20 := e.luminance(img.At(x-1, y+1))
	
	lum22 := e.luminance(img.At(x+1, y+1))

	
	return -lum00 + lum02 - 2*lum10 + 2*lum12 - lum20 + lum22
}


func (e *ImageEnhancer) sobelY(img *image.RGBA, x, y int) float64 {
	
	
	
	

	
	lum00 := e.luminance(img.At(x-1, y-1))
	lum01 := e.luminance(img.At(x, y-1))
	lum02 := e.luminance(img.At(x+1, y-1))
	lum20 := e.luminance(img.At(x-1, y+1))
	lum21 := e.luminance(img.At(x, y+1))
	lum22 := e.luminance(img.At(x+1, y+1))

	
	return -lum00 - 2*lum01 - lum02 + lum20 + 2*lum21 + lum22
}


func (e *ImageEnhancer) luminance(c color.Color) float64 {
	r, g, b, _ := c.RGBA()
	r, g, b = r>>8, g>>8, b>>8
	return 0.299*float64(r) + 0.587*float64(g) + 0.114*float64(b)
}


func ProcessImageToNetwork(img image.Image) *graph.Network {
	enhancer := NewImageEnhancer()
	enhancedImg := enhancer.EnhanceImage(img)

	generator := NewGraphGenerator()
	return generator.GenerateFromImage(enhancedImg)
}
