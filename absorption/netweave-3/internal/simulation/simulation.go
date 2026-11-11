package simulation

import (
	"log"
	"math"
	"math/rand"
	"sort"
	"sync"
	"time"

	"github.com/netweave/netweave/internal/graph"
)


var globalSimulation *Simulation


func GetSimulation() *Simulation {
	return globalSimulation
}


type Simulation struct {
	Roads       []Road
	Vehicles    []*Vehicle
	Intersections []Intersection
	Running     bool
	Speed       int
	mutex       sync.RWMutex
	updateChan  chan SimulationUpdate
	stopChan    chan bool


	initialVehicleCount int

	nodeIDToIntersectionID map[int]int
	intersectionIDToNodeID map[int]int
	poiIDToNodeID          map[int]int
}


type SimulationUpdate struct {
	VehiclePositions []VehiclePosition
	Stats            SimulationStats
}


type VehiclePosition struct {
	ID       int
	RoadID   int
	Position int
	Speed    int
}


type SimulationStats struct {
	VehicleCount    int
	AverageSpeed    float64
	CongestionLevel float64
}


func NewSimulation() *Simulation {
	sim := &Simulation{
		Roads:       make([]Road, 0),
		Vehicles:    make([]*Vehicle, 0),
		Intersections: make([]Intersection, 0),
		Running:     false,
		Speed:       100,
		updateChan:  make(chan SimulationUpdate, 10),
		stopChan:    make(chan bool),


		initialVehicleCount: 0,

		nodeIDToIntersectionID: make(map[int]int),
		intersectionIDToNodeID: make(map[int]int),
		poiIDToNodeID:          make(map[int]int),
	}

	
	globalSimulation = sim

	return sim
}


func (s *Simulation) SetRoadNetwork(roads []Road, intersections []Intersection) {
	s.mutex.Lock()
	defer s.mutex.Unlock()

	s.Roads = roads
	s.Intersections = intersections


	s.Vehicles = make([]*Vehicle, 0)

	log.Printf("Road network set: %d roads, %d intersections", len(roads), len(intersections))
}






func (s *Simulation) AddVehicle(params ...interface{}) *Vehicle {
	s.mutex.Lock()
	defer s.mutex.Unlock()

	if len(s.Roads) == 0 {
		log.Println("Cannot add vehicle: no roads in network")
		return nil
	}


	s.initialVehicleCount++


	var roadID int
	var route []int
	var maxSpeed int

	if len(params) == 0 {

		roadID = rand.Intn(len(s.Roads))
		route = []int{roadID}
		maxSpeed = s.Roads[roadID].SpeedLimit
	} else if len(params) == 1 {

		if roadIDParam, ok := params[0].(int); ok {
			roadID = roadIDParam
			route = []int{roadID}
			maxSpeed = s.Roads[roadID].SpeedLimit
		} else {
			log.Println("Invalid parameter type for roadID")
			return nil
		}
	} else if len(params) == 3 {

		var ok1, ok3 bool
		roadID, ok1 = params[0].(int)
		if routeParam, ok2 := params[1].([]int); ok2 {
			route = routeParam
		} else {
			log.Println("Invalid parameter type for route")
			return nil
		}
		maxSpeed, ok3 = params[2].(int)

		if !ok1 || !ok3 {
			log.Println("Invalid parameter types")
			return nil
		}
	} else {
		log.Println("Invalid number of parameters")
		return nil
	}


	if roadID < 0 || roadID >= len(s.Roads) {
		log.Println("Invalid road ID")
		return nil
	}


	vehicle := NewVehicleSimple(len(s.Vehicles), roadID, maxSpeed, route)


	s.Vehicles = append(s.Vehicles, vehicle)


	s.Roads[roadID].AddVehicle(vehicle.ID, 0, 0)

	log.Printf("Added vehicle %d to road %d", vehicle.ID, roadID)
	return vehicle
}


func (s *Simulation) AddVehicles(count int) {
	s.mutex.Lock()

	s.initialVehicleCount += count
	s.mutex.Unlock()

	for i := 0; i < count; i++ {
		s.AddVehicle()
	}
	log.Printf("Added %d vehicles to simulation", count)
}


