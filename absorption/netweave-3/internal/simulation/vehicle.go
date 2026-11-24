package simulation


type Vehicle struct {
	ID          int
	RoadID      int
	Position    int
	Speed       int
	MaxSpeed    int
	Length      int
	Route       []int
	RouteIdx    int
	TargetSpeed int
	CurrentCell int
	Progress    float64

	OriginPOIID       int
	DestinationPOIID  int
	ReachedSegmentEnd bool

	StuckTimer        float64 
	TimeAtCurrentNode float64 

	
	Type       string
	Aggression float64
	Color      string
	Selected   bool
}


func NewVehicle(id, roadID, maxSpeed int, route []int, originPOIID, destinationPOIID int) *Vehicle {

	colors := []string{"#FF0000", "#00FF00", "#0000FF", "#FFFF00", "#FF00FF", "#00FFFF", "#FF8000", "#8000FF", "#0080FF", "#FF0080"}
	colorIdx := id % len(colors)

	return &Vehicle{
		ID:              id,
		Position:        0,
		Speed:           0,
		MaxSpeed:        maxSpeed,
		Route:           route,
		RouteIdx:        0,
		RoadID:          roadID,
		OriginPOIID:     originPOIID,
		DestinationPOIID: destinationPOIID,
		Length:          1,
		Type:            "car",
		Aggression:      0.5,
		Color:           colors[colorIdx],
		Selected:        false,
		ReachedSegmentEnd: false,
	}
}


func NewVehicleSimple(id, roadID, maxSpeed int, route []int) *Vehicle {
	return NewVehicle(id, roadID, maxSpeed, route, -1, -1)
}


func (v *Vehicle) GetCurrentRoadSegment() int {
	if len(v.Route) == 0 || v.RouteIdx < 0 || v.RouteIdx >= len(v.Route) {
		return -1
	}
	return v.Route[v.RouteIdx]
}


func (v *Vehicle) GetNextRoadSegment() int {
	if len(v.Route) == 0 || v.RouteIdx < 0 || v.RouteIdx >= len(v.Route)-1 {
		return -1
	}
	return v.Route[v.RouteIdx+1]
}


func (v *Vehicle) HasReachedDestination(currentNodeID, destinationNodeID int) bool {
	return v.DestinationPOIID >= 0 && currentNodeID == destinationNodeID
}
