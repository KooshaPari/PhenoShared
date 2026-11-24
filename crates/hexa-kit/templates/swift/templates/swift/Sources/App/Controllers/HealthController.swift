import Vapor

struct HealthController: RouteCollection {
    func boot(routes: RoutesBuilder) throws {
        routes.get("health", use: health)
    }
    
    func health(req: Request) -> Response {
        return Response(
            status: .ok,
            headers: ["Content-Type": "application/json"],
            body: Response.Body(string: "{\"status\":\"ok\",\"version\":\"{{ version }}\"}")
        )
    }
}