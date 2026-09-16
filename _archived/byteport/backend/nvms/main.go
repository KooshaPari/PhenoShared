package main

import (
	"net/http"
	"nvms/projectManager"

	spinhttp "github.com/fermyon/spin-go-sdk/http"
	"github.com/julienschmidt/httprouter"
)

func init() {
	spinhttp.Handle(func(w http.ResponseWriter, r *http.Request) {
		router := initRouter()
		router.ServeHTTP(w, r)
	})

}
func initRouter() *spinhttp.Router {
	router := spinhttp.NewRouter()
	router.POST("/", validateAction(projectManager.DeployProject))
	router.POST("/deploy", validateAction(projectManager.DeployProject))
	router.POST("/terminate", validateAction(projectManager.TerminateProject))
	return router
}
func validateAction(handler http.HandlerFunc) httprouter.Handle {
	return func(w http.ResponseWriter, r *http.Request, _ httprouter.Params) {
		err := lib.AuthMiddleware(w, r)
		if err != nil {
			http.Error(w, "Unauthorized", http.StatusUnauthorized)
			return
		}
		handler(w, r)
	}
}
func main() {}
