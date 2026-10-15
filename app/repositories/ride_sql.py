# Shared SELECT list and joins for a ride with its stations, driver profile and vehicle.
# Fixed fragments only: every user-supplied value is a bound parameter.
RIDE_COLUMNS = """
       r.id_ride, r.id_driver, r.status AS ride_status,
       r.id_source_station, ss.station_name AS source_station_name,
       r.id_destination_station, ds.station_name AS destination_station_name,
       r.departure_time, r.estimated_arrival_time, r.total_seats, r.available_seats,
       r.price_per_seat, r.notes,
       p.full_name AS driver_name, p.photo_url AS driver_photo_url,
       v.make AS vehicle_make, v.model AS vehicle_model, v.color AS vehicle_color,
       v.vehicle_type AS vehicle_type"""
RIDE_JOINS = """
JOIN station ss ON ss.id_station = r.id_source_station
JOIN station ds ON ds.id_station = r.id_destination_station
LEFT JOIN user_profile p ON p.id_user = r.id_driver
LEFT JOIN vehicle v ON v.id_vehicle = r.id_vehicle"""
