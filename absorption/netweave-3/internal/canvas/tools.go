package canvas


type Tool struct {
	Type        ToolType
	Size        int
	Color       [3]uint8
	Properties  map[string]interface{}
}


func NewTool(toolType ToolType, size int, color [3]uint8) *Tool {
	return &Tool{
		Type:       toolType,
		Size:       size,
		Color:      color,
		Properties: make(map[string]interface{}),
	}
}


type RoadProperties struct {
	Lanes      int
	SpeedLimit int
	RoadType   string 
}


type IntersectionProperties struct {
	Type string 
}


type ZoneProperties struct {
	ZoneType string 
	Density  float64
}


func (t *Tool) SetRoadProperties(lanes, speedLimit int, roadType string) {
	t.Properties["road"] = RoadProperties{
		Lanes:      lanes,
		SpeedLimit: speedLimit,
		RoadType:   roadType,
	}
}


func (t *Tool) SetIntersectionProperties(intersectionType string) {
	t.Properties["intersection"] = IntersectionProperties{
		Type: intersectionType,
	}
}


func (t *Tool) SetZoneProperties(zoneType string, density float64) {
	t.Properties["zone"] = ZoneProperties{
		ZoneType: zoneType,
		Density:  density,
	}
}


func (t *Tool) GetRoadProperties() (RoadProperties, bool) {
	props, exists := t.Properties["road"]
	if !exists {
		return RoadProperties{}, false
	}
	
	roadProps, ok := props.(RoadProperties)
	return roadProps, ok
}


func (t *Tool) GetIntersectionProperties() (IntersectionProperties, bool) {
	props, exists := t.Properties["intersection"]
	if !exists {
		return IntersectionProperties{}, false
	}
	
	intersectionProps, ok := props.(IntersectionProperties)
	return intersectionProps, ok
}


func (t *Tool) GetZoneProperties() (ZoneProperties, bool) {
	props, exists := t.Properties["zone"]
	if !exists {
		return ZoneProperties{}, false
	}
	
	zoneProps, ok := props.(ZoneProperties)
	return zoneProps, ok
}
