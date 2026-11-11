package simulation

import (
	"math/rand"
	"sync"
	"time"
)


type CellularAutomata struct {
	cells        []Cell
	vehicles     []*Vehicle
	maxSpeed     int
	randomFactor float64
	mutex        sync.RWMutex
	timeStep     time.Duration
}


type Cell struct {
	occupied bool
	vehicleID int
	roadID    int
	position  int
}


func NewCellularAutomata(cellCount int, maxSpeed int, randomFactor float64) *CellularAutomata {
	ca := &CellularAutomata{
		cells:        make([]Cell, cellCount),
		vehicles:     make([]*Vehicle, 0),
		maxSpeed:     maxSpeed,
		randomFactor: randomFactor,
		timeStep:     100 * time.Millisecond,
	}
	return ca
}


func (ca *CellularAutomata) AddVehicle(v *Vehicle) bool {
	ca.mutex.Lock()
	defer ca.mutex.Unlock()


	if ca.cells[v.Position].occupied {
		return false
	}


	ca.vehicles = append(ca.vehicles, v)
	ca.cells[v.Position].occupied = true
	ca.cells[v.Position].vehicleID = v.ID

	return true
}


func (ca *CellularAutomata) Step() {
	ca.mutex.Lock()
	defer ca.mutex.Unlock()

	
	nextCells := make([]Cell, len(ca.cells))
	copy(nextCells, ca.cells)

	
	for i := range nextCells {
		nextCells[i].occupied = false
		nextCells[i].vehicleID = -1
	}

	
	
	vehicleIndices := rand.Perm(len(ca.vehicles))

	for _, idx := range vehicleIndices {
		v := ca.vehicles[idx]

		
		if v.Speed < ca.maxSpeed {
			v.Speed++
		}

		
		gap := ca.calculateGap(v)
		if v.Speed > gap {
			v.Speed = gap
		}

		
		
		if v.Speed > 0 && rand.Float64() < ca.randomFactor {
			v.Speed--
		}

		
		newPosition := v.Position + v.Speed

		
		if newPosition >= len(ca.cells) {
			
			
			v.Position = len(ca.cells) - 1  
			nextCells[v.Position].occupied = true
			nextCells[v.Position].vehicleID = v.ID
			v.ReachedSegmentEnd = true  
		} else {
			
			if !nextCells[newPosition].occupied {
				
				nextCells[newPosition].occupied = true
				nextCells[newPosition].vehicleID = v.ID
				v.Position = newPosition
			} else {
				
				
				foundFreeCell := false

				
				if newPosition < len(ca.cells)-1 {
					
					for offset := -1; offset <= 1; offset++ {
						tryPos := newPosition + offset

						
						if tryPos >= v.Position && tryPos < len(ca.cells) && !nextCells[tryPos].occupied {
							nextCells[tryPos].occupied = true
							nextCells[tryPos].vehicleID = v.ID
							v.Position = tryPos
							foundFreeCell = true
							break
						}
					}
				}

				
				if !foundFreeCell {
					nextCells[v.Position].occupied = true
					nextCells[v.Position].vehicleID = v.ID
				}
			}
		}
	}

	
	ca.cells = nextCells
}


func (ca *CellularAutomata) calculateGap(v *Vehicle) int {
	gap := 0
	pos := (v.Position + 1) % len(ca.cells)

	for pos != v.Position && !ca.cells[pos].occupied {
		gap++
		pos = (pos + 1) % len(ca.cells)


		if gap >= len(ca.cells) {
			break
		}
	}

	return gap
}


func (ca *CellularAutomata) GetVehicles() []*Vehicle {
	ca.mutex.RLock()
	defer ca.mutex.RUnlock()

	vehiclesCopy := make([]*Vehicle, len(ca.vehicles))
	copy(vehiclesCopy, ca.vehicles)
	return vehiclesCopy
}


func (ca *CellularAutomata) GetVehiclesAtEnd() []*Vehicle {
	ca.mutex.RLock()
	defer ca.mutex.RUnlock()

	result := make([]*Vehicle, 0)
	for _, v := range ca.vehicles {
		if v.ReachedSegmentEnd {
			result = append(result, v)
		}
	}
	return result
}


func (ca *CellularAutomata) RemoveVehicleByID(vehicleID int) bool {
	ca.mutex.Lock()
	defer ca.mutex.Unlock()

	for i, v := range ca.vehicles {
		if v.ID == vehicleID {
			
			if v.Position >= 0 && v.Position < len(ca.cells) {
				ca.cells[v.Position].occupied = false
				ca.cells[v.Position].vehicleID = -1
			}

			
			ca.vehicles = append(ca.vehicles[:i], ca.vehicles[i+1:]...)
			return true
		}
	}

	return false
}


func (ca *CellularAutomata) GetCells() []Cell {
	ca.mutex.RLock()
	defer ca.mutex.RUnlock()

	cellsCopy := make([]Cell, len(ca.cells))
	copy(cellsCopy, ca.cells)
	return cellsCopy
}
