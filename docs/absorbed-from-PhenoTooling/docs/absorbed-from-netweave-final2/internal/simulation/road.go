package simulation

import (
	"log"
	"math/rand"
	"sync"
)


type Road struct {
	ID          int
	Length      int
	Lanes       int
	SpeedLimit  int
	Cells       [][]Cell
	StartNodeID int
	EndNodeID   int
	Type        string
	mutex       sync.RWMutex
}


func NewRoad(id, length, lanes, speedLimit, startNodeID, endNodeID int, roadType string) *Road {
	road := &Road{
		ID:          id,
		Length:      length,
		Lanes:       lanes,
		SpeedLimit:  speedLimit,
		StartNodeID: startNodeID,
		EndNodeID:   endNodeID,
		Type:        roadType,
	}


	road.Cells = make([][]Cell, lanes)
	for i := 0; i < lanes; i++ {
		road.Cells[i] = make([]Cell, length)
		for j := 0; j < length; j++ {
			road.Cells[i][j] = Cell{
				occupied:  false,
				vehicleID: -1,
				roadID:    id,
				position:  j,
			}
		}
	}

	return road
}


func (r *Road) AddVehicle(vehicleID, lane, position int) bool {
	r.mutex.Lock()
	defer r.mutex.Unlock()

	if lane < 0 || lane >= r.Lanes || position < 0 || position >= r.Length {
		return false
	}

	if r.Cells[lane][position].occupied {
		return false
	}

	r.Cells[lane][position].occupied = true
	r.Cells[lane][position].vehicleID = vehicleID
	return true
}


func (r *Road) RemoveVehicle(lane, position int) {
	r.mutex.Lock()
	defer r.mutex.Unlock()

	if lane < 0 || lane >= r.Lanes || position < 0 || position >= r.Length {
		return
	}

	r.Cells[lane][position].occupied = false
	r.Cells[lane][position].vehicleID = -1
}


func (r *Road) MoveVehicle(vehicleID, fromLane, fromPos, toLane, toPos int) bool {
	r.mutex.Lock()
	defer r.mutex.Unlock()


	if fromLane < 0 || fromLane >= r.Lanes || fromPos < 0 || fromPos >= r.Length ||
		toLane < 0 || toLane >= r.Lanes || toPos < 0 || toPos >= r.Length {
		return false
	}


	if !r.Cells[fromLane][fromPos].occupied || r.Cells[fromLane][fromPos].vehicleID != vehicleID || r.Cells[toLane][toPos].occupied {
		return false
	}


	r.Cells[toLane][toPos].occupied = true
	r.Cells[toLane][toPos].vehicleID = vehicleID
	r.Cells[fromLane][fromPos].occupied = false
	r.Cells[fromLane][fromPos].vehicleID = -1

	return true
}


func (r *Road) IsOccupied(lane, position int) bool {
	r.mutex.RLock()
	defer r.mutex.RUnlock()

	if lane < 0 || lane >= r.Lanes || position < 0 || position >= r.Length {
		return false
	}

	return r.Cells[lane][position].occupied
}


func (r *Road) GetVehicleAt(lane, position int) int {
	r.mutex.RLock()
	defer r.mutex.RUnlock()

	if lane < 0 || lane >= r.Lanes || position < 0 || position >= r.Length {
		return -1
	}

	if !r.Cells[lane][position].occupied {
		return -1
	}

	return r.Cells[lane][position].vehicleID
}



func (r *Road) calculateGap(lane, position int) int {
	
	gap := 0
	pos := position + 1

	
	for pos < r.Length {
		if r.Cells[lane][pos].occupied {
			return gap
		}
		gap++
		pos++
	}

	
	return gap
}

