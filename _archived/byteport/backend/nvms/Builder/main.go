package main

import (
	"fmt"
	"net/http"

	spinhttp "github.com/fermyon/spin/sdk/go/v2/http"
)

func init() {
	spinhttp.Handle(func(w http.ResponseWriter, r *http.Request) {
		/* Receive a Proj-Obj and Zip Ball, provision a docker img for each service via aws image builder, push to ecr, may need to do push to s3 here*/
		w.Header().Set("Content-Type", "text/plain")
		fmt.Fprintln(w, "Built Images and Pushed to ECR")
	})
}

func main() {}