func (s *Simulation) AddVehiclesBetweenPOIs(count int, network *graph.Network) {
	if network == nil || len(network.POIs) < 2 {
		log.Println("Cannot add POI-based vehicles: no POIs in network")
		return
	}

	s.mutex.Lock()

	s.initialVehicleCount += count
	s.mutex.Unlock()

	pois := network.GetAllPOIs()
	if len(pois) < 2 {
		log.Println("Cannot add POI-based vehicles: need at least 2 POIs")
		return
	}



	residentialPOIs := s.getPOIsByType("residential")
	commercialPOIs := s.getPOIsByType("commercial")


	if len(residentialPOIs) == 0 || len(commercialPOIs) == 0 {
		for i := 0; i < count; i++ {
			originIdx := rand.Intn(len(pois))
			destIdx := rand.Intn(len(pois))

			for destIdx == originIdx {
				destIdx = rand.Intn(len(pois))
			}

			originPOI := pois[originIdx]
			destPOI := pois[destIdx]


			path := network.FindPathBetweenPOIs(originPOI.ID, destPOI.ID)
			if len(path) == 0 {
				continue
			}

			firstEdgeID := path[0]
			roadID := firstEdgeID
			maxSpeed := 30 + rand.Intn(30)

			vehicle := NewVehicle(
				len(s.Vehicles),
				roadID,
				maxSpeed,
				path,
				originPOI.ID,
				destPOI.ID,
			)

			s.Vehicles = append(s.Vehicles, vehicle)

			if roadID < len(s.Roads) {
				s.Roads[roadID].AddVehicle(vehicle.ID, 0, 0)
			}
		}

		log.Printf("Added %d POI-based vehicles to simulation", count)
		return
	}


	for i := 0; i < count; i++ {

		originPOIID := residentialPOIs[rand.Intn(len(residentialPOIs))]
		originNodeID, exists := s.poiIDToNodeID[originPOIID]
		if !exists {
			continue
		}


		originPOI := graph.POI{
			ID: originPOIID,
			NodeID: originNodeID,
		}


		destPOIID := commercialPOIs[rand.Intn(len(commercialPOIs))]
		destNodeID, exists := s.poiIDToNodeID[destPOIID]
		if !exists {
			continue
		}


		destPOI := graph.POI{
			ID: destPOIID,
			NodeID: destNodeID,
		}


		path := network.FindPathBetweenPOIs(originPOI.ID, destPOI.ID)

		if len(path) == 0 {

			continue
		}


		firstEdgeID := path[0]


		roadID := firstEdgeID


		maxSpeed := 30 + rand.Intn(30)

		vehicle := NewVehicle(
			len(s.Vehicles),
			roadID,
			maxSpeed,
			path,
			originPOI.ID,
			destPOI.ID,
		)


		s.Vehicles = append(s.Vehicles, vehicle)


		if roadID < len(s.Roads) {
			s.Roads[roadID].AddVehicle(vehicle.ID, 0, 0)
		}
	}

	log.Printf("Added %d POI-based vehicles to simulation", count)
}


func (s *Simulation) Start() {
	s.mutex.Lock()

	if s.Running {
		s.mutex.Unlock()
		return
	}

	s.Running = true
	s.mutex.Unlock()

	log.Println("Starting simulation")


	go s.run()
}


func (s *Simulation) Stop() {
	s.mutex.Lock()
	defer s.mutex.Unlock()

	if !s.Running {
		return
	}

	s.Running = false
	s.stopChan <- true

	log.Println("Stopping simulation")
}


func (s *Simulation) Reset() {
	s.mutex.Lock()
	defer s.mutex.Unlock()


	wasRunning := s.Running
	if wasRunning {
		s.Running = false
		s.stopChan <- true
	}


	s.Vehicles = make([]*Vehicle, 0)


	s.initialVehicleCount = 0

	for i := range s.Roads {
		s.Roads[i].Reset()
	}

	for i := range s.Intersections {
		s.Intersections[i].Reset()
	}

	log.Println("Simulation reset")


	if wasRunning {
		s.Running = true
		go s.run()
	}
}


func (s *Simulation) SetSpeed(speed int) {
	s.mutex.Lock()
	defer s.mutex.Unlock()

	s.Speed = speed
	log.Printf("Simulation speed set to %dms per step", speed)
}


func (s *Simulation) GetUpdateChannel() <-chan SimulationUpdate {
	return s.updateChan
}


func (s *Simulation) LoadNetwork(network *graph.Network) {
	s.mutex.Lock()
	defer s.mutex.Unlock()


	s.convertNetworkToSimulation(network)

	log.Printf("Loaded network with %d roads and %d intersections", len(s.Roads), len(s.Intersections))
}


func (s *Simulation) convertNetworkToSimulation(network *graph.Network) {

	s.Roads = make([]Road, 0, len(network.Edges))
	s.Intersections = make([]Intersection, 0, len(network.Nodes))
	s.Vehicles = make([]*Vehicle, 0)


	s.nodeIDToIntersectionID = make(map[int]int)
	s.intersectionIDToNodeID = make(map[int]int)
	s.poiIDToNodeID = make(map[int]int)


	for nodeID, node := range network.Nodes {
		intersectionID := len(s.Intersections)


		s.nodeIDToIntersectionID[nodeID] = intersectionID
		s.intersectionIDToNodeID[intersectionID] = nodeID


		intersection := Intersection{
			ID:            intersectionID,
			Position:      node.Position,
			Type:          "standard",
			TrafficLights: make(map[int]TrafficLightState),
			ConnectedRoads: make([]int, 0),
			currentPhase:  0,
			phaseTimer:    0,
			phaseDuration: 5 * time.Second,
			mutex:         sync.RWMutex{},
		}

		s.Intersections = append(s.Intersections, intersection)
	}


	for poiID, poi := range network.POIs {
		s.poiIDToNodeID[poiID] = poi.NodeID
	}


	for edgeID, edge := range network.Edges {

		startIntersectionID, exists := s.nodeIDToIntersectionID[edge.FromNodeID]
		if !exists {
			continue
		}

		endIntersectionID, exists := s.nodeIDToIntersectionID[edge.ToNodeID]
		if !exists {
			continue
		}


		lanes := edge.Lanes
		if lanes <= 0 {
			lanes = 1
		}

		length := edge.Length
		if length <= 0 {
			length = 100
		}

		speedLimit := edge.SpeedLimit
		if speedLimit <= 0 {
			speedLimit = 50
		}


		cells := make([][]Cell, lanes)
		for i := range cells {
			cells[i] = make([]Cell, length)
			for j := range cells[i] {
				cells[i][j] = Cell{
					occupied:  false,
					vehicleID: -1,
					roadID:    edgeID,
					position:  j,
				}
			}
		}

		road := Road{
			ID:               edgeID,
			StartNodeID:      startIntersectionID,
			EndNodeID:        endIntersectionID,
			Length:           length,
			Lanes:            lanes,
			SpeedLimit:       speedLimit,
			Type:             edge.Type,
			Cells:            cells,
			mutex:            sync.RWMutex{},
		}

		s.Roads = append(s.Roads, road)


		if startIntersectionID < len(s.Intersections) {
			s.Intersections[startIntersectionID].ConnectedRoads =
				append(s.Intersections[startIntersectionID].ConnectedRoads, edgeID)
		}

		if endIntersectionID < len(s.Intersections) {
			s.Intersections[endIntersectionID].ConnectedRoads =
				append(s.Intersections[endIntersectionID].ConnectedRoads, edgeID)
		}
	}
}


