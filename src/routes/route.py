from flask import Blueprint, jsonify, request, session
from src.models.route import Route, RouteStop
from src.models.appointment import Appointment
from src.models.patient import Patient
from src.models.user import User, db
from src.routes.auth import login_required, admin_required
from datetime import datetime, date
import dateutil.parser

route_bp = Blueprint('route', __name__)

@route_bp.route('/routes/optimize', methods=['POST'])
@login_required
def optimize_route():
    try:
        data = request.json
        user = User.query.get(session['user_id'])
        
        # Validate required fields
        required_fields = ['clinician_id', 'route_date']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'{field} is required'}), 400
        
        clinician_id = data['clinician_id']
        route_date = dateutil.parser.parse(data['route_date']).date()
        
        # Check permissions
        if user.role == 'Clinician' and user.id != clinician_id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Get appointments for the clinician on the specified date
        appointments = Appointment.query.filter(
            Appointment.clinician_id == clinician_id,
            Appointment.start_time >= datetime.combine(route_date, datetime.min.time()),
            Appointment.start_time < datetime.combine(route_date, datetime.max.time()),
            Appointment.status == 'scheduled'
        ).order_by(Appointment.start_time).all()
        
        if not appointments:
            return jsonify({'error': 'No appointments found for the specified date'}), 404
        
        # Check if route already exists
        existing_route = Route.query.filter_by(
            clinician_id=clinician_id,
            route_date=route_date
        ).first()
        
        if existing_route:
            # Update existing route
            route = existing_route
            # Clear existing stops
            RouteStop.query.filter_by(route_id=route.id).delete()
        else:
            # Create new route
            route = Route(
                clinician_id=clinician_id,
                route_date=route_date
            )
            db.session.add(route)
            db.session.flush()  # Get the route ID
        
        # Create optimized route (simplified algorithm - in reality would use mapping APIs)
        total_distance = 0
        estimated_duration = 0
        route_stops = []
        
        for i, appointment in enumerate(appointments):
            # Create route stop
            stop = RouteStop(
                route_id=route.id,
                appointment_id=appointment.id,
                stop_order=i + 1,
                arrival_time=appointment.start_time,
                departure_time=appointment.end_time
            )
            db.session.add(stop)
            route_stops.append(stop)
            
            # Estimate duration (simplified - would use real mapping data)
            estimated_duration += 60  # 60 minutes per appointment
            if i > 0:
                estimated_duration += 15  # 15 minutes travel time between appointments
                total_distance += 5  # 5 miles between appointments (simplified)
        
        # Update route with calculated values
        route.total_distance = total_distance
        route.estimated_duration = estimated_duration
        
        # Create optimized path data (simplified)
        optimized_path = {
            'stops': [
                {
                    'order': stop.stop_order,
                    'appointment_id': stop.appointment_id,
                    'patient_name': stop.appointment.patient.name,
                    'address': stop.appointment.patient.address,
                    'arrival_time': stop.arrival_time.isoformat(),
                    'departure_time': stop.departure_time.isoformat()
                }
                for stop in route_stops
            ],
            'total_distance': total_distance,
            'estimated_duration': estimated_duration
        }
        
        route.set_optimized_path(optimized_path)
        
        db.session.commit()
        
        return jsonify(route.to_dict()), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@route_bp.route('/routes/<int:route_id>', methods=['GET'])
@login_required
def get_route(route_id):
    try:
        route = Route.query.get_or_404(route_id)
        user = User.query.get(session['user_id'])
        
        # Check permissions
        if user.role == 'Clinician' and route.clinician_id != user.id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Get route stops with appointment and patient details
        stops = RouteStop.query.filter_by(route_id=route_id).order_by(RouteStop.stop_order).all()
        
        route_data = route.to_dict()
        route_data['stops'] = [stop.to_dict() for stop in stops]
        
        return jsonify(route_data)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@route_bp.route('/routes/<int:route_id>/notes', methods=['PUT'])
