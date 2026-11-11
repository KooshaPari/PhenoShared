package simulation

import (
	"log"
)


func (s *Simulation) calculateRouteToDestinationAStar(startRoadID, destPOIID int) []int {
	
	if startRoadID >= len(s.Roads) || startRoadID < 0 {
		log.Printf("Invalid start road ID: %d", startRoadID)
		return []int{}
	}

	
	destNodeID, exists := s.poiIDToNodeID[destPOIID]
	if !exists {
		log.Printf("Destination POI %d has no node ID mapping", destPOIID)
		return []int{startRoadID}
	}

	
	destIntersectionID, exists := s.nodeIDToIntersectionID[destNodeID]
	if !exists {
		log.Printf("Destination node %d has no intersection ID mapping", destNodeID)
		return []int{startRoadID}
	}

	
	currentRoad := s.Roads[startRoadID]
	startIntersectionID := currentRoad.EndNodeID

	
	if startIntersectionID == destIntersectionID {
		return []int{startRoadID}
	}

	
	openSet := make(map[int]bool)
	closedSet := make(map[int]bool)
	gScore := make(map[int]float64)
	fScore := make(map[int]float64)
	cameFrom := make(map[int]struct {
		prevIntersection int
		roadID           int
	})

	
	for i := range s.Intersections {
		gScore[i] = float64(^uint(0) >> 1) 
		fScore[i] = float64(^uint(0) >> 1) 
	}

	
	openSet[startIntersectionID] = true
	gScore[startIntersectionID] = 0
	fScore[startIntersectionID] = s.estimateDistance(startIntersectionID, destIntersectionID)

	for len(openSet) > 0 {
		
		current := -1
		lowestFScore := float64(^uint(0) >> 1)

		for nodeID := range openSet {
			if fScore[nodeID] < lowestFScore {
				lowestFScore = fScore[nodeID]
				current = nodeID
			}
		}

		
		if current == destIntersectionID {
			
			path := []int{}
			for current != startIntersectionID {
				fromData, exists := cameFrom[current]
				if !exists {
					log.Printf("Path reconstruction failed, falling back to BFS")
					return s.calculateRouteBFS(startRoadID, destIntersectionID)
				}
				path = append([]int{fromData.roadID}, path...)
				current = fromData.prevIntersection
			}

			return append([]int{startRoadID}, path...)
		}

		
		delete(openSet, current)
		closedSet[current] = true

		
		for roadID, road := range s.Roads {
			if road.StartNodeID != current {
				continue
			}

			neighbor := road.EndNodeID

			
			if closedSet[neighbor] {
				continue
			}

			
			tentativeGScore := gScore[current] + s.calculateRoadCost(road)

			
			if !openSet[neighbor] {
				openSet[neighbor] = true
			} else if tentativeGScore >= gScore[neighbor] {
				
				continue
			}

			
			cameFrom[neighbor] = struct {
				prevIntersection int
				roadID           int
			}{current, roadID}

			gScore[neighbor] = tentativeGScore
			fScore[neighbor] = gScore[neighbor] + s.estimateDistance(neighbor, destIntersectionID)
		}
	}

	
	log.Printf("No path found from road %d to POI %d using A*, falling back to BFS", startRoadID, destPOIID)
	return s.calculateRouteBFS(startRoadID, destIntersectionID)
}


func (s *Simulation) estimateDistance(from, to int) float64 {
	
	if from < len(s.Intersections) && to < len(s.Intersections) {
		fromPos := s.Intersections[from].Position
		toPos := s.Intersections[to].Position

		dx := float64(fromPos[0] - toPos[0])
		dy := float64(fromPos[1] - toPos[1])

		
		
		if dx < 0 {
			dx = -dx
		}
		if dy < 0 {
			dy = -dy
		}

		
		
		return (dx + dy) * 0.9
	}

	
	return 1.0
}


func (s *Simulation) calculateRoadCost(road Road) float64 {
	
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

	
	congestion := road.CalculateCongestion()
	congestionFactor := 1.0 + congestion

	
	return travelTime * roadFactor * congestionFactor
}


func (s *Simulation) calculateRouteBFS(startRoadID, destIntersectionID int) []int {
	if startRoadID >= len(s.Roads) || startRoadID < 0 {
		log.Printf("BFS: Invalid start road ID: %d", startRoadID)
		return []int{}
	}

	currentRoad := s.Roads[startRoadID]
	startIntersectionID := currentRoad.EndNodeID

	
	if startIntersectionID == destIntersectionID {
		
		
		log.Printf("BFS: Start intersection %d is already destination %d", startIntersectionID, destIntersectionID)
		return []int{startRoadID}
	}

	
	queue := [][]int{{startRoadID}}
	
	visitedIntersections := make(map[int]bool)
	visitedIntersections[startIntersectionID] = true

	for len(queue) > 0 {
		currentPath := queue[0]
		queue = queue[1:]

		
		lastRoadID := currentPath[len(currentPath)-1]
		if lastRoadID < 0 || lastRoadID >= len(s.Roads) {
			log.Printf("BFS: Invalid road ID %d in path, skipping", lastRoadID)
			continue 
		}
		lastRoad := s.Roads[lastRoadID]
		currentIntersectionID := lastRoad.EndNodeID

		
		for nextRoadID, nextRoad := range s.Roads {
			if nextRoad.StartNodeID == currentIntersectionID {
				neighborIntersectionID := nextRoad.EndNodeID

				
				if neighborIntersectionID == destIntersectionID {
					
					newPath := make([]int, len(currentPath))
					copy(newPath, currentPath)
					newPath = append(newPath, nextRoadID)
					log.Printf("BFS: Path found to intersection %d, length %d", destIntersectionID, len(newPath))
					return newPath
				}

				
				if !visitedIntersections[neighborIntersectionID] {
					visitedIntersections[neighborIntersectionID] = true

					
					newPath := make([]int, len(currentPath))
					copy(newPath, currentPath)
					newPath = append(newPath, nextRoadID)
					queue = append(queue, newPath)
				}
			}
		}
	}

	
	log.Printf("BFS: No path found from road %d to intersection %d", startRoadID, destIntersectionID)
	return []int{} 
}