func (s *Simulation) GetVehicles() []*Vehicle {
	s.mutex.RLock()
	defer s.mutex.RUnlock()


	vehiclesCopy := make([]*Vehicle, len(s.Vehicles))
	copy(vehiclesCopy, s.Vehicles)

	return vehiclesCopy
}


func (s *Simulation) GetStatistics() (float64, int, float64) {
	s.mutex.RLock()
	defer s.mutex.RUnlock()

	vehicleCount := len(s.Vehicles)
	avgSpeed := 0.0
	congestionLevel := 0.0

	if vehicleCount > 0 {

		totalSpeed := 0
		for _, vehicle := range s.Vehicles {
			totalSpeed += vehicle.Speed
		}
		avgSpeed = float64(totalSpeed) / float64(vehicleCount)


		totalCells := 0
		occupiedCells := 0
		for _, road := range s.Roads {
			totalCells += road.Length
			occupiedCells += road.CountOccupiedCells()
		}

		if totalCells > 0 {
			congestionLevel = float64(occupiedCells) / float64(totalCells)
		}
	}

	return avgSpeed, vehicleCount, congestionLevel
}


func (s *Simulation) run() {
	ticker := time.NewTicker(time.Duration(s.Speed) * time.Millisecond)
	defer ticker.Stop()

	for {
		select {
		case <-ticker.C:
			s.step()
		case <-s.stopChan:
			return
		}
	}
}


func (s *Simulation) step() {
	s.mutex.Lock()
	defer s.mutex.Unlock()

	if !s.Running || len(s.Roads) == 0 {
		return
	}


	for i := range s.Intersections {
		s.Intersections[i].Update(time.Millisecond * time.Duration(s.Speed))
	}


	for i := range s.Roads {
		s.Roads[i].Update()
	}


	s.handleRoadTransitions()


	s.maintainVehicleCount(len(s.Vehicles))


	positions := make([]VehiclePosition, 0, len(s.Vehicles))
	totalSpeed := 0

	for _, vehicle := range s.Vehicles {
		positions = append(positions, VehiclePosition{
			ID:       vehicle.ID,
			RoadID:   vehicle.RoadID,
			Position: vehicle.Position,
			Speed:    vehicle.Speed,
		})

		totalSpeed += vehicle.Speed
	}


	stats := SimulationStats{
		VehicleCount: len(s.Vehicles),
	}

	if len(s.Vehicles) > 0 {
		stats.AverageSpeed = float64(totalSpeed) / float64(len(s.Vehicles))


		totalCells := 0
		occupiedCells := 0
		for _, road := range s.Roads {
			totalCells += road.Length
			occupiedCells += road.CountOccupiedCells()
		}

		if totalCells > 0 {
			stats.CongestionLevel = float64(occupiedCells) / float64(totalCells)
		}
	}


	select {
	case s.updateChan <- SimulationUpdate{
		VehiclePositions: positions,
		Stats:            stats,
	}:

	default:

	}
}


func (s *Simulation) Step() {
	s.step()
}


func (s *Simulation) handleRoadTransitions() {

	dt := float64(s.Speed) / 1000.0
	stuckThreshold := 2.0

	vehiclesToRemove := make([]*Vehicle, 0)

	for _, vehicle := range s.Vehicles {
		if vehicle.ReachedSegmentEnd {



			isPotentiallyStuck := vehicle.Speed < 1

			if isPotentiallyStuck {
				vehicle.TimeAtCurrentNode += dt
				log.Printf("Vehicle %d potentially stuck at end of road %d, timer: %.2f", vehicle.ID, vehicle.RoadID, vehicle.TimeAtCurrentNode)
			} else {

				vehicle.TimeAtCurrentNode = 0
			}


			if vehicle.TimeAtCurrentNode > stuckThreshold {
				log.Printf("Vehicle %d stuck at node for >%.1f s, removing.", vehicle.ID, stuckThreshold)
				vehiclesToRemove = append(vehiclesToRemove, vehicle)
				vehicle.TimeAtCurrentNode = 0
				continue
			}


			vehicle.ReachedSegmentEnd = false
			vehicle.TimeAtCurrentNode = 0
			s.moveToNextRoad(vehicle)

		} else {

			vehicle.TimeAtCurrentNode = 0
		}
	}


	if len(vehiclesToRemove) > 0 {
		log.Printf("Removing %d stuck vehicles...", len(vehiclesToRemove))
		newVehicleList := make([]*Vehicle, 0, len(s.Vehicles)-len(vehiclesToRemove))
		removeSet := make(map[int]bool)
		for _, v := range vehiclesToRemove {
			removeSet[v.ID] = true

			if v.RoadID >= 0 && v.RoadID < len(s.Roads) {
				s.Roads[v.RoadID].RemoveVehicleByID(v.ID)
			}
		}

		for _, v := range s.Vehicles {
			if !removeSet[v.ID] {
				newVehicleList = append(newVehicleList, v)
			}
		}
		s.Vehicles = newVehicleList


		for i := 0; i < len(vehiclesToRemove); i++ {
			s.addRandomPOIVehicle()
		}
		log.Printf("Finished removing stuck vehicles. Current count: %d", len(s.Vehicles))
	}
}


