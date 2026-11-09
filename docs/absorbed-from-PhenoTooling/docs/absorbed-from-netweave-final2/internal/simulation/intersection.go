package simulation

import (
	"sync"
	"time"
)


type IntersectionType string

const (
	
	FourWay IntersectionType = "four_way"
	
	ThreeWay IntersectionType = "three_way"
	
	Roundabout IntersectionType = "roundabout"
)


type TrafficLightState string

const (
	
	Green TrafficLightState = "green"
	
	Yellow TrafficLightState = "yellow"
	
	Red TrafficLightState = "red"
)


type Intersection struct {
	ID            int
	Type          IntersectionType
	Position      [2]int 
	ConnectedRoads []int 
	TrafficLights map[int]TrafficLightState 

	currentPhase  int
	phaseTimer    time.Duration
	phaseDuration time.Duration
	mutex         sync.RWMutex
}


func NewIntersection(id int, intersectionType IntersectionType, position [2]int) *Intersection {
	return &Intersection{
		ID:            id,
		Type:          intersectionType,
		Position:      position,
		ConnectedRoads: make([]int, 0),
		TrafficLights: make(map[int]TrafficLightState),
		currentPhase:  0,
		phaseTimer:    0,
		phaseDuration: 30 * time.Second,
	}
}


func (i *Intersection) ConnectRoad(roadID int) {
	i.mutex.Lock()
	defer i.mutex.Unlock()

	
	for _, id := range i.ConnectedRoads {
		if id == roadID {
			return
		}
	}

	i.ConnectedRoads = append(i.ConnectedRoads, roadID)
	i.TrafficLights[roadID] = Red 

	
	if len(i.ConnectedRoads) == 1 {
		i.TrafficLights[roadID] = Green
	}
}


func (i *Intersection) Update(dt time.Duration) {
	i.mutex.Lock()
	defer i.mutex.Unlock()

	
	i.phaseTimer += dt

	
	if i.phaseTimer >= i.phaseDuration {
		i.phaseTimer = 0
		i.advancePhase()
	}
}


func (i *Intersection) advancePhase() {
	
	for roadID := range i.TrafficLights {
		i.TrafficLights[roadID] = Red
	}

	
	i.currentPhase = (i.currentPhase + 1) % len(i.ConnectedRoads)

	
	if len(i.ConnectedRoads) > 0 {
		currentRoadID := i.ConnectedRoads[i.currentPhase]
		i.TrafficLights[currentRoadID] = Green
	}
}


func (i *Intersection) GetTrafficLightState(roadID int) TrafficLightState {
	i.mutex.RLock()
	defer i.mutex.RUnlock()

	state, exists := i.TrafficLights[roadID]
	if !exists {
		return Red 
	}

	return state
}


func (i *Intersection) SetPhaseDuration(duration time.Duration) {
	i.mutex.Lock()
	defer i.mutex.Unlock()

	i.phaseDuration = duration
}


func (i *Intersection) Reset() {
	i.mutex.Lock()
	defer i.mutex.Unlock()

	i.currentPhase = 0
	i.phaseTimer = 0

	
	for roadID := range i.TrafficLights {
		i.TrafficLights[roadID] = Red
	}

	
	if len(i.ConnectedRoads) > 0 {
		i.TrafficLights[i.ConnectedRoads[0]] = Green
	}
}
