"""
API v1 Router - aggregates all endpoint routers
"""
from fastapi import APIRouter

from app.api.v1.endpoints import auth, profile, feed, voting, my_votes, matching, admin, dashboard

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(profile.router, prefix="/me", tags=["Profile"])
api_router.include_router(dashboard.router, tags=["Dashboard"])
api_router.include_router(feed.router, tags=["Feed"])
api_router.include_router(voting.router, prefix="/measures", tags=["Voting"])
api_router.include_router(my_votes.router, prefix="/my-votes", tags=["My Votes"])
api_router.include_router(matching.router, prefix="/matches", tags=["Matching"])
api_router.include_router(admin.router, prefix="/admin", tags=["Admin"])