func (s *Simulation) moveToNextRoad(vehicle *Vehicle) {

	if vehicle.RoadID < 0 || vehicle.RoadID >= len(s.Roads) {
		log.Printf("Vehicle %d on invalid road %d, attempting to fix", vehicle.ID, vehicle.RoadID)


		if len(s.Roads) > 0 {

			residentialPOIs := s.getPOIsByType("residential")
			if len(residentialPOIs) > 0 {
				poiID := residentialPOIs[rand.Intn(len(residentialPOIs))]
				nodeID, exists := s.poiIDToNodeID[poiID]
				if exists {
					intersectionID, exists := s.nodeIDToIntersectionID[nodeID]
					if exists {

						for i, road := range s.Roads {
							if road.StartNodeID == intersectionID || road.EndNodeID == intersectionID {
								vehicle.RoadID = i
								vehicle.Position = 0
								vehicle.OriginPOIID = poiID


								commercialPOIs := s.getPOIsByType("commercial")
								if len(commercialPOIs) > 0 {
									vehicle.DestinationPOIID = commercialPOIs[rand.Intn(len(commercialPOIs))]
									vehicle.Route = s.calculateRouteToDestinationAStar(vehicle.RoadID, vehicle.DestinationPOIID)
									vehicle.RouteIdx = 0

									s.Roads[i].AddVehicle(vehicle.ID, 0, 0)
									log.Printf("Fixed vehicle %d by placing it on road %d", vehicle.ID, i)
									return
								}
							}
						}
					}
				}
			}
		}


		log.Printf("Could not fix vehicle %d, ignoring", vehicle.ID)
		return
	}

	currentRoad := s.Roads[vehicle.RoadID]


	currentRoad.RemoveVehicleByID(vehicle.ID)


	endNodeID := currentRoad.EndNodeID


	hasReachedDestination := false
	if vehicle.DestinationPOIID >= 0 {
		destNodeID, exists := s.poiIDToNodeID[vehicle.DestinationPOIID]
		if exists {
			destIntersectionID, exists := s.nodeIDToIntersectionID[destNodeID]
			if exists && destIntersectionID == currentRoad.EndNodeID {
				hasReachedDestination = true
				log.Printf("Vehicle %d has reached destination POI %d",
					vehicle.ID, vehicle.DestinationPOIID)
			}
		}
	}


	if hasReachedDestination {
		s.handleVehicleAtDestination(vehicle, endNodeID)
		return
	}


	if vehicle.RouteIdx < len(vehicle.Route)-1 {
		log.Printf("Vehicle %d following route, current index: %d/%d",
			vehicle.ID, vehicle.RouteIdx, len(vehicle.Route)-1)
		if s.tryFollowRoute(vehicle, endNodeID) {
			return
		} else {
			log.Printf("Vehicle %d failed to follow route at index %d",
				vehicle.ID, vehicle.RouteIdx)
		}
	}


	if vehicle.DestinationPOIID >= 0 && (len(vehicle.Route) <= 1 || vehicle.RouteIdx >= len(vehicle.Route)-1) {
		log.Printf("Vehicle %d needs a new route to POI %d (current route length: %d, index: %d)",
			vehicle.ID, vehicle.DestinationPOIID, len(vehicle.Route), vehicle.RouteIdx)


		vehicle.Route = s.calculateRouteToDestinationAStar(vehicle.RoadID, vehicle.DestinationPOIID)
		vehicle.RouteIdx = 0

		log.Printf("Vehicle %d calculated new route with %d segments to POI %d",
			vehicle.ID, len(vehicle.Route), vehicle.DestinationPOIID)

		if len(vehicle.Route) > 1 {
			if s.tryFollowRoute(vehicle, endNodeID) {
				log.Printf("Vehicle %d successfully following new route to POI %d",
					vehicle.ID, vehicle.DestinationPOIID)
				return
			} else {
				log.Printf("Vehicle %d failed to follow new route to POI %d",
					vehicle.ID, vehicle.DestinationPOIID)
			}
		} else {
			log.Printf("Vehicle %d could not find valid route to POI %d",
				vehicle.ID, vehicle.DestinationPOIID)
		}
	}


	nextRoads := make([]int, 0)
	for i, road := range s.Roads {
		if road.StartNodeID == endNodeID && i != vehicle.RoadID {
			nextRoads = append(nextRoads, i)
		}
	}


	if len(nextRoads) == 0 {
		log.Printf("Vehicle %d at dead-end (node %d), turning around",
			vehicle.ID, endNodeID)



		turnaroundRoads := make([]int, 0)
		for i, road := range s.Roads {
			if road.EndNodeID == endNodeID && i != vehicle.RoadID {
				turnaroundRoads = append(turnaroundRoads, i)
			}
		}

		if len(turnaroundRoads) > 0 {

			nextRoadID := turnaroundRoads[rand.Intn(len(turnaroundRoads))]
			vehicle.RoadID = nextRoadID
			vehicle.Position = 0
			s.Roads[nextRoadID].AddVehicle(vehicle.ID, 0, 0)


			if vehicle.DestinationPOIID >= 0 {
				vehicle.Route = s.calculateRouteToDestinationAStar(vehicle.RoadID, vehicle.DestinationPOIID)
				vehicle.RouteIdx = 0
				log.Printf("Vehicle %d turned around and recalculated route with %d segments",
					vehicle.ID, len(vehicle.Route))
			}
			return
		}


		log.Printf("Vehicle %d staying at dead-end, will get new destination", vehicle.ID)

		s.handleVehicleAtDestination(vehicle, endNodeID)
		return
	}


	nextRoadID := s.chooseNextRoadTowardDestination(nextRoads, endNodeID, vehicle.DestinationPOIID)


	vehicle.RoadID = nextRoadID
	vehicle.Position = 0


	s.Roads[nextRoadID].AddVehicle(vehicle.ID, 0, 0)
	log.Printf("Vehicle %d moved to road %d", vehicle.ID, nextRoadID)
}



