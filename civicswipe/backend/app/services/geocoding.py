"""
Geocoding service for address validation and coordinate resolution.
Uses Census Geocoder API (free, no key required). Works for all US addresses.
"""
import httpx
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)

CENSUS_GEOCODER_BASE = "https://geocoding.geo.census.gov/geocoder"


class GeocodingService:
    """
    Service for geocoding addresses to lat/lon coordinates using the Census Geocoder.
    """

    async def geocode_address(
        self,
        street: str,
        city: str,
        state: str,
        zip_code: str,
    ) -> Optional[Tuple[float, float]]:
        """
        Geocode a US address to (latitude, longitude) via Census Geocoder.
        Works for any address in all 50 states + DC.
        """
        try:
            url = f"{CENSUS_GEOCODER_BASE}/locations/address"
            params = {
                "street": street,
                "city": city,
                "state": state,
                "zip": zip_code,
                "benchmark": "Public_AR_Current",
                "format": "json",
            }

            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()

            matches = data.get("result", {}).get("addressMatches", [])
            if not matches:
                logger.warning(f"No geocode match for {street}, {city}, {state} {zip_code}")
                return None

            coords = matches[0].get("coordinates", {})
            lat = coords.get("y")
            lon = coords.get("x")

            if lat is not None and lon is not None:
                return (float(lat), float(lon))

            return None

        except Exception as e:
            logger.error(f"Geocoding failed: {e}")
            return None

    async def reverse_geocode(
        self,
        lat: float,
        lon: float,
    ) -> Optional[dict]:
        """
        Reverse geocode coordinates to geographic info via Census Geocoder.
        """
        try:
            url = f"{CENSUS_GEOCODER_BASE}/geographies/coordinates"
            params = {
                "x": str(lon),
                "y": str(lat),
                "benchmark": "Public_AR_Current",
                "vintage": "Current_Current",
                "format": "json",
            }

            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()

            geographies = data.get("result", {}).get("geographies", {})
            return geographies if geographies else None

        except Exception as e:
            logger.error(f"Reverse geocoding failed: {e}")
            return None

    def normalize_address(
        self,
        street: str,
        city: str,
        state: str,
        zip_code: str,
    ) -> dict:
        """Normalize address components for consistent storage."""
        return {
            "street": street.strip().upper(),
            "city": city.strip().title(),
            "state": state.strip().upper(),
            "zip_code": zip_code.strip(),
        }


# Global instance
geocoding_service = GeocodingService()
