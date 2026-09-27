package routes

import (
	"byteport/models"
	"net/http"

	"github.com/gin-gonic/gin"
)

func GetInstances(c *gin.Context) {
	var instances []models.Instance
	user := c.MustGet("user").(models.User)
	models.DB.Where("owner = ?", user.UUID).Find(&instances)
	c.JSON(http.StatusOK, instances)
}