func (s *Simulation) tryFollowRoute(vehicle *Vehicle, endNodeID int) bool {

	vehicle.RouteIdx++


	if vehicle.RouteIdx >= len(vehicle.Route) {
		log.Printf("Vehicle %d route index %d out of bounds (len: %d)",
			vehicle.ID, vehicle.RouteIdx, len(vehicle.Route))
		vehicle.RouteIdx--
		return false
	}


	nextRoadID := vehicle.Route[vehicle.RouteIdx]


	isValidNextRoad := false
	if nextRoadID >= 0 && nextRoadID < len(s.Roads) {
		road := s.Roads[nextRoadID]
		if road.StartNodeID == endNodeID {
			isValidNextRoad = true
		} else {
			log.Printf("Vehicle %d next road %d starts at node %d, but current road ends at node %d",
				vehicle.ID, nextRoadID, road.StartNodeID, endNodeID)


			for i, r := range s.Roads {
				if r.StartNodeID == endNodeID && r.EndNodeID == road.StartNodeID {

					log.Printf("Vehicle %d found connecting road %d to fix route", vehicle.ID, i)


					newRoute := make([]int, 0, len(vehicle.Route)+1)
					newRoute = append(newRoute, vehicle.Route[:vehicle.RouteIdx]...)
					newRoute = append(newRoute, i)
					newRoute = append(newRoute, vehicle.Route[vehicle.RouteIdx:]...)

					vehicle.Route = newRoute

					return s.tryFollowRoute(vehicle, endNodeID)
				}
			}
		}
	} else {
		log.Printf("Vehicle %d next road ID %d is invalid (valid range: 0-%d)",
			vehicle.ID, nextRoadID, len(s.Roads)-1)
	}


	if isValidNextRoad {

		roadCongestion := float64(s.Roads[nextRoadID].CountOccupiedCells()) / float64(s.Roads[nextRoadID].Length)



		if roadCongestion > 0.8 && len(vehicle.Route) > vehicle.RouteIdx+1 && rand.Float64() < 0.3 {

			log.Printf("Vehicle %d avoiding severely congested road %d (%.2f%% full)",
				vehicle.ID, nextRoadID, roadCongestion*100)


			if vehicle.DestinationPOIID >= 0 {
				newRoute := s.calculateRouteToDestinationAStar(vehicle.RoadID, vehicle.DestinationPOIID)
				if len(newRoute) > 1 && len(newRoute) < len(vehicle.Route)-vehicle.RouteIdx {

					log.Printf("Vehicle %d found better route around congestion (%d segments vs %d remaining)",
						vehicle.ID, len(newRoute), len(vehicle.Route)-vehicle.RouteIdx)
					vehicle.Route = newRoute
					vehicle.RouteIdx = 0
					return s.tryFollowRoute(vehicle, endNodeID)
				} else {
					log.Printf("Vehicle %d staying on current route despite congestion", vehicle.ID)
				}
			}
		}


		vehicle.RoadID = nextRoadID
		vehicle.Position = 0


		startPos := rand.Intn(3)
		if startPos >= s.Roads[nextRoadID].Length {
			startPos = 0
		}

		s.Roads[nextRoadID].AddVehicle(vehicle.ID, 0, startPos)
		log.Printf("Vehicle %d successfully moved to next road %d in route (index %d/%d)",
			vehicle.ID, nextRoadID, vehicle.RouteIdx, len(vehicle.Route)-1)
		return true
	}


	vehicle.RouteIdx--



	if vehicle.DestinationPOIID >= 0 && rand.Float64() < 0.1 {
		log.Printf("Vehicle %d recalculating route after failure (rare case)", vehicle.ID)
		newRoute := s.calculateRouteToDestinationAStar(vehicle.RoadID, vehicle.DestinationPOIID)
		if len(newRoute) > 1 {
			log.Printf("Vehicle %d found new route with %d segments after failure",
				vehicle.ID, len(newRoute))
			vehicle.Route = newRoute
			vehicle.RouteIdx = 0
			return s.tryFollowRoute(vehicle, endNodeID)
		}
	}

	return false
}


