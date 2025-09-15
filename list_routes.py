import sys
sys.path.append('.')

from app.main import app
from fastapi.routing import APIRoute

def get_routes():
    routes = []
    for route in app.routes:
        if isinstance(route, APIRoute):
            routes.append({
                'path': route.path,
                'methods': list(route.methods),
                'name': route.name
            })
    return routes

if __name__ == "__main__":
    for route in get_routes():
        for method in route['methods']:
            if method != 'HEAD' and method != 'OPTIONS':
                print(f"{method} {route['path']} ({route['name']})")