func (r *Road) Update() {
	r.mutex.Lock()
	defer r.mutex.Unlock()

	
	sim := GetSimulation()
	if sim == nil {
		log.Println("Error: Simulation is nil in Road.Update()")
		return
	}

	
	nextCells := make([][]Cell, r.Lanes)
	for i := range nextCells {
		nextCells[i] = make([]Cell, r.Length)
		for j := range nextCells[i] {
			nextCells[i][j] = Cell{
				occupied:  false,
				vehicleID: -1,
				roadID:    r.ID,
				position:  j,
			}
		}
	}

	
	vehicleMap := make(map[int]*Vehicle)
	for _, v := range sim.Vehicles {
		if v.RoadID == r.ID {
			vehicleMap[v.ID] = v
		}
	}

	
	type roadVehicle struct {
		vehicleID int
		lane      int
		position  int
		speed     int
		vehicle   *Vehicle 
	}
	vehicles := make([]roadVehicle, 0)

	
	for lane := 0; lane < r.Lanes; lane++ {
		for pos := 0; pos < r.Length; pos++ {
			if r.Cells[lane][pos].occupied {
				vehicleID := r.Cells[lane][pos].vehicleID

				
				if vehicle, exists := vehicleMap[vehicleID]; exists && vehicle.RoadID == r.ID {
					vehicles = append(vehicles, roadVehicle{
						vehicleID: vehicleID,
						lane:      lane,
						position:  pos,
						speed:     vehicle.Speed,
						vehicle:   vehicle, 
					})
				}
			}
		}
	}

	
	rand.Shuffle(len(vehicles), func(i, j int) {
		vehicles[i], vehicles[j] = vehicles[j], vehicles[i]
	})

	for _, v := range vehicles {
		
		vehicle := v.vehicle
		if vehicle == nil {
			continue 
		}

		
		if vehicle.Speed < r.SpeedLimit {
			vehicle.Speed++
		}

		
		gap := r.calculateGap(v.lane, v.position)
		if vehicle.Speed > gap {
			vehicle.Speed = gap
		}

		
		if vehicle.Speed > 0 && rand.Float64() < 0.2 { 
			vehicle.Speed--
		}

		
		newPosition := v.position + vehicle.Speed

		
		if newPosition >= r.Length {
			
			vehicle.ReachedSegmentEnd = true
			vehicle.Position = r.Length - 1 

			
			nextCells[v.lane][r.Length-1].occupied = true
			nextCells[v.lane][r.Length-1].vehicleID = v.vehicleID
		} else {
			
			if !nextCells[v.lane][newPosition].occupied {
				
				nextCells[v.lane][newPosition].occupied = true
				nextCells[v.lane][newPosition].vehicleID = v.vehicleID
				vehicle.Position = newPosition
			} else {
				
				foundFreeCell := false

				
				for offset := -1; offset <= 1; offset += 2 { 
					newLane := v.lane + offset
					if newLane >= 0 && newLane < r.Lanes {
						
						canChangeLane := true

						
						for checkPos := newPosition - 1; checkPos <= newPosition + 1; checkPos++ {
							if checkPos >= 0 && checkPos < r.Length && nextCells[newLane][checkPos].occupied {
								canChangeLane = false
								break
							}
						}

						if canChangeLane {
							nextCells[newLane][newPosition].occupied = true
							nextCells[newLane][newPosition].vehicleID = v.vehicleID
							vehicle.Position = newPosition
							foundFreeCell = true
							break
						}
					}
				}

				
				if !foundFreeCell {
					for offset := -1; offset <= 1; offset++ {
						tryPos := newPosition + offset
						if tryPos > v.position && tryPos < r.Length && !nextCells[v.lane][tryPos].occupied {
							nextCells[v.lane][tryPos].occupied = true
							nextCells[v.lane][tryPos].vehicleID = v.vehicleID
							vehicle.Position = tryPos
							foundFreeCell = true
							break
						}
					}
				}

				
				if !foundFreeCell {
					nextCells[v.lane][v.position].occupied = true
					nextCells[v.lane][v.position].vehicleID = v.vehicleID
					vehicle.Position = v.position
				}
			}
		}
	}

	
	r.Cells = nextCells
}


func (r *Road) Reset() {
	r.mutex.Lock()
	defer r.mutex.Unlock()


	for i := range r.Cells {
		for j := range r.Cells[i] {
			r.Cells[i][j].occupied = false
			r.Cells[i][j].vehicleID = -1
		}
	}
}


func (r *Road) CountOccupiedCells() int {
	r.mutex.RLock()
	defer r.mutex.RUnlock()

	count := 0
	for i := range r.Cells {
		for j := range r.Cells[i] {
			if r.Cells[i][j].occupied {
				count++
			}
		}
	}

	return count
}


func (r *Road) CalculateCongestion() float64 {
	r.mutex.RLock()
	defer r.mutex.RUnlock()

	totalCells := r.Length * r.Lanes
	if totalCells == 0 {
		return 0.0
	}

	occupiedCount := 0
	for i := range r.Cells {
		for j := range r.Cells[i] {
			if r.Cells[i][j].occupied {
				occupiedCount++
			}
		}
	}

	return float64(occupiedCount) / float64(totalCells)
}


func (r *Road) RemoveVehicleByID(vehicleID int) {
	r.mutex.Lock()
	defer r.mutex.Unlock()


	for i := range r.Cells {
		for j := range r.Cells[i] {
			if r.Cells[i][j].occupied && r.Cells[i][j].vehicleID == vehicleID {
				r.Cells[i][j].occupied = false
				r.Cells[i][j].vehicleID = -1
				return
			}
		}
	}
}