func (s *Simulation) handleVehicleAtDestination(vehicle *Vehicle, endNodeID int) {

	log.Printf("Vehicle %d reached destination POI %d", vehicle.ID, vehicle.DestinationPOIID)


	nextRoads := make([]int, 0)
	for i, road := range s.Roads {
		if road.StartNodeID == endNodeID && i != vehicle.RoadID {
			nextRoads = append(nextRoads, i)
		}
	}


	if len(nextRoads) == 0 {
		log.Printf("Vehicle %d at dead-end, staying at current position", vehicle.ID)
		return
	}


	vehicle.OriginPOIID = vehicle.DestinationPOIID


	currentPOIType := ""
	if vehicle.OriginPOIID%2 == 0 {
		currentPOIType = "residential"
	} else {
		currentPOIType = "commercial"
	}

	log.Printf("Vehicle %d at %s POI %d, selecting new destination",
		vehicle.ID, currentPOIType, vehicle.OriginPOIID)


	var newDestPOIs []int
	if currentPOIType == "residential" {

		newDestPOIs = s.getPOIsByType("commercial")
		log.Printf("Found %d commercial POIs as potential destinations", len(newDestPOIs))
	} else {

		newDestPOIs = s.getPOIsByType("residential")
		log.Printf("Found %d residential POIs as potential destinations", len(newDestPOIs))
	}


	if len(newDestPOIs) > 0 {

		validDestinations := make([]int, 0, len(newDestPOIs))
		for _, poiID := range newDestPOIs {
			if poiID != vehicle.OriginPOIID {
				validDestinations = append(validDestinations, poiID)
			}
		}

		if len(validDestinations) > 0 {


			if len(validDestinations) > 3 && rand.Float64() < 0.7 {

				type destDistance struct {
					poiID    int
					distance float64
				}

				distances := make([]destDistance, 0, len(validDestinations))


				for _, destID := range validDestinations {

					originNodeID, exists := s.poiIDToNodeID[vehicle.OriginPOIID]
					if !exists {
						continue
					}

					destNodeID, exists := s.poiIDToNodeID[destID]
					if !exists {
						continue
					}


					_, exists = s.nodeIDToIntersectionID[originNodeID]
					if !exists {
						continue
					}

					_, exists = s.nodeIDToIntersectionID[destNodeID]
					if !exists {
						continue
					}


					jitter := rand.Float64() * 0.3 + 0.85


					distance := float64(len(s.calculateRouteToDestinationAStar(vehicle.RoadID, destID))) * jitter

					distances = append(distances, destDistance{
						poiID:    destID,
						distance: distance,
					})
				}


				sort.Slice(distances, func(i, j int) bool {
					return distances[i].distance > distances[j].distance
				})


				idx := 0
				if len(distances) > 1 && rand.Float64() < 0.3 {
					idx = 1
				} else if len(distances) > 2 && rand.Float64() < 0.15 {
					idx = 2
				}

				if len(distances) > idx {
					vehicle.DestinationPOIID = distances[idx].poiID
				} else {

					vehicle.DestinationPOIID = validDestinations[rand.Intn(len(validDestinations))]
				}
			} else {

				vehicle.DestinationPOIID = validDestinations[rand.Intn(len(validDestinations))]
			}

			log.Printf("Vehicle %d new destination: POI %d", vehicle.ID, vehicle.DestinationPOIID)
		} else {

			log.Printf("Vehicle %d has no valid destinations, staying at current position", vehicle.ID)
			return
		}
	} else {

		log.Printf("Vehicle %d has no valid destinations of appropriate type, staying at current position", vehicle.ID)
		return
	}


	vehicle.Route = s.calculateRouteToDestinationAStar(vehicle.RoadID, vehicle.DestinationPOIID)
	vehicle.RouteIdx = 0


	if len(vehicle.Route) > 1 && s.tryFollowRoute(vehicle, endNodeID) {
		return
	}



	if len(nextRoads) > 1 && vehicle.DestinationPOIID >= 0 {
		nextRoadID := s.chooseNextRoadTowardDestination(nextRoads, endNodeID, vehicle.DestinationPOIID)
		vehicle.RoadID = nextRoadID
	} else {

		nextRoadID := nextRoads[rand.Intn(len(nextRoads))]
		vehicle.RoadID = nextRoadID
	}


	startPos := rand.Intn(3)
	if startPos >= s.Roads[vehicle.RoadID].Length {
		startPos = 0
	}

	vehicle.Position = startPos
	s.Roads[vehicle.RoadID].AddVehicle(vehicle.ID, 0, startPos)
}


func (s *Simulation) chooseNextRoadTowardDestination(nextRoads []int, currentNodeID, destPOIID int) int {

	if destPOIID < 0 || len(nextRoads) <= 1 {
		return nextRoads[rand.Intn(len(nextRoads))]
	}


	destNodeID, exists := s.poiIDToNodeID[destPOIID]
	if !exists {
		return nextRoads[rand.Intn(len(nextRoads))]
	}


	destIntersectionID, exists := s.nodeIDToIntersectionID[destNodeID]
	if !exists {
		return nextRoads[rand.Intn(len(nextRoads))]
	}


	destPos := s.Intersections[destIntersectionID].Position
	currentPos := s.Intersections[currentNodeID].Position

	type roadScore struct {
		roadID int
		score  float64
	}

	scores := make([]roadScore, 0, len(nextRoads))


	scoredRoads := make(map[int]bool)

	for _, roadID := range nextRoads {
		if roadID >= len(s.Roads) || scoredRoads[roadID] {
			continue
		}

		scoredRoads[roadID] = true
		road := s.Roads[roadID]
		endNodeID := road.EndNodeID


		score := 0.0


		if endNodeID == destIntersectionID {
			score = 1000.0
		} else if endNodeID < len(s.Intersections) {

			endPos := s.Intersections[endNodeID].Position


			currentDx := float64(currentPos[0] - destPos[0])
			currentDy := float64(currentPos[1] - destPos[1])
			currentDist := math.Abs(currentDx) + math.Abs(currentDy)


			newDx := float64(endPos[0] - destPos[0])
			newDy := float64(endPos[1] - destPos[1])
			newDist := math.Abs(newDx) + math.Abs(newDy)


			if newDist < currentDist {

				score += 50.0 * (currentDist - newDist) / currentDist
			} else {

				score -= 20.0 * (newDist - currentDist) / currentDist
			}



			currentDistToCenter := math.Sqrt(float64(currentPos[0]*currentPos[0] + currentPos[1]*currentPos[1]))
			destDistToCenter := math.Sqrt(float64(destPos[0]*destPos[0] + destPos[1]*destPos[1]))
			endDistToCenter := math.Sqrt(float64(endPos[0]*endPos[0] + endPos[1]*endPos[1]))

			if destDistToCenter < currentDistToCenter && endDistToCenter < currentDistToCenter {

				score += 30.0 * (currentDistToCenter - endDistToCenter) / currentDistToCenter
			} else if destDistToCenter > currentDistToCenter && endDistToCenter > currentDistToCenter {

				score += 30.0 * (endDistToCenter - currentDistToCenter) / currentDistToCenter
			}


			route := s.calculateRouteToDestinationAStar(roadID, destPOIID)
			if len(route) > 0 {

				score += 80.0 - float64(len(route))


				switch road.Type {
				case "highway":
					score *= 1.2
				case "major":
					score *= 1.1
				case "minor":
					score *= 0.9
				case "local":
					score *= 0.8
				}
			}
		}



		jitter := rand.Float64() * 3.0
		score += jitter

		scores = append(scores, roadScore{roadID: roadID, score: score})
	}


	if len(scores) > 0 {

		sort.Slice(scores, func(i, j int) bool {
			return scores[i].score > scores[j].score
		})


		if len(scores) >= 3 {
			log.Printf("Top road scores: 1st=%f, 2nd=%f, 3rd=%f",
				scores[0].score, scores[1].score, scores[2].score)
		}



		if rand.Float64() < 0.7 && scores[0].score > 0 {
			return scores[0].roadID
		} else if len(scores) > 1 && rand.Float64() < 0.9 {

			return scores[1 % len(scores)].roadID
		} else if len(scores) > 2 {

			return scores[2 % len(scores)].roadID
		}
	}


	return nextRoads[rand.Intn(len(nextRoads))]
}


