package render

import (
	"fmt"
	"image/png"
	"os"
	"path/filepath"
	"sync"
	"time"

	"github.com/netweave/netweave/internal/graph"
	"github.com/netweave/netweave/internal/simulation"
)


type AnimationRenderer struct {
	renderer      *Image2Image
	frameCount    int
	outputDir     string
	frameInterval time.Duration
	mutex         sync.Mutex
	isRecording   bool
}


func NewAnimationRenderer(width, height int, outputDir string) *AnimationRenderer {
	return &AnimationRenderer{
		renderer:      NewImage2Image(width, height),
		frameCount:    0,
		outputDir:     outputDir,
		frameInterval: 100 * time.Millisecond,
		isRecording:   false,
	}
}


func (a *AnimationRenderer) StartRecording() error {
	a.mutex.Lock()
	defer a.mutex.Unlock()

	if a.isRecording {
		return nil 
	}

	
	err := os.MkdirAll(a.outputDir, 0755)
	if err != nil {
		return err
	}

	a.frameCount = 0
	a.isRecording = true
	return nil
}


func (a *AnimationRenderer) StopRecording() {
	a.mutex.Lock()
	defer a.mutex.Unlock()

	a.isRecording = false
}


func (a *AnimationRenderer) RecordFrame(network *graph.Network, vehicles []*simulation.Vehicle) error {
	a.mutex.Lock()
	defer a.mutex.Unlock()

	if !a.isRecording {
		return nil
	}

	
	a.renderer.RenderMap(network)
	a.renderer.UpdateTraffic(network, vehicles)
	img := a.renderer.GetImage()

	
	frameFilename := filepath.Join(a.outputDir, fmt.Sprintf("frame_%04d.png", a.frameCount))
	file, err := os.Create(frameFilename)
	if err != nil {
		return err
	}
	defer file.Close()

	err = png.Encode(file, img)
	if err != nil {
		return err
	}

	a.frameCount++
	return nil
}


func (a *AnimationRenderer) GetFrameCount() int {
	a.mutex.Lock()
	defer a.mutex.Unlock()

	return a.frameCount
}


func (a *AnimationRenderer) SetFrameInterval(interval time.Duration) {
	a.mutex.Lock()
	defer a.mutex.Unlock()

	a.frameInterval = interval
}


func (a *AnimationRenderer) GetFrameInterval() time.Duration {
	a.mutex.Lock()
	defer a.mutex.Unlock()

	return a.frameInterval
}


func (a *AnimationRenderer) CreateGIF(outputPath string) error {
	
	
	

	
	return nil
}
