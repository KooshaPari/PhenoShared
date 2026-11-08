package graph


type POIType string

const (

	POIResidential POIType = "residential"
	POICommercial  POIType = "commercial"
	
)


type POI struct {
	ID       int
	NodeID   int
	Type     POIType
	Name     string
	Capacity int
	Position [2]int
}


func NewPOI(id, nodeID int, poiType POIType, position [2]int) *POI {

	name := string(poiType) + "-" + string(id)


	capacity := 5
	switch poiType {
	case POIResidential:
		capacity = 10
	case POICommercial:
		capacity = 20
	
	}

	return &POI{
		ID:       id,
		NodeID:   nodeID,
		Type:     poiType,
		Name:     name,
		Capacity: capacity,
		Position: position,
	}
}


func IsPOI(node *Node) bool {
	_, exists := node.GetProperty("poi")
	return exists
}


func GetPOIType(node *Node) POIType {
	poiType, exists := node.GetProperty("poi_type")
	if !exists {
		return ""
	}
	return POIType(poiType.(string))
}


func AttachPOI(node *Node, poi *POI) {
	node.SetProperty("poi", true)
	node.SetProperty("poi_id", poi.ID)
	node.SetProperty("poi_type", string(poi.Type))
	node.SetProperty("poi_name", poi.Name)
	node.SetProperty("poi_capacity", poi.Capacity)
}