func (s *Simulation) GetStats() SimulationStats {
	s.mutex.Lock()
	defer s.mutex.Unlock()

	stats := SimulationStats{
		VehicleCount: len(s.Vehicles),
	}

	totalSpeed := 0
	for _, vehicle := range s.Vehicles {
		totalSpeed += vehicle.Speed
	}

	if len(s.Vehicles) > 0 {
		stats.AverageSpeed = float64(totalSpeed) / float64(len(s.Vehicles))
	}


	totalCells := 0
	occupiedCells := 0
	for _, road := range s.Roads {
		totalCells += road.Length
		occupiedCells += road.CountOccupiedCells()
	}

	if totalCells > 0 {
		stats.CongestionLevel = float64(occupiedCells) / float64(totalCells)
	}

	return stats
}


func (s *Simulation) IsRunning() bool {
	s.mutex.Lock()
	defer s.mutex.Unlock()
	return s.Running
}


func (s *Simulation) GetRoads() []Road {
	s.mutex.RLock()
	defer s.mutex.RUnlock()


	roadsCopy := make([]Road, len(s.Roads))
	copy(roadsCopy, s.Roads)

	return roadsCopy
}


func (s *Simulation) getAllPOIIDs() []int {
	poiIDs := make([]int, 0, len(s.poiIDToNodeID))


	for poiID := range s.poiIDToNodeID {
		poiIDs = append(poiIDs, poiID)
	}


	if len(poiIDs) == 0 {

		for _, vehicle := range s.Vehicles {
			if vehicle.OriginPOIID >= 0 && !contains(poiIDs, vehicle.OriginPOIID) {
				poiIDs = append(poiIDs, vehicle.OriginPOIID)
			}
			if vehicle.DestinationPOIID >= 0 && !contains(poiIDs, vehicle.DestinationPOIID) {
				poiIDs = append(poiIDs, vehicle.DestinationPOIID)
			}
		}
	}

	return poiIDs
}


func (s *Simulation) getPOIsByType(poiTypes interface{}) []int {
	poiIDs := make([]int, 0)


	if typeStr, ok := poiTypes.(string); ok {
		for poiID, nodeID := range s.poiIDToNodeID {

			intersectionID, exists := s.nodeIDToIntersectionID[nodeID]
			if !exists {
				continue
			}


			for i := range s.Intersections {
				if i == intersectionID {








					isMatch := false
					switch typeStr {
					case "residential":
						isMatch = poiID%2 == 0
					case "commercial":
						isMatch = poiID%2 == 1
					}

					if isMatch {
						poiIDs = append(poiIDs, poiID)
					}
					break
				}
			}
		}
		return poiIDs
	}


	if typeSlice, ok := poiTypes.([]string); ok {

		typeMap := make(map[string]bool)
		for _, t := range typeSlice {
			typeMap[t] = true
		}

		for poiID, nodeID := range s.poiIDToNodeID {

			intersectionID, exists := s.nodeIDToIntersectionID[nodeID]
			if !exists {
				continue
			}


			for i := range s.Intersections {
				if i == intersectionID {

					poiType := ""
					if poiID%2 == 0 {
						poiType = "residential"
					} else {
						poiType = "commercial"
					}

					if typeMap[poiType] {
						poiIDs = append(poiIDs, poiID)
					}
					break
				}
			}
		}
	}

	return poiIDs
}


func contains(slice []int, val int) bool {
	for _, item := range slice {
		if item == val {
			return true
		}
	}
	return false
}




func (s *Simulation) maintainVehicleCount(targetCount int) {

	validVehicles := make([]*Vehicle, 0, len(s.Vehicles))
	for _, vehicle := range s.Vehicles {
		if vehicle.RoadID >= 0 && vehicle.RoadID < len(s.Roads) {
			validVehicles = append(validVehicles, vehicle)
		}
	}


	if len(validVehicles) < len(s.Vehicles) {
		s.Vehicles = validVehicles
	}
}