@login_required
def update_route_notes(route_id):
    try:
        route = Route.query.get_or_404(route_id)
        user = User.query.get(session['user_id'])
        data = request.json
        
        # Check permissions
        if user.role == 'Clinician' and route.clinician_id != user.id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Update notes for specific stops
        if 'stop_notes' in data:
            for stop_data in data['stop_notes']:
                if 'stop_id' in stop_data and 'notes' in stop_data:
                    stop = RouteStop.query.filter_by(
                        id=stop_data['stop_id'],
                        route_id=route_id
                    ).first()
                    
                    if stop:
                        stop.visit_notes = stop_data['notes']
        
        db.session.commit()
        return jsonify({'message': 'Notes updated successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@route_bp.route('/routes/<int:route_id>/stops/<int:stop_id>/status', methods=['PUT'])
@login_required
def update_stop_status(route_id, stop_id):
    try:
        route = Route.query.get_or_404(route_id)
        user = User.query.get(session['user_id'])
        data = request.json
        
        # Check permissions
        if user.role == 'Clinician' and route.clinician_id != user.id:
            return jsonify({'error': 'Access denied'}), 403
        
        stop = RouteStop.query.filter_by(id=stop_id, route_id=route_id).first_or_404()
        
        if 'status' not in data:
            return jsonify({'error': 'Status is required'}), 400
        
        valid_statuses = ['pending', 'in-progress', 'completed', 'skipped']
        if data['status'] not in valid_statuses:
            return jsonify({'error': 'Invalid status'}), 400
        
        stop.status = data['status']
        
        # Update timestamps based on status
        if data['status'] == 'in-progress' and not stop.arrival_time:
            stop.arrival_time = datetime.now()
        elif data['status'] == 'completed' and not stop.departure_time:
            stop.departure_time = datetime.now()
        
        db.session.commit()
        return jsonify(stop.to_dict())
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@route_bp.route('/clinicians/<int:clinician_id>/routes', methods=['GET'])
@login_required
def get_clinician_routes(clinician_id):
    try:
        user = User.query.get(session['user_id'])
        
        # Check permissions
        if user.role == 'Clinician' and user.id != clinician_id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Get query parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        query = Route.query.filter_by(clinician_id=clinician_id)
        
        if start_date:
            start_dt = dateutil.parser.parse(start_date).date()
            query = query.filter(Route.route_date >= start_dt)
        
        if end_date:
            end_dt = dateutil.parser.parse(end_date).date()
            query = query.filter(Route.route_date <= end_dt)
        
        routes = query.order_by(Route.route_date.desc()).all()
        return jsonify([route.to_dict() for route in routes])
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@route_bp.route('/routes/<int:route_id>', methods=['DELETE'])
@login_required
def delete_route(route_id):
    try:
        route = Route.query.get_or_404(route_id)
        user = User.query.get(session['user_id'])
        
        # Check permissions
        if user.role == 'Clinician' and route.clinician_id != user.id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Delete route stops first
        RouteStop.query.filter_by(route_id=route_id).delete()
        
        # Delete route
        db.session.delete(route)
        db.session.commit()
        
        return '', 204
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@route_bp.route('/routes/today', methods=['GET'])
@login_required
def get_today_routes():
    try:
        user = User.query.get(session['user_id'])
        today = date.today()
        
        if user.role == 'Clinician':
            # Get today's route for the clinician
            route = Route.query.filter_by(
                clinician_id=user.id,
                route_date=today
            ).first()
            
            if route:
                stops = RouteStop.query.filter_by(route_id=route.id).order_by(RouteStop.stop_order).all()
                route_data = route.to_dict()
                route_data['stops'] = [stop.to_dict() for stop in stops]
                return jsonify(route_data)
            else:
                return jsonify({'message': 'No route found for today'}), 404
        
        else:
            # Admins can see all routes for today
            routes = Route.query.filter_by(route_date=today).all()
            routes_data = []
            
            for route in routes:
                stops = RouteStop.query.filter_by(route_id=route.id).order_by(RouteStop.stop_order).all()
                route_data = route.to_dict()
                route_data['stops'] = [stop.to_dict() for stop in stops]
                routes_data.append(route_data)
            
            return jsonify(routes_data)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

