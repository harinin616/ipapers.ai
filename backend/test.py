from fastapi import FastAPI
from pprint import pprint

pprint([(r.path, r.methods, r.name) for r in app.router.routes])