func (s *Simulation) addRandomPOIVehicle() {

	residentialPOIs := s.getPOIsByType("residential")
	commercialPOIs := s.getPOIsByType("commercial")


	if len(residentialPOIs) == 0 || len(commercialPOIs) == 0 {
		s.AddVehicle()
		return
	}


	originPOIID := residentialPOIs[rand.Intn(len(residentialPOIs))]


	destPOIID := commercialPOIs[rand.Intn(len(commercialPOIs))]


	originNodeID, exists := s.poiIDToNodeID[originPOIID]
	if !exists {
		log.Printf("Origin POI %d has no node ID mapping", originPOIID)
		s.AddVehicle()
		return
	}


	originIntersectionID, exists := s.nodeIDToIntersectionID[originNodeID]
	if !exists {
		log.Printf("Origin node %d has no intersection ID mapping", originNodeID)
		s.AddVehicle()
		return
	}


	connectedRoads := make([]int, 0)
	for i, road := range s.Roads {
		if road.StartNodeID == originIntersectionID {
			connectedRoads = append(connectedRoads, i)
		}
	}


	if len(connectedRoads) == 0 {
		log.Printf("No roads connected to intersection %d for residential POI %d", originIntersectionID, originPOIID)
		s.AddVehicle()
		return
	}


	roadID := connectedRoads[rand.Intn(len(connectedRoads))]


	route := s.calculateRouteToDestinationAStar(roadID, destPOIID)


	if len(route) <= 1 {
		log.Printf("Could not find valid route from residential POI %d to commercial POI %d", originPOIID, destPOIID)


		for attempts := 0; attempts < 3 && len(route) <= 1; attempts++ {
			destPOIID = commercialPOIs[rand.Intn(len(commercialPOIs))]
			route = s.calculateRouteToDestination(roadID, destPOIID)
		}


		if len(route) <= 1 {
			s.AddVehicle()
			return
		}
	}


	maxSpeed := s.Roads[roadID].SpeedLimit
	if maxSpeed <= 0 {
		maxSpeed = 30 + rand.Intn(30)
	} else {

		maxSpeed = int(float64(maxSpeed) * (0.8 + 0.4*rand.Float64()))
	}


	vehicle := NewVehicle(
		len(s.Vehicles),
		roadID,
		maxSpeed,
		route,
		originPOIID,
		destPOIID,
	)


	s.Vehicles = append(s.Vehicles, vehicle)


	if roadID < len(s.Roads) {
		s.Roads[roadID].AddVehicle(vehicle.ID, 0, 0)
		log.Printf("Added vehicle %d from residential POI %d to commercial POI %d with route length %d",
			vehicle.ID, originPOIID, destPOIID, len(route))
	}
}


func (s *Simulation) calculateRouteToDestination(startRoadID, destPOIID int) []int {

	destNodeID, exists := s.poiIDToNodeID[destPOIID]
	if !exists {

		return []int{startRoadID}
	}


	destIntersectionID, exists := s.nodeIDToIntersectionID[destNodeID]
	if !exists {
		return []int{startRoadID}
	}


	if startRoadID >= len(s.Roads) || startRoadID < 0 {

		return []int{}
	}

	currentRoad := s.Roads[startRoadID]
	startIntersectionID := currentRoad.EndNodeID


	if startIntersectionID == destIntersectionID {
		return []int{startRoadID}
	}





	dist := make(map[int]int)
	prev := make(map[int]int)
	visited := make(map[int]bool)


	for i := range s.Intersections {
		dist[i] = int(^uint(0) >> 1)
		prev[i] = -1
	}


	dist[startIntersectionID] = 0


	for {

		current := -1
		minDist := int(^uint(0) >> 1)

		for i := range s.Intersections {
			if !visited[i] && dist[i] < minDist {
				minDist = dist[i]
				current = i
			}
		}


		if current == -1 || current == destIntersectionID {
			break
		}


		visited[current] = true


		for _, road := range s.Roads {
			if road.StartNodeID == current && !visited[road.EndNodeID] {

				speedLimit := road.SpeedLimit
				if speedLimit <= 0 {
					speedLimit = 1
				}

				travelTime := float64(road.Length) / float64(speedLimit)


				roadFactor := 1.0
				switch road.Type {
				case "highway":
					roadFactor = 0.7
				case "major":
					roadFactor = 0.8
				case "minor":
					roadFactor = 1.2
				case "local":
					roadFactor = 1.5
				}


				newDist := dist[current] + int(travelTime * roadFactor)

				if newDist < dist[road.EndNodeID] {
					dist[road.EndNodeID] = newDist
					prev[road.EndNodeID] = current
				}
			}
		}
	}


	if prev[destIntersectionID] == -1 {

		return s.calculateRouteBFS(startRoadID, destIntersectionID)
	}


	path := []int{}
	current := destIntersectionID


	for current != startIntersectionID {
		prevNode := prev[current]
		if prevNode == -1 {

			return s.calculateRouteBFS(startRoadID, destIntersectionID)
		}


		roadFound := false
		for i, road := range s.Roads {
			if road.StartNodeID == prevNode && road.EndNodeID == current {

				path = append([]int{i}, path...)
				roadFound = true
				break
			}
		}

		if !roadFound {

			return s.calculateRouteBFS(startRoadID, destIntersectionID)
		}

		current = prevNode
	}


	return append([]int{startRoadID}, path...)
}


func (s *Simulation) GetMaxVehicles() int {


	s.mutex.RLock()
	defer s.mutex.RUnlock()
	return s.initialVehicleCount
}
