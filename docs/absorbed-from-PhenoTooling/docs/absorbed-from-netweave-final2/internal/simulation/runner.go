package simulation

import (
	"math/rand"
	"sync"
	"time"
)


type SimulationRunner struct {
	simulation *Simulation
	ticker     *time.Ticker
	done       chan bool
	mutex      sync.RWMutex
	running    bool
}


func NewSimulationRunner(simulation *Simulation) *SimulationRunner {
	return &SimulationRunner{
		simulation: simulation,
		done:       make(chan bool),
		running:    false,
	}
}


func (r *SimulationRunner) Start(stepInterval time.Duration) {
	r.mutex.Lock()
	defer r.mutex.Unlock()

	if r.running {
		return
	}

	r.running = true
	r.simulation.Start()
	r.ticker = time.NewTicker(stepInterval)

	go func() {
		for {
			select {
			case <-r.done:
				return
			case <-r.ticker.C:
				r.simulation.Step()
			}
		}
	}()
}


func (r *SimulationRunner) Stop() {
	r.mutex.Lock()
	defer r.mutex.Unlock()

	if !r.running {
		return
	}

	r.ticker.Stop()
	r.done <- true
	r.simulation.Stop()
	r.running = false
}


func (r *SimulationRunner) IsRunning() bool {
	r.mutex.RLock()
	defer r.mutex.RUnlock()

	return r.running
}


func (r *SimulationRunner) SetStepInterval(interval time.Duration) {
	r.mutex.Lock()
	defer r.mutex.Unlock()

	if r.running {
		r.ticker.Stop()
		r.ticker = time.NewTicker(interval)
	}
}


func (r *SimulationRunner) AddRandomVehicles(count int) {
	r.mutex.Lock()
	defer r.mutex.Unlock()

	
	residentialPOIs := r.simulation.getPOIsByType("residential")
	commercialPOIs := r.simulation.getPOIsByType("commercial")

	
	if len(residentialPOIs) > 0 && len(commercialPOIs) > 0 {
		
		for i := 0; i < count; i++ {
			r.simulation.addRandomPOIVehicle()
		}
		return
	}

	
	roads := r.simulation.GetRoads()
	if len(roads) == 0 {
		return
	}

	rnd := rand.New(rand.NewSource(time.Now().UnixNano()))

	for i := 0; i < count; i++ {
		startRoadIdx := rnd.Intn(len(roads))
		startRoad := roads[startRoadIdx]

		routeLength := 1 + rnd.Intn(5)
		route := make([]int, 0, routeLength)
		route = append(route, startRoad.ID)

		currentNodeID := startRoad.EndNodeID
		for j := 1; j < routeLength; j++ {
			connectedRoads := make([]Road, 0)
			for _, road := range roads {
				if road.StartNodeID == currentNodeID && road.ID != route[j-1] {
					connectedRoads = append(connectedRoads, road)
				}
			}

			if len(connectedRoads) == 0 {
				break
			}

			nextRoad := connectedRoads[rnd.Intn(len(connectedRoads))]
			route = append(route, nextRoad.ID)
			currentNodeID = nextRoad.EndNodeID
		}

		maxSpeed := int(float64(startRoad.SpeedLimit) * (0.8 + 0.4*rnd.Float64()))

		r.simulation.AddVehicle(startRoad.ID, route, maxSpeed)
	}
}
